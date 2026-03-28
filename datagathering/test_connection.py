import logging
import yaml
import os
from dotenv import load_dotenv
from thetadata import ThetaClient

logger = logging.getLogger(__name__)
load_dotenv()

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_terminal_connection():
    config = load_config()
    tickers = config.get('tickers', [])
    if not tickers:
        logger.error("No tickers found in configuration.")
        return
        
    test_ticker = tickers[0]
    logger.info(f"Testing terminal connection for ticker: {test_ticker}")
    
    try:
        # Connect to Terminal using .env credentials if set
        username = os.getenv("THETA_USERNAME")
        password = os.getenv("THETA_PASSWORD")
        if username and username != "your_pro_username":
            logger.info("Authenticating with Pro account credentials...")
            client = ThetaClient(username=username, passwd=password)
        else:
            client = ThetaClient()
        
        # Test basic retrieval (get option expirations)
        with client.connect():
            logger.info("Connected to terminal. Fetching expirations...")
            expirations = client.get_expirations(test_ticker)
            logger.info(f"Successfully connected to Theta Terminal.")
            logger.info(f"Retrieved {len(expirations)} expirations for {test_ticker}: {expirations[:5]}...")
        
    except Exception as e:
        logger.error(f"Failed to connect to Theta terminal or fetch data: {e}")
        logger.error("Please ensure the Theta Terminal is running on your machine.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_terminal_connection()
