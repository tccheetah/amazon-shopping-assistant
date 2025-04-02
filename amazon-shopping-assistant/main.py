import logging
import sys
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
    logger.info("Starting Amazon Shopping Assistant")
    
    browser_manager = BrowserManager()
    conversation = ConversationManager(browser_manager)
    
    try:
        # Initialize conversation and browser
        conversation.initialize()
        
        # Simple CLI interface for testing
        print("\n===== Amazon Shopping Assistant =====")
        print("Type your shopping requests in natural language")
        print("For example: 'Find me a coffee maker under $100 with good reviews'")
        print("Type 'exit' to quit")
        print("=====================================\n")
        
        while True:
            user_input = input("\nWhat would you like to shop for? > ")
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                break
                
            # Process the message
            print("\nSearching Amazon...")
            result = conversation.process_message(user_input)
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