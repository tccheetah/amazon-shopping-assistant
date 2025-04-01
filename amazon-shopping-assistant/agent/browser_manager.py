import time
import random
import logging
from playwright.sync_api import sync_playwright
from config.settings import USER_AGENT, HEADLESS, DELAY_MIN, DELAY_MAX

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages browser sessions for interacting with Amazon.
    Handles browser initialization, navigation, and implements
    anti-detection measures like random delays.
    """
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def start(self):
        """Initialize the browser session with appropriate settings"""
        try:
            logger.info("Starting browser session")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=HEADLESS)
            
            # Configure context with custom user agent and viewport
            self.context = self.browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 720},
                locale="en-US"
            )
            
            # Enable JS console logging for debugging
            self.context.on("console", lambda msg: logger.debug(f"Browser console: {msg.text}"))
            
            self.page = self.context.new_page()
            return self.page
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            self.close()
            raise
    
    def close(self):
        """Close all browser resources to prevent memory leaks"""
        logger.info("Closing browser session")
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def random_delay(self, min_delay=None, max_delay=None):
        """
        Add a random delay to simulate human behavior
        Optionally override default delay range with custom values
        """
        min_delay = min_delay if min_delay is not None else DELAY_MIN
        max_delay = max_delay if max_delay is not None else DELAY_MAX
        
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"Adding random delay of {delay:.2f}s")
        time.sleep(delay)
        
    def add_human_behavior(self):
        """Add random mouse movements to appear more human-like"""
        try:
            # Move to random position on page
            page_width = self.page.viewport_size["width"]
            page_height = self.page.viewport_size["height"]
            
            # Random position avoiding edges
            x = random.randint(100, page_width - 200)
            y = random.randint(100, page_height - 200)
            
            self.page.mouse.move(x, y)
            self.random_delay(0.1, 0.3)
        except Exception as e:
            logger.warning(f"Failed to add human behavior: {str(e)}")