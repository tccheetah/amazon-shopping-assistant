import logging
import sys
import argparse
import time
from agent.browser_manager import BrowserManager
from agent.conversation import ConversationManager
from config.settings import LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('amazon_assistant.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Amazon Shopping Assistant V2"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Amazon Shopping Assistant V2')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--user-id', type=str, default=None, help='User ID for personalization')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with increased verbosity')
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting Amazon Shopping Assistant V2")
    
    browser_manager = BrowserManager()
    conversation = ConversationManager(browser_manager)
    
    try:
        # Initialize conversation and browser
        conversation.initialize()
        
        # Enhanced CLI interface for testing
        print("\n===== Amazon Shopping Assistant V2 =====")
        print("Introducing intelligent shopping with deep product research!")
        print("")
        print("Try commands like:")
        print("- Find me a lightweight laptop with at least 16GB RAM and good battery life under $1200")
        print("- Compare these products")
        print("- Read in-depth review analysis")
        print("- See detailed product specifications")
        print("- Which product has the best reliability?")
        print("")
        print("Type 'exit' to quit")
        print("=========================================\n")
        
        while True:
            user_input = input("\nWhat would you like to shop for? > ")
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                break
            
            # Process the message with user ID for personalization
            print("\nProcessing your request...")
            start_time = time.time()
            
            # V2: Progressive response approach
            if len(user_input.split()) > 3 and any(term in user_input.lower() for term in ['find', 'search', 'get']):
                print("Searching Amazon for matching products...")
            
            result = conversation.process_message(user_input, user_id=args.user_id)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print("\n" + result["response"])
            
            # Show processing metrics in debug mode
            if args.debug:
                print(f"\n[Debug] Processing time: {processing_time:.2f} seconds")
                if "products" in result:
                    num_products = len(result.get("products", []))
                    print(f"[Debug] Found {num_products} products")
                    
                    # Show top product scores
                    for i, product in enumerate(result.get("products", [])[:3]):
                        score = product.get("score", 0)
                        print(f"[Debug] Product {i+1} score: {score:.2f}")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        # Clean up resources
        browser_manager.close()
        logger.info("Amazon Shopping Assistant shut down")

if __name__ == "__main__":
    main()