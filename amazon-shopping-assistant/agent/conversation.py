import logging
import re
import json
import time
from typing import Dict, Any, List, Optional
from .query_parser import QueryParser
from .amazon_navigator import AmazonNavigator
from .product_analyzer import ProductAnalyzer
from .product_researcher import ProductResearcher
from .browser_manager import BrowserManager
from .agent_framework import AgentFramework
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages conversation with v2 agentic capabilities and deep product research"""
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.query_parser = QueryParser()
        self.amazon_navigator = AmazonNavigator(browser_manager)
        self.product_analyzer = ProductAnalyzer()
        # New for v2: Product Researcher for deep analysis
        self.product_researcher = ProductResearcher(browser_manager)
        self.agent = AgentFramework()
        
        self.conversation_history = []
        self.current_products = []
        self.current_query = {}
        self.current_plan = []
        self.current_step = 0
        self.researched_products = {}  # Cache for already researched products
    
    def initialize(self):
        """Initialize the conversation and browser"""
        page = self.amazon_navigator.initialize()
        self.product_researcher.initialize(page)
    
    def process_message(self, user_message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Process message with v2 planning and advanced features"""
        try:
            self.conversation_history.append({"role": "user", "content": user_message})
            
            # Determine intent and check if this is a follow-up
            is_followup = self.is_followup_query(user_message)
            intent = self._get_intent(user_message)
            
            # Direct command handling for better UX
            message_lower = user_message.lower()
            if "compare" in message_lower and "product" in message_lower and len(self.current_products) > 1:
                return self._compare_products_deeply()
            elif any(x in message_lower for x in ["review", "what people say"]) and self.current_products:
                return self._deep_review_analysis()
            elif any(x in message_lower for x in ["specs", "specifications", "details"]) and self.current_products:
                return self._research_product(self.current_products[0])
            
            # Handle specialized intents
            if intent == "reviews" and self.current_products:
                return self._deep_review_analysis()
            elif intent == "compare" and len(self.current_products) > 1:
                return self._compare_products_deeply()
            elif intent == "research" and self.current_products:
                return self._research_product(self.current_products[0])
            elif is_followup:
                parsed_query = self.handle_followup_query(user_message)
                return self._execute_search(parsed_query, is_refinement=True)
            else:
                # V2: Create a multi-step plan using the agent framework
                try:
                    self.current_plan = self.agent.create_plan(user_message, user_id)
                    logger.info(f"Created plan: {self.current_plan}")
                except Exception as e:
                    logger.error(f"Error creating plan: {str(e)}")
                    self.current_plan = [{"step_number": 1, "action": "search"}]
                
                # V2: Use AI for query parsing if available
                try:
                    if OPENAI_API_KEY:
                        parsed_query = self.agent.parse_query_with_ai(user_message)
                        logger.info(f"AI parsed query: {parsed_query}")
                    else:
                        parsed_query = self.query_parser.parse_shopping_query(user_message)
                except Exception as e:
                    logger.error(f"AI parsing error: {str(e)}")
                    parsed_query = self.query_parser.parse_shopping_query(user_message)
                
                self.current_query = parsed_query
                return self._execute_search(parsed_query, user_id=user_id)
        except Exception as e:
            logger.error(f"Process message error: {str(e)}")
            return {"response": f"I encountered an issue: {str(e)}"}
    
    def _get_intent(self, message: str) -> str:
        """Get the primary intent from the message"""
        message = message.lower()
        if any(term in message for term in ["review", "what are people saying", "feedback", "opinions"]):
            return "reviews"
        elif any(term in message for term in ["compare", "difference", "better", "which one", "vs", "versus"]):
            return "compare"
        elif any(term in message for term in ["details", "more info", "specifications", "specs", "tell me about", "research"]):
            return "research"
        return "search"
    
    def _execute_search(self, parsed_query: Dict[str, Any], is_refinement: bool = False, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute search with product analysis and optional deep research"""
        try:
            # Initial progress message
            initial_response = {"response": "Searching for products that match your criteria...", "is_interim": True}
            logger.info("Executing search with parsed query")
            
            # Basic search flow
            search_term = self.construct_search_term(parsed_query)
            self.amazon_navigator.search_products(search_term)
            self.apply_filters_from_query(parsed_query)
            products = self.amazon_navigator.extract_search_results(max_results=5)
            
            # Analyze products
            ranked_products = self.product_analyzer.rank_products(products, parsed_query)
            self.current_products = ranked_products
            
            # Add recommendations
            for product in ranked_products:
                product['recommendation_reason'] = self.product_analyzer.get_recommendation_reason(
                    product, parsed_query)
            
            # V2: Perform deep research on top product if in plan or high-value item
            should_research = self._should_perform_research(parsed_query)
            
            if should_research and ranked_products:
                top_product = ranked_products[0]
                research_data = self.product_researcher.research_product(top_product)
                top_product['research'] = research_data
                self.researched_products[top_product.get('link', '')] = research_data
            
            # V2: Update user preferences
            if user_id and ranked_products:
                for i, product in enumerate(ranked_products[:3]):
                    # Weight by position (first product gets more weight)
                    action = "viewed_first" if i == 0 else "viewed"
                    self.agent.update_preferences(user_id, product, parsed_query, action)
            
            # V2: Get next actions from plan
            next_actions = self._get_next_actions()
            
            # V2: Generate refinement suggestions
            refinement_suggestions = self.agent.suggest_refinements(parsed_query, ranked_products)
            
            # Create response
            response = self._format_search_response(ranked_products, parsed_query, 
                                                   is_refinement, next_actions, 
                                                   refinement_suggestions)
            self.conversation_history.append({"role": "assistant", "content": response})

            if products:
                links_available = sum(1 for p in products if p.get('link'))
                logger.info(f"Products with valid links: {links_available}/{len(products)}")
                if links_available > 0:
                    logger.info(f"Sample link: {products[0].get('link', 'None')}")
                        
            return {
                "response": response,
                "products": ranked_products,
                "parsed_query": parsed_query
            }
        except Exception as e:
            logger.error(f"Search execution error: {str(e)}")
            return {"response": "I'm having trouble searching for these products. Could you try a different search term?"}
    
    def _should_perform_research(self, query: Dict[str, Any]) -> bool:
        """Determine if deep product research should be performed"""
        # Check if it's in our plan
        research_in_plan = False
        for step in self.current_plan:
            if step.get("action") == "analyze_reviews" or step.get("action") == "research":
                research_in_plan = True
                break
        
        # For high-value items (over $100), always do research
        high_value = False
        price_max = query.get("price_range", {}).get("max", 0)
        if price_max and price_max > 100:
            high_value = True
        
        # For items where user explicitly mentioned quality or reliability
        quality_focus = False
        keywords = query.get("keywords", [])
        quality_terms = ["quality", "reliable", "durable", "best", "top", "premium"]
        if any(term in ' '.join(keywords).lower() for term in quality_terms):
            quality_focus = True
        
        return research_in_plan or high_value or quality_focus
    
    def _deep_review_analysis(self) -> Dict[str, Any]:
        """V2: Perform deep analysis of product reviews"""
        try:
            product = self.current_products[0]
            product_link = product.get("link")
            if not product_link:
                return {"response": "I can't access this product's reviews."}
            
            # Check if we've already researched this product
            if product_link in self.researched_products:
                research = self.researched_products[product_link]
                review_data = research.get("review_analysis", {})
            else:
                # Navigate to product and perform research
                logger.info(f"Performing deep review analysis for: {product.get('title', 'unknown product')}")
                research = self.product_researcher.research_product(product)
                review_data = research.get("review_analysis", {})
                self.researched_products[product_link] = research
            
            # Format enhanced review response
            response = f"## In-depth Review Analysis: {product.get('title', 'This Product')}\n\n"
            
            if "sentiment" in review_data:
                response += f"**Overall Sentiment**: {review_data['sentiment']}\n\n"
            
            if "strengths" in review_data and review_data["strengths"]:
                response += "### Key Strengths\n"
                for strength in review_data["strengths"]:
                    response += f"✅ {strength}\n"
                response += "\n"
            
            if "concerns" in review_data and review_data["concerns"]:
                response += "### Common Concerns\n"
                for concern in review_data["concerns"]:
                    response += f"⚠️ {concern}\n"
                response += "\n"
            
            if "longevity" in review_data and review_data["longevity"] != "unknown":
                response += f"**Durability Assessment**: {review_data['longevity']}\n\n"
            
            if "common_themes" in review_data and review_data["common_themes"]:
                response += "### Common Themes in Reviews\n"
                for theme in review_data["common_themes"]:
                    response += f"• {theme}\n"
                response += "\n"
            
            if "customer_service" in review_data and review_data["customer_service"]:
                response += f"**Customer Service**: {review_data['customer_service']}\n\n"
            
            if "competitor_mentions" in review_data and review_data["competitor_mentions"]:
                response += "### Compared To\n"
                for competitor in review_data["competitor_mentions"]:
                    response += f"• {competitor}\n"
                response += "\n"
            
            # Add pros and cons summary
            if "pros_cons" in research:
                pros = research["pros_cons"].get("pros", [])
                cons = research["pros_cons"].get("cons", [])
                
                if pros:
                    response += "### Pros\n"
                    for pro in pros:
                        response += f"👍 {pro}\n"
                    response += "\n"
                
                if cons:
                    response += "### Cons\n"
                    for con in cons:
                        response += f"👎 {con}\n"
                    response += "\n"
            
            # Add verification info
            verified = review_data.get("verified_purchases", 0)
            if verified:
                response += f"*Based on {verified} verified purchase reviews*\n\n"
            
            response += "Would you like to compare with other products or learn more about specific aspects?"
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return {"response": response, "research": research}
            
        except Exception as e:
            logger.error(f"Deep review analysis error: {str(e)}")
            return {"response": "I encountered an issue analyzing the reviews. Would you like to see basic product information instead?"}
    
    def _research_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """V2: Perform detailed research on a specific product"""
        try:
            product_link = product.get("link")
            if not product_link:
                return {"response": "I can't access this product's details."}
            
            # Check if already researched
            if product_link in self.researched_products:
                research = self.researched_products[product_link]
            else:
                # Perform new research
                logger.info(f"Researching product details for: {product.get('title', 'unknown product')}")
                research = self.product_researcher.research_product(product)
                self.researched_products[product_link] = research
            
            # Format comprehensive product details
            response = f"## Detailed Analysis: {product.get('title', 'This Product')}\n\n"
            
            # Add specifications
            specs = research.get("specifications", {})
            if specs:
                response += "### Key Specifications\n"
                for key, value in list(specs.items())[:8]:  # Limit to top 8 specs
                    response += f"• **{key}**: {value}\n"
                response += "\n"
            
            # Add description summary
            description = research.get("detailed_description", "")
            if description:
                # Summarize if too long
                if len(description) > 300:
                    response += "### Product Description\n"
                    response += description[:300] + "...\n\n"
                else:
                    response += "### Product Description\n"
                    response += description + "\n\n"
            
            # Add pros and cons
            pros_cons = research.get("pros_cons", {})
            pros = pros_cons.get("pros", [])
            cons = pros_cons.get("cons", [])
            
            if pros:
                response += "### Pros\n"
                for pro in pros:
                    response += f"👍 {pro}\n"
                response += "\n"
            
            if cons:
                response += "### Cons\n"
                for con in cons:
                    response += f"👎 {con}\n"
                response += "\n"
            
            # Add review summary
            review_data = research.get("review_analysis", {})
            if review_data:
                response += "### What Customers Say\n"
                if "sentiment" in review_data:
                    response += f"**Overall Sentiment**: {review_data['sentiment']}\n"
                
                if "strengths" in review_data and review_data["strengths"]:
                    top_strengths = ', '.join(review_data["strengths"][:3])
                    response += f"**Top Strengths**: {top_strengths}\n"
                
                if "concerns" in review_data and review_data["concerns"]:
                    top_concerns = ', '.join(review_data["concerns"][:3])
                    response += f"**Top Concerns**: {top_concerns}\n"
                
                response += "\n"
            
            response += "Would you like to compare with other products or see full review details?"
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return {"response": response, "research": research}
            
        except Exception as e:
            logger.error(f"Product research error: {str(e)}")
            return {"response": "I had trouble researching this product in depth. Would you like to see the basic information instead?"}
    
    def _compare_products_deeply(self) -> Dict[str, Any]:
        """V2: Compare multiple products with deep research insights"""
        try:
            products = self.current_products[:3]  # Limit to top 3
            
            # Research all products if needed
            researched_products = []
            for product in products:
                product_link = product.get("link", "")
                if not product_link:
                    logger.warning(f"Missing link for product: {product.get('title', 'Unknown')}")
                    continue
                    
                # Check if already researched
                if product_link in self.researched_products:
                    research = self.researched_products[product_link]
                else:
                    # Perform new research
                    logger.info(f"Researching for comparison: {product.get('title', 'unknown product')}")
                    research = self.product_researcher.research_product(product)
                    self.researched_products[product_link] = research
                
                researched_products.append(product.copy())
                researched_products[-1]['research'] = research
            
            if len(researched_products) < 2:
                return {"response": "I need at least two products with valid links to compare. Please try a different search."}
                
            # Generate deep comparison using the product researcher
            comparison = self.product_researcher.compare_multiple_products(researched_products)
            
            # Format enhanced comparison response
            response = "## Product Comparison Analysis\n\n"
            
            # Best choice recommendation
            if "best_choice" in comparison:
                best_choice = comparison["best_choice"]
                best_idx = 0
                if isinstance(best_choice, dict) and "product_index" in best_choice:
                    best_idx = best_choice.get("product_index", 0) - 1
                
                if 0 <= best_idx < len(products):
                    best_product = products[best_idx]
                    response += f"### 🏆 Best Overall Choice: {best_product.get('title', 'Product ' + str(best_idx+1))}\n"
                    
                    if isinstance(best_choice, dict) and "reason" in best_choice:
                        response += f"*{best_choice.get('reason', '')}*\n\n"
                    elif isinstance(best_choice, str):
                        response += f"*{best_choice}*\n\n"
                    else:
                        response += "\n"
            
            # Best value recommendation
            if "best_value" in comparison:
                value_choice = comparison["best_value"]
                value_idx = 0
                if isinstance(value_choice, dict) and "product_index" in value_choice:
                    value_idx = value_choice.get("product_index", 0) - 1
                
                if 0 <= value_idx < len(products):
                    value_product = products[value_idx]
                    response += f"### 💰 Best Value Choice: {value_product.get('title', 'Product ' + str(value_idx+1))}\n"
                    
                    if isinstance(value_choice, dict) and "reason" in value_choice:
                        response += f"*{value_choice.get('reason', '')}*\n\n"
                    elif isinstance(value_choice, str):
                        response += f"*{value_choice}*\n\n"
                    else:
                        response += "\n"
            
            # Feature comparison
            if "feature_comparison" in comparison and comparison["feature_comparison"]:
                response += "### Feature Comparison\n"
                
                if isinstance(comparison["feature_comparison"], list):
                    for feature in comparison["feature_comparison"]:
                        if isinstance(feature, dict):
                            feature_name = feature.get("name", "")
                            winner_idx = 0
                            if "winner_index" in feature:
                                winner_idx = feature.get("winner_index", 0) - 1
                            
                            if feature_name and 0 <= winner_idx < len(products):
                                winner_product = products[winner_idx]
                                winner_name = winner_product.get('title', f'Product {winner_idx+1}')
                                # Shorten title if too long
                                if len(winner_name) > 30:
                                    winner_name = winner_name[:27] + "..."
                                response += f"• **{feature_name}**: {winner_name} wins\n"
                else:
                    response += str(comparison["feature_comparison"]) + "\n"
                    
                response += "\n"
            
            # Reliability comparison
            if "reliability_comparison" in comparison:
                response += "### Reliability Assessment\n"
                if isinstance(comparison["reliability_comparison"], dict):
                    response += json.dumps(comparison["reliability_comparison"]) + "\n\n"
                else:
                    response += str(comparison["reliability_comparison"]) + "\n\n"
            
            # Price analysis
            if "price_analysis" in comparison:
                response += "### Price-to-Value Analysis\n"
                if isinstance(comparison["price_analysis"], dict):
                    response += json.dumps(comparison["price_analysis"]) + "\n\n"
                else:
                    response += str(comparison["price_analysis"]) + "\n\n"
            
            # User recommendation
            if "recommendation" in comparison:
                response += "### Best For Different Users\n"
                if isinstance(comparison["recommendation"], dict):
                    response += json.dumps(comparison["recommendation"]) + "\n\n"
                else:
                    response += str(comparison["recommendation"]) + "\n\n"
            
            # Summary
            response += "### Summary\n"
            for i, product in enumerate(products):
                product_title = product.get('title', f'Product {i+1}')
                # Shorten title if too long
                if len(product_title) > 40:
                    product_title = product_title[:37] + "..."
                    
                if i < len(researched_products):
                    research = researched_products[i].get('research', {})
                    pros = research.get('pros_cons', {}).get('pros', [])
                    cons = research.get('pros_cons', {}).get('cons', [])
                    
                    response += f"**{product_title}**\n"
                    if pros:
                        response += f"*Pros*: {', '.join(pros[:2])}\n"
                    if cons:
                        response += f"*Cons*: {', '.join(cons[:2])}\n"
                else:
                    response += f"**{product_title}**\n"
                    
                response += "\n"
            
            response += "Would you like more details about any specific product or aspect?"
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return {"response": response, "comparison": comparison}
        
        except Exception as e:
            logger.error(f"Deep comparison error: {str(e)}")
            return {"response": "I had trouble generating a detailed comparison. Would you like to see a basic comparison instead?"}
    
    def _get_next_actions(self) -> List[str]:
        """Get next steps from plan and context"""
        actions = []
        
        # Check plan for next steps
        if self.current_plan and self.current_step < len(self.current_plan):
            next_step = self.current_plan[self.current_step]
            self.current_step += 1
            
            action = next_step.get("action", "")
            if action == "analyze_reviews":
                actions.append("Read in-depth review analysis")
            elif action == "compare":
                actions.append("Compare top products")
            elif action == "research":
                actions.append("See detailed product specifications")
            elif action == "filter":
                actions.append("Refine your search")
            elif action == "recommend":
                actions.append("Get my final recommendation")
        
        # Add default actions based on context
        if len(self.current_products) > 1 and "Compare top products" not in actions:
            actions.append("Compare top products")
        
        if "Read in-depth review analysis" not in actions and self.current_products:
            actions.append("Read in-depth review analysis")
            
        if "See detailed product specifications" not in actions and self.current_products:
            actions.append("See detailed product specifications")
            
        return actions
    
    def _format_search_response(self, products: List[Dict], parsed_query: Dict, 
                              is_refinement: bool, next_actions: List[str],
                              refinement_suggestions: List[str]) -> str:
        """Format search results with next actions and refinement suggestions"""
        if not products:
            return "I couldn't find products matching your request. Would you like to try different terms?"
        
        # Create appropriate intro based on context
        if is_refinement:
            intro = "Here are the refined results based on your request:"
        else:
            product_type = parsed_query.get("product_type", "products")
            intro = f"I found these {product_type} that match your criteria:"
        
        response_parts = [intro]
        
        # Add top products with enhanced details
        for i, product in enumerate(products[:3], 1):
            product_details = f"\n### {i}. {product.get('title', 'Unknown product')}\n"
            product_details += f"* **Price**: {product.get('price', 'Price not available')}\n"
            product_details += f"* **Rating**: {product.get('rating', 'No ratings')}"
            
            # Add review count if available
            review_count = product.get('review_count', 0)
            if review_count:
                product_details += f" ({review_count} reviews)\n"
            else:
                product_details += "\n"
            
            # V2: Add enhanced features extraction
            if 'research' in product:
                # Use researched specifications
                specs = product['research'].get('specifications', {})
                if specs:
                    important_specs = []
                    # Focus on key specs based on product type
                    product_type = parsed_query.get("product_type", "").lower()
                    if "laptop" in product_type:
                        keys_to_check = ["Processor", "RAM", "Storage", "Display", "Battery", "Weight"]
                    elif "phone" in product_type:
                        keys_to_check = ["Display", "Camera", "Battery", "Storage", "RAM"]
                    else:
                        keys_to_check = list(specs.keys())
                    
                    for key in keys_to_check:
                        if key in specs:
                            important_specs.append(f"**{key}**: {specs[key]}")
                    
                    if important_specs:
                        product_details += f"* **Specs**: {' | '.join(important_specs[:3])}\n"
            else:
                # Extract features from title
                key_features = []
                title = product.get('title', '').lower()
                for feature in ["ram", "processor", "ssd", "battery", "display", "screen"]:
                    if feature in title:
                        pattern = rf'(\d+(?:\.\d+)?\s*(?:GB|TB|GHz|inch|hours)?\s*{re.escape(feature)})'
                        match = re.search(pattern, title, re.IGNORECASE)
                        if match:
                            key_features.append(match.group(0))
                
                if key_features:
                    product_details += f"* **Features**: {', '.join(key_features)}\n"
                
            # Add shipping info
            product_details += f"* {'✓ Prime shipping' if product.get('has_prime', False) else 'Standard shipping'}\n"
            
            # Add recommendation reason
            if product.get('recommendation_reason'):
                product_details += f"* **Why this product**: {product['recommendation_reason']}\n"
            
            # Add pros/cons if available from research
            if 'research' in product and 'pros_cons' in product['research']:
                pros = product['research']['pros_cons'].get('pros', [])
                cons = product['research']['pros_cons'].get('cons', [])
                
                if pros:
                    product_details += f"* **Top Pro**: {pros[0]}\n"
                if cons:
                    product_details += f"* **Note**: {cons[0]}\n"
            
            response_parts.append(product_details)
        
        # V2: Add refinement suggestions with more context
        if refinement_suggestions:
            response_parts.append("\n### Suggestions to improve results")
            for suggestion in refinement_suggestions:
                response_parts.append(f"* {suggestion}")
        
        # Add next actions with clear paths forward
        if next_actions:
            response_parts.append("\n### What would you like to do next?")
            for action in next_actions:
                response_parts.append(f"* {action}")
        
        return "\n".join(response_parts)
    
    def is_followup_query(self, message: str) -> bool:
        """Enhanced follow-up detection with better context awareness"""
        if len(self.conversation_history) < 2:
            return False
            
        # Direct commands that should be treated as follow-ups when products exist
        direct_commands = [
            "compare", "compare products", "compare top products", 
            "reviews", "read reviews", "read in-depth review analysis",
            "details", "specifications", "specs", "see detailed product specifications",
            "tell me more", "more information", "learn more"
        ]
        
        message_lower = message.lower()
        
        # Check if this is a direct command and we have products
        if self.current_products and any(cmd in message_lower for cmd in direct_commands):
            return True
            
        # Original follow-up detection logic
        followup_phrases = [
            "show me", "more details", "cheaper", "better",
            "what about", "how about", "features", "price", "shipping"
        ]
        
        # Check for short queries that reference previous context
        is_short_query = len(message.split()) < 5
        has_pronoun_reference = any(term in message_lower for term in ["it", "this", "that", "these", "those", "they"])
        
        # Check for product number references (e.g., "show me #2")
        has_product_reference = bool(re.search(r'#?\d+', message_lower))
        
        # Check for command-like queries without clear product type
        is_command_without_product = (
            any(term in message_lower for term in ["show", "get", "tell", "find"]) and
            is_short_query and
            not any(term in message_lower for term in ["product", "item", "laptop", "phone"])
        )
        
        # Check for explicit follow-up phrases
        has_followup_phrase = any(phrase in message_lower for phrase in followup_phrases)
        
        return (
            (is_short_query and (has_pronoun_reference or has_product_reference)) or
            is_command_without_product or
            has_followup_phrase
        )
    
    def handle_followup_query(self, message: str) -> Dict[str, Any]:
        """Enhanced follow-up handling with better understanding of refinements"""
        modified_query = self.current_query.copy()
        message_lower = message.lower()
        
        # Check for specific product selection by number
        product_num_match = re.search(r'#?(\d+)', message_lower)
        if product_num_match:
            product_num = int(product_num_match.group(1))
            if 1 <= product_num <= len(self.current_products):
                # User is selecting a specific product for further investigation
                selected_product = self.current_products[product_num - 1]
                
                if "reviews" in message_lower or "what do people say" in message_lower:
                    # User wants reviews for specific product
                    self.current_products = [selected_product]
                    return self._deep_review_analysis()
                elif "details" in message_lower or "specs" in message_lower or "more about" in message_lower:
                    # User wants details for specific product
                    self.current_products = [selected_product]
                    return self._research_product(selected_product)
        
        # Price refinements
        if any(term in message_lower for term in ["cheaper", "less expensive", "lower price", "budget"]):
            current_max = modified_query.get("price_range", {}).get("max")
            if current_max:
                # Reduce by 20% or $100, whichever is less
                reduction = min(current_max * 0.2, 100)
                new_max = current_max - reduction
                if "price_range" not in modified_query:
                    modified_query["price_range"] = {}
                modified_query["price_range"]["max"] = new_max
        elif any(term in message_lower for term in ["more expensive", "higher quality", "premium", "better"]):
            current_min = modified_query.get("price_range", {}).get("min", 0)
            # Increase the minimum price to focus on higher-end products
            if "price_range" not in modified_query:
                modified_query["price_range"] = {}
            modified_query["price_range"]["min"] = current_min + 100
        
        # Quality refinements
        if any(term in message_lower for term in ["better rating", "higher rating", "top rated", "best reviews"]):
            # Increase minimum rating
            modified_query["rating_min"] = 4
            modified_query["exact_rating_min"] = 4.5
        
        # Feature refinements
        feature_patterns = [
            # Format: (regex pattern, feature name, keyword to add)
            (r'with\s+(\d+)\s*GB\s+RAM', "RAM", "RAM"),
            (r'more\s+RAM', "RAM", "more RAM"),
            (r'larger\s+screen', "screen", "larger screen"),
            (r'(\d+)\s*inch', "screen size", "inch"),
            (r'better\s+battery', "battery", "long battery"),
            (r'faster', "performance", "fast"),
            (r'lightweight', "weight", "lightweight"),
            (r'slim|thin', "design", "slim"),
            (r'portable', "portability", "portable")
        ]
        
        for pattern, feature_name, keyword in feature_patterns:
            if re.search(pattern, message_lower):
                # Add the feature to keywords
                if "keywords" not in modified_query:
                    modified_query["keywords"] = []
                if keyword not in modified_query["keywords"]:
                    modified_query["keywords"].append(keyword)
        
        # Shipping preference refinements
        if "prime" in message_lower or "fast shipping" in message_lower or "quick delivery" in message_lower:
            modified_query["prime_shipping"] = True
        
        # Brand refinements
        brand_match = re.search(r'by\s+([A-Za-z]+)', message_lower)
        if brand_match:
            brand = brand_match.group(1).capitalize()
            if "keywords" not in modified_query:
                modified_query["keywords"] = []
            modified_query["keywords"].append(brand)
        
        return modified_query
    
    def construct_search_term(self, parsed_query: Dict[str, Any]) -> str:
        """Construct an optimized search term from parsed query"""
        components = []
        
        # Always include product type
        if parsed_query.get("product_type"):
            components.append(parsed_query["product_type"])
        
        # Add primary keywords that significantly narrow the search
        important_keywords = []
        general_keywords = []
        
        for keyword in parsed_query.get("keywords", []):
            # Identify high-value keywords (specific features, specs, etc.)
            if any(term in keyword.lower() for term in [
                "gb", "tb", "inch", "hz", "processor", "intel", "amd", "ryzen",
                "nvidia", "wireless", "bluetooth", "waterproof", "rechargeable"
            ]):
                important_keywords.append(keyword)
            else:
                general_keywords.append(keyword)
        
        # Add important keywords first (up to 2)
        for keyword in important_keywords[:2]:
            if keyword.lower() not in ' '.join(components).lower():
                components.append(keyword)
        
        # Add general keywords if space allows (up to 1 more)
        for keyword in general_keywords[:1]:
            if keyword.lower() not in ' '.join(components).lower():
                components.append(keyword)
        
        # Add material if specified
        if parsed_query.get("material") and parsed_query["material"].lower() not in ' '.join(components).lower():
            components.append(parsed_query["material"])
        
        # Construct and log the final search term
        search_term = ' '.join(components)
        logger.info(f"Constructed search term: '{search_term}'")
        return search_term
    
    def apply_filters_from_query(self, parsed_query: Dict[str, Any]):
        """Apply filters based on parsed query parameters"""
        # Price filter
        if parsed_query.get("price_range"):
            min_price = parsed_query["price_range"].get("min")
            max_price = parsed_query["price_range"].get("max")
            if min_price or max_price:
                self.amazon_navigator.apply_price_filter(min_price, max_price)
                logger.info(f"Applied price filter: min={min_price}, max={max_price}")
        
        # Rating filter
        if parsed_query.get("rating_min"):
            rating_min = parsed_query["rating_min"]
            rating_int = min(4, max(1, int(rating_min)))
            self.amazon_navigator.apply_rating_filter(rating_int)
            logger.info(f"Applied rating filter: {rating_int}+ stars")
        
        # Prime filter
        if parsed_query.get("prime_shipping"):
            self.amazon_navigator.apply_prime_filter()
            logger.info("Applied Prime filter")
            
        # Give Amazon's filters time to apply
        self.browser_manager.random_delay(0.5, 1.5)