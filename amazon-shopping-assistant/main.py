import logging
import sys
import argparse
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
    """Main entry point for the Amazon Shopping Assistant"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Amazon Shopping Assistant')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--user-id', type=str, default=None, help='User ID for personalization')
    args = parser.parse_args()
    
    logger.info("Starting Amazon Shopping Assistant")
    
    browser_manager = BrowserManager()
    conversation = ConversationManager(browser_manager)
    
    try:
        # Initialize conversation and browser
        conversation.initialize()
        
        # Enhanced CLI interface for testing
        print("\n===== Amazon Shopping Assistant =====")
        print("Now with v2 enhancements!")
        print("Try commands like:")
        print("- Find me a coffee maker under $100 with good reviews")
        print("- Compare these products")
        print("- Read customer reviews")
        print("Type 'exit' to quit")
        print("=====================================\n")
        
        while True:
            user_input = input("\nWhat would you like to shop for? > ")
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                break
                
            # Process the message with user ID for personalization
            print("\nProcessing your request...")
            result = conversation.process_message(user_input, user_id=args.user_id)
            print("\n" + result["response"])
            
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