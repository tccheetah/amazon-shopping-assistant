import re
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class QueryParser:
    """
    Parses natural language shopping queries into structured parameters
    that can be used to filter and search products on Amazon.
    """
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def parse_shopping_query(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language shopping query into structured parameters
        For v0, we'll use a combination of regex patterns and simple rules
        to extract basic parameters that map to Amazon's filters.
        """
        try:
            # Default structure
            parsed = {
                "product_type": None,
                "price_range": {
                    "min": None,
                    "max": None
                },
                "rating_min": None,
                "prime_shipping": False,
                "keywords": []
            }
            
            # Extract product type (usually the main noun)
            product_match = re.search(r'(?:find|get|show|search for)?\s*(?:a|an|some)?\s*(.+?)(?:\s+under|\s+with|\s+that|\s+for|\s+less than|\s+above|\s+below|\s+rated|\s+by|\s+from|$)', query, re.IGNORECASE)
            if product_match:
                parsed["product_type"] = product_match.group(1).strip()
            
            # Extract price constraints
            max_price_match = re.search(r'(?:under|less than|below|max|maximum|up to)\s*\$?(\d+(?:\.\d+)?)', query, re.IGNORECASE)
            if max_price_match:
                parsed["price_range"]["max"] = float(max_price_match.group(1))
                
            min_price_match = re.search(r'(?:over|more than|above|min|minimum|starting from|at least)\s*\$?(\d+(?:\.\d+)?)', query, re.IGNORECASE)
            if min_price_match:
                parsed["price_range"]["min"] = float(min_price_match.group(1))
                
            price_range_match = re.search(r'\$?(\d+(?:\.\d+)?)\s*(?:to|-)\s*\$?(\d+(?:\.\d+)?)', query, re.IGNORECASE)
            if price_range_match:
                parsed["price_range"]["min"] = float(price_range_match.group(1))
                parsed["price_range"]["max"] = float(price_range_match.group(2))
            
            # Extract minimum rating
            rating_match = re.search(r'(?:rated|rating|stars?|reviews?)\s*(?:of|with|above|at least)?\s*(\d+(?:\.\d+)?)\+?\s*(?:stars?|or above|or higher|and above)', query, re.IGNORECASE)
            if rating_match:
                parsed["rating_min"] = float(rating_match.group(1))
                
            # Check for Prime shipping preference
            if re.search(r'(?:with)?\s*(?:prime|fast|quick|rapid|express)\s*(?:shipping|delivery)', query, re.IGNORECASE):
                parsed["prime_shipping"] = True
            
            # Extract keywords that might be important for filtering
            keyword_patterns = [
                r'(?:with|has|having|include|includes|including|contain|contains|containing)\s+(.+?)(?:\s+and|\s+with|\s+that|\s+for|\s+under|$)',
                r'(?:that is|which is|that are|which are)\s+(.+?)(?:\s+and|\s+with|\s+that|\s+for|$)'
            ]
            
            for pattern in keyword_patterns:
                keyword_match = re.search(pattern, query, re.IGNORECASE)
                if keyword_match:
                    keywords = keyword_match.group(1).strip()
                    # Split by common conjunctions and add to list
                    words = re.split(r'\s*(?:,|and|or)\s*', keywords)
                    parsed["keywords"].extend([w.strip() for w in words if w.strip()])
            
            logger.info(f"Parsed query using regex: {query}")
            return parsed
                
        except Exception as e:
            logger.error(f"Failed to parse query with regex: {str(e)}")
            # Return minimal parsed info on error
            return {
                "product_type": query,
                "price_range": {"min": None, "max": None},
                "rating_min": None,
                "prime_shipping": False,
                "keywords": []
            }