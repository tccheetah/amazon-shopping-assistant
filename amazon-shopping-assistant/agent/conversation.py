import logging
from typing import Dict, Any, List, Optional
from .query_parser import QueryParser
from .amazon_navigator import AmazonNavigator
from .product_analyzer import ProductAnalyzer
from .browser_manager import BrowserManager

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Manages the conversation flow between the user and the shopping assistant.
    Tracks context and handles message processing.
    """
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.query_parser = QueryParser()
        self.amazon_navigator = AmazonNavigator(browser_manager)
        self.product_analyzer = ProductAnalyzer()
        self.conversation_history = []
        self.current_products = []
        self.current_query = {}
        
    def initialize(self):
        """Initialize the conversation and browser"""
        self.amazon_navigator.initialize()
        
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process a user message and return a response"""
        try:
            # Store message in history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Check if this is a follow-up or refinement
            is_followup = self.is_followup_query(user_message)
            
            # Parse the query
            if is_followup:
                parsed_query = self.handle_followup_query(user_message)
            else:
                parsed_query = self.query_parser.parse_shopping_query(user_message)
                
            self.current_query = parsed_query
            
            # Construct search term from parsed query
            search_term = self.construct_search_term(parsed_query)
            
            # Search on Amazon
            self.amazon_navigator.search_products(search_term)
            
            # Apply filters based on parsed query
            self.apply_filters_from_query(parsed_query)
            
            # Extract results
            products = self.amazon_navigator.extract_search_results(max_results=5)
            
            # Analyze and rank products
            ranked_products = self.product_analyzer.rank_products(products, parsed_query)
            self.current_products = ranked_products
            
            # Add recommendation reasons
            for product in ranked_products:
                product['recommendation_reason'] = self.product_analyzer.get_recommendation_reason(product, parsed_query)
            
            # Create response
            response = self.format_response(ranked_products, parsed_query, is_followup)
            
            # Store response in history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return {
                "response": response,
                "products": ranked_products,
                "parsed_query": parsed_query
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            error_response = f"I encountered an issue while processing your request: {str(e)}"
            self.conversation_history.append({
                "role": "assistant",
                "content": error_response
            })
            return {
                "response": error_response,
                "error": str(e)
            }
    
    def is_followup_query(self, message: str) -> bool:
        """Determine if a message is a follow-up to previous conversation"""
        # Simple heuristics for follow-up detection
        
        # Check if this is the first message
        if len(self.conversation_history) < 2:
            return False
            
        # Check for common follow-up phrases
        followup_phrases = [
            "show me more", "more details", "tell me more", 
            "what about", "how about", "can i see", "cheaper", 
            "more expensive", "better", "higher rated", "another"
        ]
        
        message_lower = message.lower()
        for phrase in followup_phrases:
            if phrase in message_lower:
                return True
                
        # Check for very short queries that don't specify a product
        if len(message.split()) < 4 and not any(keyword in message_lower for keyword in ["find", "search", "get me", "looking for"]):
            return True
            
        return False
        
    def handle_followup_query(self, message: str) -> Dict[str, Any]:
        """Handle follow-up queries by modifying the previous query context"""
        # Start with the current query
        modified_query = self.current_query.copy()
        
        message_lower = message.lower()
        
        # Check for price refinements
        if any(term in message_lower for term in ["cheaper", "less expensive", "lower price"]):
            current_max = modified_query.get("price_range", {}).get("max")
            if current_max:
                # Reduce max price by 20%
                modified_query["price_range"]["max"] = current_max * 0.8
            else:
                # Set a reasonable max price
                modified_query["price_range"] = {"min": None, "max": 100}
                
        if any(term in message_lower for term in ["more expensive", "higher price", "premium", "better quality"]):
            current_min = modified_query.get("price_range", {}).get("min", 0)
            # Increase min price
            modified_query["price_range"]["min"] = current_min * 1.5 if current_min else 100
            
        # Check for rating refinements
        if any(term in message_lower for term in ["better rated", "higher rating", "top rated"]):
            current_rating = modified_query.get("rating_min", 0)
            modified_query["rating_min"] = max(4, current_rating + 0.5)
            
        # Check for Prime refinements
        if "prime" in message_lower:
            modified_query["prime_shipping"] = True
            
        # Extract any new keywords
        keyword_indicators = ["with", "that has", "including", "features", "made of", "contains"]
        for indicator in keyword_indicators:
            if indicator in message_lower:
                # Extract text after the indicator
                parts = message_lower.split(indicator, 1)
                if len(parts) > 1 and parts[1].strip():
                    new_keywords = [kw.strip() for kw in parts[1].split() if len(kw) > 2]
                    existing_keywords = modified_query.get("keywords", [])
                    modified_query["keywords"] = list(set(existing_keywords + new_keywords))
        
        return modified_query
    
    def construct_search_term(self, parsed_query: Dict[str, Any]) -> str:
        """Construct a search term from the parsed query for Amazon's search box"""
        components = []
        
        # Start with the product type
        if parsed_query.get("product_type"):
            components.append(parsed_query["product_type"])
            
        # Add important keywords
        for keyword in parsed_query.get("keywords", [])[:3]:  # Limit to top 3 keywords
            if keyword not in ' '.join(components):
                components.append(keyword)
                
        return ' '.join(components)
        
    def apply_filters_from_query(self, parsed_query: Dict[str, Any]):
        """Apply appropriate Amazon filters based on parsed query"""
        # Apply price filter if specified
        if parsed_query.get("price_range"):
            min_price = parsed_query["price_range"].get("min")
            max_price = parsed_query["price_range"].get("max")
            if min_price or max_price:
                self.amazon_navigator.apply_price_filter(min_price, max_price)
                
        # Apply rating filter if specified
        if parsed_query.get("rating_min"):
            rating_min = parsed_query["rating_min"]
            # Amazon only has whole number ratings (4 stars & up, 3 stars & up, etc.)
            rating_int = min(4, max(1, int(rating_min)))
            self.amazon_navigator.apply_rating_filter(rating_int)
            
        # Apply Prime filter if requested
        if parsed_query.get("prime_shipping"):
            self.amazon_navigator.apply_prime_filter()
    
    def format_response(self, products: List[Dict[str, Any]], parsed_query: Dict[str, Any], is_followup: bool) -> str:
        """Format products into a user-friendly response"""
        if not products:
            return "I couldn't find any products matching your request. Would you like to try different search terms or criteria?"
        
        # Construct intro message
        if is_followup:
            intro = "Here are the updated results based on your request:"
        else:
            product_type = parsed_query.get("product_type", "products")
            intro = f"I found some {product_type} that match your criteria:"
        
        response_parts = [intro]
        
        # Add products
        for i, product in enumerate(products[:3], 1):
            price = product.get('price', 'Price not available')
            rating = product.get('rating', 'No ratings')
            prime = "✓ Prime shipping" if product.get('has_prime', False) else "Standard shipping"
            reason = product.get('recommendation_reason', '')
            
            product_details = f"\n{i}. {product.get('title', 'Unknown product')}\n"
            product_details += f"   • Price: {price}\n"
            product_details += f"   • Rating: {rating}\n"
            product_details += f"   • {prime}\n"
            if reason:
                product_details += f"   • {reason}"
            
            response_parts.append(product_details)
        
        # Add suggestions for next steps
        response_parts.append("\nYou can:")
        
        # Add detail suggestion
        response_parts.append("• Ask for more details about any product")
        
        # Add refined search suggestions based on context
        suggestions = []
        
        if not parsed_query.get("prime_shipping"):
            suggestions.append("• Filter for Prime shipping")
        
        price_max = parsed_query.get("price_range", {}).get("max")
        if price_max:
            suggestions.append(f"• Look for cheaper options under ${int(price_max * 0.8)}")
        else:
            suggestions.append("• Set a price range")
        
        if not parsed_query.get("rating_min") or parsed_query.get("rating_min") < 4:
            suggestions.append("• Find better rated products")
            
        response_parts.extend(suggestions)
        
        return "\n".join(response_parts)