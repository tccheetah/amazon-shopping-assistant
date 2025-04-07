import logging
import re
from typing import Dict, List, Any, Optional
from config.settings import AMAZON_BASE_URL
from .browser_manager import BrowserManager

logger = logging.getLogger(__name__)

class AmazonNavigator:
    """
    Handles navigation and interaction with Amazon website.
    Responsible for searching, applying filters, and extracting product data.
    """
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.page = None
        
    def initialize(self):
        """Initialize the browser and navigate to Amazon"""
        self.page = self.browser_manager.start()
        self.navigate_to_home()
        return self.page
    
    def navigate_to_home(self):
        """Navigate to Amazon homepage"""
        try:
            self.page.goto(AMAZON_BASE_URL)
            self.browser_manager.random_delay()
            logger.info("Navigated to Amazon homepage")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to Amazon: {str(e)}")
            return False
    
    def search_products(self, query: str):
        """Search for products with the given query"""
        try:
            # Clear any existing search text
            self.page.fill("input#twotabsearchtextbox", "")
            self.browser_manager.random_delay(0.5, 1.5)
            
            # Type the query with slight pauses to appear human
            for char in query:
                self.page.type("input#twotabsearchtextbox", char)
                self.browser_manager.random_delay(0.01, 0.05)
                
            self.browser_manager.random_delay()
            self.page.press("input#twotabsearchtextbox", "Enter")
            
            # Wait for search results to load
            self.page.wait_for_selector("[data-component-type='s-search-result']", timeout=10000)
            self.browser_manager.random_delay()
            
            logger.info(f"Searched for: {query}")
            return True
        except Exception as e:
            logger.error(f"Failed to search products: {str(e)}")
            return False
    
    def apply_price_filter(self, min_price: Optional[float] = None, max_price: Optional[float] = None):
        """Apply price range filter if specified"""
        try:
            # Check if price filter exists on this page
            if not self.page.is_visible("#priceRefinements"):
                logger.info("Price refinements not available on this page")
                return False
                
            if min_price is not None:
                min_input = self.page.query_selector('input[placeholder="Min"]')
                if min_input:
                    min_input.fill(str(min_price))
                    
            if max_price is not None:
                max_input = self.page.query_selector('input[placeholder="Max"]')
                if max_input:
                    max_input.fill(str(max_price))
            
            # If either price was set, click Go button
            if (min_price is not None or max_price is not None) and self.page.is_visible('span.a-button-inner input[type="submit"]'):
                self.page.click('span.a-button-inner input[type="submit"]')
                self.page.wait_for_load_state("networkidle")
                self.browser_manager.random_delay()
                logger.info(f"Applied price filter: min={min_price}, max={max_price}")
                return True
                
            return False
        except Exception as e:
            logger.error(f"Failed to apply price filter: {str(e)}")
            return False
    
    def apply_prime_filter(self):
        """Apply Amazon Prime filter"""
        try:
            # Look for Prime checkbox in different possible locations
            prime_selectors = [
                'span:has-text("Prime Eligible") >> xpath=../preceding-sibling::div//input[@type="checkbox"]',
                'span:has-text("Prime") >> xpath=../preceding-sibling::div//input[@type="checkbox"]',
                '[aria-label="Prime Eligible"]'
            ]
            
            for selector in prime_selectors:
                if self.page.is_visible(selector):
                    self.page.click(selector)
                    self.page.wait_for_load_state("networkidle")
                    self.browser_manager.random_delay()
                    logger.info("Applied Prime filter")
                    return True
            
            logger.info("Prime filter not found")
            return False
        except Exception as e:
            logger.error(f"Failed to apply Prime filter: {str(e)}")
            return False
    
    def apply_rating_filter(self, min_rating: int):
        """Apply minimum rating filter (1-4 stars)"""
        if min_rating < 1 or min_rating > 4:
            logger.warning(f"Invalid min_rating: {min_rating}. Must be between 1-4.")
            return False
            
        try:
            # Map rating value to the corresponding selector
            rating_selector_map = {
                4: 'section[aria-label="4 Stars & Up"]',
                3: 'section[aria-label="3 Stars & Up"]',
                2: 'section[aria-label="2 Stars & Up"]',
                1: 'section[aria-label="1 Star & Up"]'
            }
            
            selector = rating_selector_map.get(min_rating)
            if self.page.is_visible(selector):
                self.page.click(selector)
                self.page.wait_for_load_state("networkidle")
                self.browser_manager.random_delay()
                logger.info(f"Applied {min_rating}+ star filter")
                return True
                
            logger.info(f"{min_rating}+ star filter not found")
            return False
        except Exception as e:
            logger.error(f"Failed to apply rating filter: {str(e)}")
            return False
    
    def extract_search_results(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """Extract product information from search results page"""
        try:
            # Wait for search results to load
            self.page.wait_for_selector("[data-component-type='s-search-result']", timeout=10000)
            
            # Extract product information
            products = []
            product_elements = self.page.query_selector_all("[data-component-type='s-search-result']")
            
            for i, element in enumerate(product_elements):
                if i >= max_results:
                    break
                
                try:
                    # FIX: Multiple approaches to extract title correctly
                    title = "Unknown Title"
                    
                    # Approach 1: Standard title selector
                    title_element = element.query_selector("h2 a span")
                    if title_element:
                        title = title_element.inner_text()
                    
                    # Approach 2: Alternative selectors if the first one failed
                    if title == "Unknown Title":
                        alt_title_selectors = [
                            "h2 .a-link-normal", 
                            ".a-size-medium.a-color-base.a-text-normal",
                            ".a-size-base-plus.a-color-base.a-text-normal"
                        ]
                        for selector in alt_title_selectors:
                            alt_title_element = element.query_selector(selector)
                            if alt_title_element:
                                alt_title = alt_title_element.inner_text()
                                if alt_title and len(alt_title) > 5:  # Ensure it's not empty or too short
                                    title = alt_title
                                    break
                    
                    # Approach 3: Try to get the title from the a tag's aria-label
                    if title == "Unknown Title":
                        a_element = element.query_selector("h2 a")
                        if a_element:
                            aria_label = a_element.get_attribute("aria-label")
                            if aria_label and len(aria_label) > 5:
                                title = aria_label
                    
                    # Extract price with multiple approaches
                    price_whole_element = element.query_selector(".a-price-whole")
                    price_fraction_element = element.query_selector(".a-price-fraction")
                    price_element = element.query_selector(".a-price .a-offscreen")
                    
                    # Try different price extraction methods
                    price = "Price not available"
                    if price_element:
                        price = price_element.inner_text()
                    elif price_whole_element and price_fraction_element:
                        price = f"${price_whole_element.inner_text()}.{price_fraction_element.inner_text()}"
                    
                    # Extract rating with multiple approaches
                    rating = "No rating"
                    rating_element = element.query_selector("span.a-icon-alt")
                    if rating_element:
                        rating = rating_element.inner_text()
                    
                    # Alternative rating selector
                    if rating == "No rating":
                        alt_rating_element = element.query_selector(".a-icon-star-small .a-icon-alt")
                        if alt_rating_element:
                            rating = alt_rating_element.inner_text()
                    
                    # Extract reviews
                    reviews = "0"
                    reviews_element = element.query_selector("span.a-size-base.s-underline-text")
                    if reviews_element:
                        reviews = reviews_element.inner_text()
                    
                    # Alternative reviews selector
                    if reviews == "0":
                        alt_reviews_element = element.query_selector("a .a-size-base")
                        if alt_reviews_element:
                            reviews_text = alt_reviews_element.inner_text()
                            if reviews_text and reviews_text.replace(',', '').isdigit():
                                reviews = reviews_text
                    
                    # Extract numeric rating
                    rating_value = 0.0
                    if rating != "No rating":
                        rating_match = re.search(r'(\d+(\.\d+)?)', rating)
                        if rating_match:
                            rating_value = float(rating_match.group(1))
                    
                    # Extract link
                    link_element = element.query_selector("h2 a")
                    link = link_element.get_attribute("href") if link_element else None
                                        
                    # Ensure we have a complete URL
                    if link:
                        # Handle relative URLs
                        if link.startswith("/"):
                            full_link = f"{AMAZON_BASE_URL}{link}"
                        elif not link.startswith("http"):
                            full_link = f"{AMAZON_BASE_URL}/{link}"
                        else:
                            full_link = link
                            
                        # Clean up the URL by removing tracking parameters
                        if "?" in full_link:
                            base_url = full_link.split("?")[0]
                            full_link = base_url
                    else:
                        full_link = None

                    product["link"] = full_link
                    
                    # Extract Prime status
                    prime_element = element.query_selector("i.a-icon-prime")
                    if not prime_element:
                        prime_element = element.query_selector("span.aok-relative span.a-icon-prime")
                    has_prime = bool(prime_element)
                    
                    # Extract product image
                    img_element = element.query_selector("img.s-image")
                    img_url = img_element.get_attribute("src") if img_element else None
                    
                    product = {
                        "title": title,
                        "price": price,
                        "price_value": self._extract_price_value(price),
                        "rating": rating,
                        "rating_value": rating_value,
                        "reviews": reviews,
                        "review_count": self._extract_review_count(reviews),
                        "has_prime": has_prime,
                        "link": full_link,
                        "image": img_url
                    }
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.warning(f"Failed to extract product {i}: {str(e)}")
            
            logger.info(f"Extracted {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"Failed to extract search results: {str(e)}")
            return []
    
    def _extract_price_value(self, price_str: str) -> float:
        """Extract numeric price value from price string"""
        try:
            # Remove currency symbols and commas
            cleaned = price_str.replace('$', '').replace(',', '').replace(' ', '')
            # Try to extract the first valid number
            match = re.search(r'\d+(\.\d+)?', cleaned)
            if match:
                return float(match.group(0))
            return 0.0
        except Exception:
            return 0.0
    
    def _extract_review_count(self, reviews_str: str) -> int:
        """Extract numeric review count from reviews string"""
        try:
            # Remove commas and extract number
            cleaned = reviews_str.replace(',', '')
            match = re.search(r'(\d+)', cleaned)
            if match:
                return int(match.group(1))
            return 0
        except Exception:
            return 0