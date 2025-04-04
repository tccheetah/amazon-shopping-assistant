import logging
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
            Return JSON with steps array containing: step_number, action (search/filter/analyze_reviews/compare), parameters
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Shopping assistant planner"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            import json
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
    
    def update_preferences(self, user_id: str, product_data: Dict):
        """Learn user preferences from selected products"""
        if not user_id:
            return
            
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {"price_ranges": {}, "brands": [], "features": []}
            
        prefs = self.user_preferences[user_id]
        
        # Update price preference for category
        category = product_data.get("category", "general")
        price = product_data.get("price_value", 0)
        if price > 0:
            prefs["price_ranges"][category] = price
            
        # Update brand preference
        brand = product_data.get("brand")
        if brand and brand not in prefs["brands"]:
            prefs["brands"].append(brand)
            
        # Update feature preferences
        features = product_data.get("features", [])
        for feature in features:
            if feature not in prefs["features"]:
                prefs["features"].append(feature)
    
    def analyze_reviews(self, reviews_text: str) -> Dict:
        """Extract key insights from product reviews"""
        try:
            prompt = f"""
            Analyze these product reviews and extract:
            1. Overall sentiment (positive/mixed/negative)
            2. Top 3 strengths mentioned
            3. Top 3 concerns mentioned
            
            Reviews: {reviews_text[:1000]}
            
            Return JSON with: sentiment, strengths (array), concerns (array)
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Review analyzer"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            import json
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error analyzing reviews: {str(e)}")
            return {"sentiment": "unknown", "strengths": [], "concerns": []}
    
    def compare_products(self, products: List[Dict]) -> Dict:
        """Generate product comparison based on key attributes"""
        try:
            if len(products) < 2:
                return {"error": "Need at least 2 products"}
                
            # Format minimal product data
            product_data = []
            for i, p in enumerate(products[:3]):
                product_data.append({
                    "id": i+1,
                    "title": p.get("title", "Unknown")[:50],
                    "price": p.get("price", "Unknown"),
                    "rating": p.get("rating", "Unknown"),
                    "prime": p.get("has_prime", False)
                })
            
            prompt = f"""
            Compare these products on price, quality, and value. Products: {product_data}
            Return JSON with: winner_overall, best_value, best_features, comparison_summary
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Product comparison expert"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            import json
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error comparing products: {str(e)}")
            return {"error": str(e)}