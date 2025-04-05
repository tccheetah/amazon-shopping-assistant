import logging
import time
import json
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class AgentFramework:
    """V2 enhancement: Agent framework for planning, reasoning and executing multi-step workflows"""
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.user_preferences = {}
        self.current_plan = []
        self.current_step = 0
    
    def create_plan(self, query: str, user_id: Optional[str] = None) -> List[Dict]:
        """Create a multi-step plan for handling a shopping query"""
        try:
            # Use preferences if available
            user_context = ""
            if user_id and user_id in self.user_preferences:
                user_context = f"User preferences: {self.user_preferences[user_id]}"
            
            prompt = f"""
            Create a 2-3 step plan for this shopping request: "{query}" {user_context}
            Consider these possible actions:
            1. search - Initial product search
            2. filter - Apply additional filters
            3. analyze_reviews - Analyze customer reviews
            4. compare - Compare multiple products
            5. recommend - Make a final recommendation
            
            Return JSON with steps array containing: 
            - step_number: Integer
            - action: String (one of the above)
            - parameters: Object with relevant parameters
            - reasoning: String explaining why this step is needed
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Shopping assistant planner"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            plan_data = json.loads(response.choices[0].message.content)
            self.current_plan = plan_data.get("steps", [])
            self.current_step = 0
            
            logger.info(f"Created plan with {len(self.current_plan)} steps")
            return self.current_plan
            
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            # Fallback to basic plan
            return [{"step_number": 1, "action": "search", "parameters": {"query": query}}]
    
    def get_next_step(self) -> Dict:
        """Get the next step in the current plan"""
        if not self.current_plan or self.current_step >= len(self.current_plan):
            return None
            
        step = self.current_plan[self.current_step]
        self.current_step += 1
        return step
    
    def update_preferences(self, user_id: str, product_data: Dict, query_data: Dict, action: str = "viewed"):
        """Learn user preferences from interactions"""
        if not user_id:
            return
            
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "price_ranges": {},
                "brands": [], 
                "features": [],
                "categories": {},
                "interactions": []
            }
            
        prefs = self.user_preferences[user_id]
        
        # Update price preference for category
        category = product_data.get("category", query_data.get("product_type", "general"))
        price = product_data.get("price_value", 0)
        
        # Weight preferences by action type
        action_weights = {
            "viewed": 1,
            "compared": 2,
            "added_to_cart": 3,
            "purchased": 5
        }
        weight = action_weights.get(action, 1)
        
        # Update category preference strength
        if category not in prefs["categories"]:
            prefs["categories"][category] = weight
        else:
            prefs["categories"][category] += weight
        
        # Update price range preference
        if price > 0:
            if category not in prefs["price_ranges"]:
                prefs["price_ranges"][category] = price
            else:
                # Weighted average of prices
                current = prefs["price_ranges"][category]
                prefs["price_ranges"][category] = (current + (price * weight)) / (1 + weight)
                
        # Update brand preference
        brand = product_data.get("brand")
        if brand:
            # Check if brand exists
            brand_exists = False
            for b in prefs["brands"]:
                if isinstance(b, dict) and b.get("name") == brand:
                    b["weight"] += weight
                    brand_exists = True
                    break
                elif isinstance(b, str) and b == brand:
                    # Convert old format to new format
                    prefs["brands"].remove(b)
                    prefs["brands"].append({"name": brand, "weight": weight})
                    brand_exists = True
                    break
                    
            if not brand_exists:
                prefs["brands"].append({"name": brand, "weight": weight})
        
        # Extract and update feature preferences
        features = self._extract_features(product_data)
        for feature in features:
            feature_exists = False
            for f in prefs["features"]:
                if isinstance(f, dict) and f.get("name") == feature:
                    f["weight"] += weight
                    feature_exists = True
                    break
                elif isinstance(f, str) and f == feature:
                    # Convert old format to new format
                    prefs["features"].remove(f)
                    prefs["features"].append({"name": feature, "weight": weight})
                    feature_exists = True
                    break
                    
            if not feature_exists:
                prefs["features"].append({"name": feature, "weight": weight})
        
        # Record interaction for future analysis
        prefs["interactions"].append({
            "timestamp": time.time(),
            "product_id": product_data.get("asin", "unknown"),
            "action": action,
            "category": category
        })
        
        # Prune old interactions
        if len(prefs["interactions"]) > 100:
            prefs["interactions"] = prefs["interactions"][-100:]
    
    def _extract_features(self, product_data: Dict) -> List[str]:
        """Extract features from product data"""
        features = []
        title = product_data.get("title", "").lower()
        
        # Common feature patterns by category
        patterns = {
            "laptop": ["ram", "processor", "ssd", "hdd", "display", "screen", "battery", "graphics"],
            "phone": ["storage", "camera", "battery", "display", "processor", "ram"],
            "general": ["wireless", "bluetooth", "waterproof", "portable", "digital"]
        }
        
        category = product_data.get("category", "general")
        feature_words = patterns.get(category, patterns["general"])
        
        for word in feature_words:
            if word in title:
                # Try to extract specification with the feature
                pattern = rf'(\d+(?:\.\d+)?\s*(?:GB|TB|MP|GHz|inch|hours)?\s*{re.escape(word)})'
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    features.append(match.group(0))
                else:
                    features.append(word)
                    
        return features
    
    def analyze_reviews(self, reviews_text: str) -> Dict:
        """Extract key insights from product reviews"""
        try:
            prompt = f"""
            Analyze these product reviews and extract:
            1. Overall sentiment (positive/mixed/negative)
            2. Top 3 strengths mentioned
            3. Top 3 concerns mentioned
            4. Most frequently mentioned features
            5. Reliability assessment (very reliable, reliable, questionable, unreliable)
            
            Reviews: {reviews_text[:2000]}
            
            Return JSON with: sentiment, strengths (array), concerns (array), features (array), reliability
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Review analyzer"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error analyzing reviews: {str(e)}")
            return {"sentiment": "unknown", "strengths": [], "concerns": [], "features": [], "reliability": "unknown"}
    
    def compare_products(self, products: List[Dict]) -> Dict:
        """Generate product comparison based on key attributes"""
        try:
            if len(products) < 2:
                return {"error": "Need at least 2 products"}
                
            # Prepare product data with feature extraction
            product_data = []
            for i, p in enumerate(products[:3]):
                # Extract key features from title
                features = []
                title = p.get("title", "Unknown")
                for keyword in ["RAM", "processor", "CPU", "battery", "display", "weight", "storage", "SSD", "resolution"]:
                    if keyword.lower() in title.lower():
                        pattern = r'(\d+(?:\.\d+)?\s*(?:GB|TB|GHz|inch|hours|lbs)?\s*' + keyword + r')'
                        match = re.search(pattern, title, re.IGNORECASE)
                        if match:
                            features.append(match.group(0))
                
                product_data.append({
                    "id": i+1,
                    "title": p.get("title", "Unknown")[:50],
                    "price": p.get("price", "Unknown"),
                    "rating": p.get("rating", "Unknown"),
                    "features": features,
                    "prime": p.get("has_prime", False)
                })
            
            prompt = f"""
            Compare these products on price, quality, and value for a shopper. Products: 
            {json.dumps(product_data)}
            
            Return JSON with: 
            - best_overall: ID of best overall product
            - best_value: ID of best value product
            - comparison_table: Array of feature comparisons
            - summary: Detailed analysis of strengths and weaknesses
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Product comparison expert"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error comparing products: {str(e)}")
            return {"error": str(e)}
    
    def parse_query_with_ai(self, query: str) -> Dict:
        """Use AI to parse shopping query with advanced understanding"""
        try:
            if not OPENAI_API_KEY:
                # Fallback to regex parser
                from agent.query_parser import QueryParser
                return QueryParser().parse_shopping_query(query)
                
            prompt = f"""
            Parse this shopping query into structured parameters:
            "{query}"
            
            Return JSON with:
            - product_type: Main product category
            - price_range: {{min, max}} (numbers)
            - keywords: Array of important features or requirements
            - rating_min: Minimum star rating (number)
            - prime_shipping: Boolean if Prime is requested
            - exact_rating_min: Precise rating threshold if specified
            - material: Material requirement if specified
            - origin_country: Country of origin if specified
            - excluded_terms: Terms to exclude
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Shopping query analyzer"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"AI parsing failed: {str(e)}")
            # Fallback to regex parsing
            from agent.query_parser import QueryParser
            return QueryParser().parse_shopping_query(query)
    
    def suggest_refinements(self, query_data: Dict, products: List[Dict]) -> List[str]:
        """Suggest potential refinements based on initial results"""
        try:
            if not products:
                return ["Try different search terms", "Expand your price range"]
                
            suggestions = []
            
            # Price-based suggestions
            prices = [p.get("price_value", 0) for p in products if p.get("price_value", 0) > 0]
            if prices:
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                
                price_range_min = query_data.get("price_range", {}).get("min", 0)
                price_range_max = query_data.get("price_range", {}).get("max", float('inf'))
                
                if price_range_max and avg_price > price_range_max * 0.9:
                    suggestions.append(f"Increase your budget (most items are around ${avg_price:.2f})")
                elif price_range_min and min_price > price_range_min * 1.5:
                    suggestions.append(f"Might need a higher budget (cheapest item is ${min_price:.2f})")
            
            # Rating-based suggestions
            ratings = [p.get("rating_value", 0) for p in products if p.get("rating_value", 0) > 0]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                if avg_rating < 4.0:
                    suggestions.append("Consider higher-rated alternatives")
            
            # Feature-based suggestions
            product_type = query_data.get("product_type", "")
            if product_type == "laptop":
                if not any("SSD" in p.get("title", "") for p in products):
                    suggestions.append("Specify SSD storage for faster performance")
                if not any("RAM" in p.get("title", "") for p in products):
                    suggestions.append("Specify RAM requirements")
            
            # Prime shipping suggestion
            if not query_data.get("prime_shipping") and any(p.get("has_prime") for p in products):
                suggestions.append("Filter for Prime shipping")
            
            # Add general suggestions if needed
            if len(suggestions) < 2:
                suggestions.append("Sort by customer ratings")
                
            return suggestions[:3]  # Limit to top 3 suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return ["Refine your search terms", "Try a different price range"]