import logging
import math
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ProductAnalyzer:
    """
    Analyzes and ranks products based on user preferences and query parameters.
    For v0, implements a basic scoring system based on explicit filters.
    """
    def __init__(self):
        # Weights for different ranking factors (can be tuned)
        self.weights = {
            "rating": 0.4,      # Higher rating is better
            "reviews": 0.2,     # More reviews is better
            "price": 0.2,       # Lower price is better (within range)
            "prime": 0.1,       # Prime shipping is preferred
            "relevance": 0.1    # Title relevance to query
        }
    
    def rank_products(self, products: List[Dict[str, Any]], parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank products based on query parameters"""
        try:
            # Simple scoring system focusing on explicit preferences
            for product in products:
                score = 0
                
                # 1. Rating score (0-5 scale, normalized to 0-40 points)
                rating = product.get('rating_value', 0)
                score += rating * 8 * self.weights["rating"]
                
                # 2. Reviews score (log scale, max 20 points)
                review_count = product.get('review_count', 0)
                if review_count > 0:
                    # Log scale to prevent products with thousands of reviews from dominating
                    review_score = min(20, math.log(review_count + 1) * 2)
                    score += review_score * self.weights["reviews"]
                
                # 3. Prime shipping bonus
                if product.get('has_prime', False) and parsed_query.get('prime_shipping', False):
                    score += 10 * self.weights["prime"]
                
                # 4. Price factor (inversely proportional, max 20 points)
                price = product.get('price_value', 0)
                price_min = parsed_query.get('price_range', {}).get('min', 0)
                price_max = parsed_query.get('price_range', {}).get('max', float('inf'))
                
                if price > 0:
                    # If within specified range, give full points
                    if (price_min is None or price >= price_min) and (price_max is None or price <= price_max):
                        price_score = 20
                    else:
                        # Penalty for being outside the range
                        price_score = 5
                        
                    score += price_score * self.weights["price"]
                
                # 5. Title relevance score
                title = product.get('title', '').lower()
                product_type = parsed_query.get('product_type', '').lower()
                keywords = parsed_query.get('keywords', [])
                
                relevance_score = 0
                # Match product type
                if product_type and product_type in title:
                    relevance_score += 5
                
                # Match keywords
                for keyword in keywords:
                    if keyword.lower() in title:
                        relevance_score += 3
                
                # Cap at 10 points
                relevance_score = min(10, relevance_score)
                score += relevance_score * self.weights["relevance"]
                
                # Final score rounded to 2 decimal places
                product['score'] = round(score, 2)
            
            # Sort by score, descending
            ranked_products = sorted(products, key=lambda x: x.get('score', 0), reverse=True)
            
            logger.info(f"Ranked {len(ranked_products)} products")
            return ranked_products
            
        except Exception as e:
            logger.error(f"Failed to rank products: {str(e)}")
            return products
    
    def get_recommendation_reason(self, product: Dict[str, Any], parsed_query: Dict[str, Any]) -> str:
        """Generate a simple explanation for why this product was recommended"""
        try:
            reasons = []
            
            # Check rating
            if product.get('rating_value', 0) >= 4:
                reasons.append(f"high rating of {product.get('rating')}") 
            
            # Check reviews
            review_count = product.get('review_count', 0)
            if review_count > 1000:
                reasons.append(f"over {review_count} reviews")
            elif review_count > 100:
                reasons.append(f"{review_count} reviews")
            
            # Check price
            price_max = parsed_query.get('price_range', {}).get('max')
            if price_max and product.get('price_value', 0) <= price_max:
                reasons.append(f"within your budget of ${price_max}")
            
            # Check Prime
            if product.get('has_prime', False) and parsed_query.get('prime_shipping', False):
                reasons.append("Prime shipping")
            
            # Check keywords matches
            keywords = parsed_query.get('keywords', [])
            matching_keywords = []
            title = product.get('title', '').lower()
            
            for keyword in keywords:
                if keyword.lower() in title:
                    matching_keywords.append(keyword)
            
            if matching_keywords:
                keyword_text = ', '.join(matching_keywords)
                reasons.append(f"matches your criteria: {keyword_text}")
            
            # Construct the reason text
            if reasons:
                return "Recommended for its " + ", ".join(reasons)
            else:
                return "This product matches your search"
                
        except Exception as e:
            logger.error(f"Failed to generate recommendation reason: {str(e)}")
            return "This product matches your search"