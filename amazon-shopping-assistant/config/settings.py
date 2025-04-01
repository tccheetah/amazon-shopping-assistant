import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Browser settings
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"

# Rate limiting
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
DELAY_MIN = float(os.getenv("DELAY_MIN", 1))
DELAY_MAX = float(os.getenv("DELAY_MAX", 3))

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Amazon specific
AMAZON_BASE_URL = "https://www.amazon.com"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")