import logging
import yaml
import os
from dotenv import load_dotenv
from thetadata import ThetaClient, DataType, OptionReqType, OptionRight

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Mock function for Phase 2 - REDIS push
def push_to_phase_2(symbol, spread_type, details):
    """
    Pushes the anomaly or valid spread to the next phase.
    """
    logger.info(f"PHASE 2 QUEUE | SIGNAL DETECTED: {symbol} | Type: {spread_type} | Details: {details}")

def apply_spread_cap(raw_spread: float, strike_diff: float, bound: float = 0.01) -> float:
    """
    Every spread must be capped so that its value is never zero, negative, or equal to the full strike width.
    """
    return max(bound, min(raw_spread, strike_diff - bound))

def start_option_chain_monitor():
    """
    Connects to the local Theta Terminal and streams NBBO ticks, or fetches historical for testing.
    """
    config = load_config()
    tickers = config.get('tickers', [])
    
    if not tickers:
        logger.error("No tickers configured.")
        return

    try:
        # Load Pro credentials if present
        username = os.getenv("THETA_USERNAME")
        password = os.getenv("THETA_PASSWORD")
        if username and username != "your_pro_username":
            logger.info("Initializing ThetaClient with Pro credentials...")
            client = ThetaClient(username=username, passwd=password)
        else:
            logger.info("Initializing default ThetaClient (Free connection)...")
            client = ThetaClient()
    except Exception as e:
        logger.error(f"Failed to connect to Theta Client: {e}")
        return
    
    data_mode = os.getenv("DATA_GATHER_MODE", "STREAMING")
    
    if data_mode == "HISTORICAL":
        logger.info("HISTORICAL MODE ACTIVATED - Fetching test option data...")
        test_ticker = os.getenv("HIST_TEST_TICKER", tickers[0])
        test_exp = os.getenv("HIST_TEST_EXP", "20240119")
        test_strike = int(os.getenv("HIST_TEST_STRIKE", "150"))
        right_str = os.getenv("HIST_TEST_RIGHT", "C")
        test_right = OptionRight.CALL if right_str.upper() == 'C' else OptionRight.PUT
        
        try:
            from datetime import date
            from thetadata import DateRange
            
            # Immediate test using get_hist_option to bypass FPSS requirement
            logger.info(f"Requesting historical quotes for {test_ticker} {test_exp} {test_strike}{right_str}")
            
            exp_date = date(int(str(test_exp)[:4]), int(str(test_exp)[4:6]), int(str(test_exp)[6:]))
            
            with client.connect():
                logger.info("Connected to terminal! Fetching data...")
                res = client.get_hist_option(
                    req=OptionReqType.QUOTE,
                    root=test_ticker,
                    exp=exp_date,
                    strike=float(test_strike),
                    right=test_right,
                    date_range=DateRange.from_days(1) # Fetch the last available day of data
                )
                logger.info("Successfully fetched historical data!")
                # The result is automatically a pandas DataFrame in thetadata
                logger.info(f"Retrieved {len(res)} rows. Showing first 5:")
                logger.info("\n" + str(res.head() if hasattr(res, 'head') else res))
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            
    else:
        logger.info(f"Starting option root monitor (STREAMING) for symbols: {tickers}")
        try:
            with client.connect():
                for symbol in tickers:
                    logger.info(f"Subscribing to option root stream for {symbol}...")
                    with client.get_snapshot(
                        req=OptionReqType.QUOTE,
                        root=symbol
                    ) as stream:
                        logger.info(f"Stream started successfully for {symbol}. Waiting for ticks...")
                        for tick in stream:
                            bid = tick[DataType.BID]
                            ask = tick[DataType.ASK]
                            mid = (bid + ask) / 2
                            pass
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user.")
        except Exception as e:
            logger.error(f"Error during streaming: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_option_chain_monitor()
