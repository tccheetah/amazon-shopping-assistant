import logging
import re
import json
from typing import Dict, List, Any, Optional
from config.settings import AMAZON_BASE_URL
from .browser_manager import BrowserManager
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class ProductResearcher:
    """
    V2 enhancement: Performs deep research on individual products
    by examining product pages, reviews, and specifications.
    """
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.page = None
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    def initialize(self, page):
        """Initialize with browser page"""
        self.page = page
        
    def research_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive research on a single product"""
        result = {
            "title": product.get("title", "Unknown"),
            "basic_info": product,
            "specifications": {},
            "review_analysis": {},
            "detailed_description": "",
            "pros_cons": {"pros": [], "cons": []}
        }
        
        try:
            # Navigate to product page
            if not product.get("link"):
                logger.warning("No product link available for research")
                return result
                
            self.page.goto(product["link"])
            self.browser_manager.random_delay()
            logger.info(f"Researching product: {product.get('title', 'Unknown')}")
            
            # 1. Extract detailed specifications
            result["specifications"] = self._extract_specifications()
            
            # 2. Extract product description
            result["detailed_description"] = self._extract_product_description()
            
            # 3. Analyze reviews in depth
            result["review_analysis"] = self._analyze_reviews_in_depth()
            
            # 4. Generate pros and cons with AI
            result["pros_cons"] = self._generate_pros_cons(
                result["specifications"], 
                result["detailed_description"],
                result["review_analysis"]
            )
            
            logger.info("Product research completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error researching product: {str(e)}")
            return result
    
    def _extract_specifications(self) -> Dict[str, Any]:
        """Extract detailed product specifications"""
        specs = {}
        try:
            # Look for specification table (multiple possible selectors)
            spec_selectors = [
                "#productDetails_techSpec_section_1",
                "#prodDetails",
                ".a-section.a-spacing-small.a-spacing-top-small > table",
                "#detailBullets_feature_div"
            ]
            
            for selector in spec_selectors:
                if self.page.is_visible(selector):
                    # Table-based specs
                    rows = self.page.query_selector_all(f"{selector} tr")
                    for row in rows:
                        # Try to get key and value
                        key_element = row.query_selector("th")
                        value_element = row.query_selector("td")
                        
                        if key_element and value_element:
                            key = key_element.inner_text().strip()
                            value = value_element.inner_text().strip()
                            specs[key] = value
                    
                    # If we found specs, break out
                    if specs:
                        break
            
            # Bullet-based specs
            if not specs:
                bullet_items = self.page.query_selector_all("#detailBullets_feature_div .a-list-item")
                for item in bullet_items:
                    text = item.inner_text().strip()
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        specs[key] = value
            
            # Extract key specs from various elements
            key_specs = {
                "RAM": self._extract_spec_value(["RAM", "Memory"]),
                "Storage": self._extract_spec_value(["Storage", "SSD", "HDD", "Hard Drive"]),
                "Processor": self._extract_spec_value(["Processor", "CPU"]),
                "Display": self._extract_spec_value(["Display", "Screen", "Monitor"]),
                "Battery": self._extract_spec_value(["Battery", "Battery Life"]),
                "Weight": self._extract_spec_value(["Weight", "Item Weight"])
            }
            
            # Combine extracted specs
            for key, value in key_specs.items():
                if value and key not in specs:
                    specs[key] = value
            
            logger.info(f"Extracted {len(specs)} specifications")
            return specs
            
        except Exception as e:
            logger.error(f"Error extracting specifications: {str(e)}")
            return specs
    
    def _extract_spec_value(self, keywords: List[str]) -> Optional[str]:
        """Extract a specific specification value by keywords"""
        selectors = [
            "#productDetails_techSpec_section_1",
            "#prodDetails",
            "#feature-bullets",
            "#detailBullets_feature_div",
            "#productDescription"
        ]
        
        for selector in selectors:
            if not self.page.is_visible(selector):
                continue
                
            element_text = self.page.query_selector(selector).inner_text().lower()
            
            for keyword in keywords:
                pattern = rf'{re.escape(keyword.lower())}[:\s]+([^,\n\r]+)'
                match = re.search(pattern, element_text)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def _extract_product_description(self) -> str:
        """Extract the product description"""
        description = ""
        try:
            # Try multiple possible selectors
            description_selectors = [
                "#productDescription",
                "#feature-bullets",
                ".a-section.a-spacing-medium.a-spacing-top-small"
            ]
            
            for selector in description_selectors:
                if self.page.is_visible(selector):
                    description += self.page.query_selector(selector).inner_text().strip() + "\n"
            
            logger.info(f"Extracted product description ({len(description)} chars)")
            return description
            
        except Exception as e:
            logger.error(f"Error extracting product description: {str(e)}")
            return description
    
    def _analyze_reviews_in_depth(self) -> Dict[str, Any]:
        """Analyze reviews with deeper insights"""
        result = {
            "sentiment": "unknown",
            "strengths": [],
            "concerns": [],
            "longevity": "unknown",
            "verified_purchases": 0,
            "recent_reviews": [],
            "common_themes": []
        }
        
        try:
            # Navigate to reviews page
            review_selectors = [
                "a[data-hook='see-all-reviews-link-foot']",
                "a.a-link-emphasis[href*='#customerReviews']",
                "a[href*='#customerReviews']"
            ]
            
            for selector in review_selectors:
                if self.page.is_visible(selector):
                    self.page.click(selector)
                    self.browser_manager.random_delay()
                    break
            
            # Count verified purchases
            verified_elements = self.page.query_selector_all(".a-color-state:text('Verified Purchase')")
            result["verified_purchases"] = len(verified_elements)
            
            # Extract review dates
            date_elements = self.page.query_selector_all("[data-hook='review-date']")
            review_dates = [e.inner_text() for e in date_elements[:5]]
            result["recent_reviews"] = review_dates
            
            # Extract review texts
            reviews = self.page.query_selector_all(
                ".a-section.review-text, .a-section.review-text-content")
            reviews_text = "\n".join([r.inner_text() for r in reviews[:10]])
            
            if not reviews_text:
                logger.warning("No review text found")
                return result
            
            # AI-powered review analysis
            ai_analysis = self._get_review_insights(reviews_text)
            
            # Update result with AI analysis
            result.update(ai_analysis)
            
            logger.info("Completed in-depth review analysis")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing reviews: {str(e)}")
            return result
    
    def _get_review_insights(self, reviews_text: str) -> Dict[str, Any]:
        """Use AI to extract deeper insights from reviews"""
        try:
            prompt = f"""
            Analyze these product reviews in depth and extract:
            1. Overall sentiment (positive/mixed/negative)
            2. Top 5 specific strengths mentioned by multiple reviewers
            3. Top 5 specific concerns or issues mentioned by reviewers
            4. Assessment of product longevity/durability (excellent/good/average/poor/unknown)
            5. Common themes across reviews
            6. Any mentions of customer service quality
            7. Any comparison to competing products
            
            Reviews: {reviews_text[:3000]}
            
            Return JSON with: 
            - sentiment: string
            - strengths: array of strings
            - concerns: array of strings
            - longevity: string
            - common_themes: array of strings
            - customer_service: string or null
            - competitor_mentions: array of strings or null
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Expert product review analyst"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"AI review analysis error: {str(e)}")
            return {
                "sentiment": "unknown",
                "strengths": [],
                "concerns": [],
                "longevity": "unknown",
                "common_themes": []
            }
    
    def _generate_pros_cons(self, specs: Dict[str, Any], description: str, reviews: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate comprehensive pros and cons using all collected data"""
        try:
            # Prepare context
            context = {
                "specifications": specs,
                "description_excerpt": description[:500],
                "review_strengths": reviews.get("strengths", []),
                "review_concerns": reviews.get("concerns", []),
                "review_sentiment": reviews.get("sentiment", "unknown")
            }
            
            prompt = f"""
            Based on this product data, generate a comprehensive list of pros and cons:
            {json.dumps(context)}
            
            Return JSON with:
            - pros: Array of specific advantages (5-7 items)
            - cons: Array of specific disadvantages (3-5 items)
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Expert product analyst"}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error generating pros/cons: {str(e)}")
            return {"pros": [], "cons": []}

    def compare_multiple_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform deep comparison of multiple products based on research"""
        if len(products) < 2:
            return {"error": "Need at least 2 products for comparison"}
            
        try:
            product_data = []
            
            # Research each product first
            for product in products[:3]:
                research = self.research_product(product)
                product_data.append({
                    "title": product.get("title", "Unknown"),
                    "price": product.get("price", "Unknown"),
                    "rating": product.get("rating", "Unknown"),
                    "specs": research["specifications"],
                    "pros": research["pros_cons"]["pros"],
                    "cons": research["pros_cons"]["cons"],
                    "review_sentiment": research["review_analysis"].get("sentiment", "unknown"),
                    "longevity": research["review_analysis"].get("longevity", "unknown")
                })
            
            # Generate AI comparison
            prompt = f"""
            Compare these products in depth, considering specifications, price, reviews, and overall value:
            {json.dumps(product_data)}
            
            Return JSON with:
            - best_choice: Object with reason and product_index
            - best_value: Object with reason and product_index
            - feature_comparison: Array of feature objects with name and winner_index
            - reliability_comparison: Assessment of reliability for each product
            - price_analysis: Value assessment considering features and price
            - recommendation: Which type of user would prefer each product
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Expert product comparison analyst"}, 
                        {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            comparison_data = json.loads(response.choices[0].message.content)
            return comparison_data
            
        except Exception as e:
            logger.error(f"Error in deep product comparison: {str(e)}")
            return {"error": str(e)}