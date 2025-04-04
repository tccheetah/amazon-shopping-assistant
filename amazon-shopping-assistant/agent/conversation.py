import logging
import re
import json
from typing import Dict, Any, List, Optional
from .query_parser import QueryParser
from .amazon_navigator import AmazonNavigator
from .product_analyzer import ProductAnalyzer
from .browser_manager import BrowserManager
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages conversation with v2 agentic capabilities"""
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.query_parser = QueryParser()
        self.amazon_navigator = AmazonNavigator(browser_manager)
        self.product_analyzer = ProductAnalyzer()
        self.conversation_history = []
        self.current_products = []
        self.current_query = {}
        # V2 additions
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.user_preferences = {}  # For user preference learning
        self.current_plan = []      # For multi-step planning
        self.current_step = 0
    
    def initialize(self):
        """Initialize the conversation and browser"""
        self.amazon_navigator.initialize()
    
    def process_message(self, user_message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Process message with v2 planning and advanced features"""
        try:
            self.conversation_history.append({"role": "user", "content": user_message})
            
            # Determine intent
            is_followup = self.is_followup_query(user_message)
            intent = self._get_intent(user_message)
            
            # Handle different intents
            if intent == "reviews" and self.current_products:
                return self._analyze_reviews()
            elif intent == "compare" and len(self.current_products) > 1:
                return self._compare_products()
            elif is_followup:
                parsed_query = self.handle_followup_query(user_message)
                return self._execute_search(parsed_query, is_refinement=True)
            else:
                # New search with planning
                parsed_query = self.query_parser.parse_shopping_query(user_message)
                self.current_query = parsed_query
                self.current_plan = self._create_plan(user_message)
                return self._execute_search(parsed_query, user_id=user_id)
        except Exception as e:
            logger.error(f"Process message error: {str(e)}")
            return {"response": f"I encountered an issue: {str(e)}"}
    
    def _get_intent(self, message: str) -> str:
        """Get the primary intent from the message"""
        message = message.lower()
        if any(term in message for term in ["review", "what are people saying", "feedback"]):
            return "reviews"
        elif any(term in message for term in ["compare", "difference", "better"]):
            return "compare"
        return "search"
    
    def _create_plan(self, query: str) -> List[Dict]:
        """V2: Create a multi-step plan for shopping"""
        try:
            prompt = f"""
            Create a 2-3 step plan for this shopping request: "{query}"
            Return JSON with steps array containing: step_number, action (search/analyze_reviews/compare)
            """
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Shopping assistant planner"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            plan_data = json.loads(response.choices[0].message.content)
            return plan_data.get("steps", [])
        except Exception as e:
            logger.error(f"Plan creation error: {str(e)}")
            return [{"step_number": 1, "action": "search"}]
    
    def _execute_search(self, parsed_query: Dict[str, Any], is_refinement: bool = False, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute search with product analysis"""
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
        
        # V2: Update user preferences
        if user_id and ranked_products:
            self._learn_preferences(user_id, ranked_products[0], parsed_query)
        
        # Get next actions from plan
        next_actions = self._get_next_actions()
        
        # Create response
        response = self._format_search_response(ranked_products, parsed_query, is_refinement, next_actions)
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return {
            "response": response,
            "products": ranked_products,
            "parsed_query": parsed_query
        }
    
    def _analyze_reviews(self) -> Dict[str, Any]:
        """V2: Analyze product reviews with AI"""
        try:
            product = self.current_products[0]
            if not product.get("link"):
                return {"response": "I can't access this product's reviews."}
                
            # Navigate to product and reviews
            self.amazon_navigator.page.goto(product["link"])
            self.browser_manager.random_delay()
            
            # Find reviews link
            review_selectors = [
                "a[data-hook='see-all-reviews-link-foot']",
                "a.a-link-emphasis[href*='#customerReviews']",
                "a[href*='#customerReviews']"
            ]
            
            for selector in review_selectors:
                if self.amazon_navigator.page.is_visible(selector):
                    self.amazon_navigator.page.click(selector)
                    self.browser_manager.random_delay()
                    break
            
            # Get review text
            reviews = self.amazon_navigator.page.query_selector_all(
                ".a-section.review-text, .a-section.review-text-content")
            reviews_text = "\n".join([r.inner_text() for r in reviews[:8]])
            
            if not reviews_text:
                return {"response": "No reviews found for this product."}
                
            # Analyze with AI
            analysis = self._get_review_insights(reviews_text)
            
            # Format response
            response = f"Here's what customers say about {product.get('title', 'this product')}:\n\n"
            
            if "sentiment" in analysis:
                response += f"Overall sentiment: {analysis['sentiment']}\n\n"
            
            if "strengths" in analysis and analysis["strengths"]:
                response += "✅ Strengths:\n"
                for strength in analysis["strengths"][:3]:
                    response += f"• {strength}\n"
                response += "\n"
            
            if "concerns" in analysis and analysis["concerns"]:
                response += "⚠️ Concerns:\n"
                for concern in analysis["concerns"][:3]:
                    response += f"• {concern}\n"
                response += "\n"
            
            response += "Would you like to compare products or refine your search?"
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return {"response": response, "analysis": analysis}
            
        except Exception as e:
            logger.error(f"Review analysis error: {str(e)}")
            return {"response": "I had trouble analyzing reviews. Let me show you other options."}
    
    def _get_review_insights(self, reviews_text: str) -> Dict:
        """Use AI to extract insights from reviews"""
        try:
            prompt = f"""
            Analyze these product reviews and extract:
            1. Overall sentiment (positive/mixed/negative)
            2. Top 3 strengths mentioned by customers
            3. Top 3 concerns mentioned by customers
            
            Reviews: {reviews_text[:1500]}
            
            Return JSON with: sentiment, strengths (array), concerns (array)
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Review analyst"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            return json.loads(response.choices[0].message.content)
        except:
            return {"sentiment": "unknown", "strengths": [], "concerns": []}
    
    def _compare_products(self) -> Dict[str, Any]:
        """V2: Compare multiple products with AI"""
        try:
            products = self.current_products[:3]
            
            # Format for API
            product_data = []
            for i, p in enumerate(products):
                product_data.append({
                    "id": i+1,
                    "title": p.get("title", "Product " + str(i+1))[:40],
                    "price": p.get("price", "Unknown"),
                    "rating": p.get("rating", "Unknown"),
                    "prime": p.get("has_prime", False)
                })
            
            # Get comparison from AI
            comparison = self._get_comparison_analysis(product_data)
            
            # Format response
            response = "Here's how these products compare:\n\n"
            
            if "best_overall" in comparison:
                response += f"🏆 Best Overall: Product {comparison['best_overall']}\n"
            
            if "best_value" in comparison:
                response += f"💰 Best Value: Product {comparison['best_value']}\n\n"
            
            if "summary" in comparison:
                response += f"{comparison['summary']}\n\n"
            
            response += "Would you like more details about a specific product?"
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return {"response": response, "comparison": comparison}
        
        except Exception as e:
            logger.error(f"Comparison error: {str(e)}")
            return {"response": "I had trouble comparing these products."}
    
    def _get_comparison_analysis(self, products: List[Dict]) -> Dict:
        """Use AI to compare products"""
        try:
            prompt = f"""
            Compare these products:
            {json.dumps(products)}
            
            Return JSON with: best_overall (number), best_value (number), summary (text)
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Product comparison expert"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            return json.loads(response.choices[0].message.content)
        except:
            return {"summary": "Unable to generate detailed comparison."}
    
    def _learn_preferences(self, user_id: str, product: Dict, query: Dict) -> None:
        """V2: Learn user preferences from selections"""
        try:
            if user_id not in self.user_preferences:
                self.user_preferences[user_id] = {"price_ranges": {}, "brands": [], "features": []}
            
            prefs = self.user_preferences[user_id]
            
            # Update price preference by category
            category = query.get("product_type", "general")
            price = product.get("price_value", 0)
            if price > 0:
                prefs["price_ranges"][category] = price
            
            # Extract potential brand and features
            title = product.get("title", "").lower()
            words = title.split()
            if words and len(words[0]) > 2:
                brand = words[0].capitalize()
                if brand not in prefs["brands"]:
                    prefs["brands"].append(brand)
            
            # Extract features
            common_features = ["wireless", "bluetooth", "waterproof", "portable", "digital"]
            for feature in common_features:
                if feature in title and feature not in prefs["features"]:
                    prefs["features"].append(feature)
        except:
            pass  # Silent failure for preferences
    
    def _get_next_actions(self) -> List[str]:
        """Get next steps from plan"""
        actions = []
        
        # Check plan for next steps
        if self.current_plan and self.current_step < len(self.current_plan):
            next_step = self.current_plan[self.current_step]
            self.current_step += 1
            
            action = next_step.get("action", "")
            if action == "analyze_reviews":
                actions.append("Read customer reviews")
            elif action == "compare":
                actions.append("Compare top products")
        
        # Add default actions based on context
        if len(self.current_products) > 1 and "Compare top products" not in actions:
            actions.append("Compare top products")
        
        if "Read customer reviews" not in actions and self.current_products:
            actions.append("Read customer reviews")
            
        return actions
    
    def _format_search_response(self, products: List[Dict], parsed_query: Dict, 
                              is_refinement: bool, next_actions: List[str]) -> str:
        """Format search results with next actions"""
        if not products:
            return "I couldn't find products matching your request. Would you like to try different terms?"
        
        if is_refinement:
            intro = "Here are the refined results based on your request:"
        else:
            product_type = parsed_query.get("product_type", "products")
            intro = f"I found these {product_type} that match your criteria:"
        
        response_parts = [intro]
        
        # Add top products
        for i, product in enumerate(products[:3], 1):
            product_details = f"\n{i}. {product.get('title', 'Unknown product')}\n"
            product_details += f"   • Price: {product.get('price', 'Price not available')}\n"
            product_details += f"   • Rating: {product.get('rating', 'No ratings')}\n"
            product_details += f"   • {'✓ Prime shipping' if product.get('has_prime', False) else 'Standard shipping'}\n"
            
            if product.get('recommendation_reason'):
                product_details += f"   • {product['recommendation_reason']}"
            
            response_parts.append(product_details)
        
        # Add next actions
        if next_actions:
            response_parts.append("\nWhat would you like to do next?")
            for action in next_actions:
                response_parts.append(f"• {action}")
        
        return "\n".join(response_parts)
    
    # The following methods remain mostly the same as v1
    def is_followup_query(self, message: str) -> bool:
        if len(self.conversation_history) < 2:
            return False
        followup_phrases = ["show me", "more details", "reviews", "cheaper", "better"]
        message_lower = message.lower()
        for phrase in followup_phrases:
            if phrase in message_lower:
                return True
        return len(message.split()) < 4 and not any(term in message_lower for term in ["find", "search", "get"])
        
    def handle_followup_query(self, message: str) -> Dict[str, Any]:
        modified_query = self.current_query.copy()
        message_lower = message.lower()
        
        # Price refinements
        if any(term in message_lower for term in ["cheaper", "less"]):
            current_max = modified_query.get("price_range", {}).get("max")
            if current_max:
                modified_query["price_range"]["max"] = current_max * 0.8
        
        # Other refinements (rating, prime, etc.) - similar to v1
        return modified_query
    
    def construct_search_term(self, parsed_query: Dict[str, Any]) -> str:
        components = []
        if parsed_query.get("product_type"):
            components.append(parsed_query["product_type"])
        for keyword in parsed_query.get("keywords", [])[:3]:
            if keyword not in ' '.join(components):
                components.append(keyword)
        return ' '.join(components)
    
    def apply_filters_from_query(self, parsed_query: Dict[str, Any]):
        # Price filter
        if parsed_query.get("price_range"):
            min_price = parsed_query["price_range"].get("min")
            max_price = parsed_query["price_range"].get("max")
            if min_price or max_price:
                self.amazon_navigator.apply_price_filter(min_price, max_price)
        
        # Rating filter
        if parsed_query.get("rating_min"):
            rating_min = parsed_query["rating_min"]
            rating_int = min(4, max(1, int(rating_min)))
            self.amazon_navigator.apply_rating_filter(rating_int)
        
        # Prime filter
        if parsed_query.get("prime_shipping"):
            self.amazon_navigator.apply_prime_filter()