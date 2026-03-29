"""
Interactive Brokers provider stub.

This is a STUB implementation showing how to integrate IBKR.

Requirements:
  - IB Gateway or TWS running locally
  - ib_insync: pip install ib_insync
  
Configuration (.env):
  IBKR_HOST=127.0.0.1    # Default: localhost
  IBKR_PORT=7497         # 7497=live TWS, 7496=paper TWS, 4002=Gateway
  IBKR_CLIENT_ID=1       # Unique client ID
  
Usage:
  1. Start IB Gateway or TWS
  2. Enable API connections in settings
  3. Set DATA_PROVIDER=ibkr
  4. Run pipeline

TODO:
  [ ] Install ib_insync: pip install ib_insync
  [ ] Implement connection logic
  [ ] Implement option chain fetching
  [ ] Add error handling
  [ ] Add rate limiting
  [ ] Test with live market data
"""
import os
import logging
from typing import List
from dotenv import load_dotenv
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

load_dotenv()
logger = logging.getLogger(__name__)


class IBKRProvider(BaseProvider):
    """Interactive Brokers provider via IB API."""
    
    def __init__(self):
        self.host = os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = int(os.getenv("IBKR_PORT", "7497"))
        self.client_id = int(os.getenv("IBKR_CLIENT_ID", "1"))
        self.ib = None
    
    @property
    def name(self) -> str:
        return "ibkr"
    
    def _connect(self):
        """Connect to IB Gateway or TWS."""
        if self.ib is not None:
            return  # Already connected
        
        try:
            from ib_insync import IB
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            logger.info(f"[ibkr] Connected to {self.host}:{self.port}")
        except ImportError:
            logger.error("[ibkr] ib_insync not installed: pip install ib_insync")
            self.ib = None
        except Exception as e:
            logger.error(f"[ibkr] Connection failed: {e}")
            self.ib = None
    
    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        """
        Fetch option chain from Interactive Brokers.
        
        TODO: Complete implementation
        
        Steps:
          1. Connect to IB Gateway
          2. Qualify underlying contract
          3. Request option chain parameters
          4. For each expiration/strike/right:
             - Create option contract
             - Request market data (bid/ask/volume)
             - Convert to StandardOptionTick
          5. Return list of ticks
        """
        logger.warning("[ibkr] STUB: fetch_chain() not implemented yet")
        logger.info("[ibkr] To implement:")
        logger.info("[ibkr]   1. Install: pip install ib_insync")
        logger.info("[ibkr]   2. Start IB Gateway or TWS")
        logger.info("[ibkr]   3. Enable API connections")
        logger.info("[ibkr]   4. Complete fetch_chain() implementation")
        
        return []


# Example implementation (commented out - for reference):
"""
def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
    self._connect()
    
    if not self.ib or not self.ib.isConnected():
        logger.error("[ibkr] Not connected to IB Gateway")
        return []
    
    ticks = []
    
    try:
        from ib_insync import Stock, Option
        
        # 1. Define underlying
        stock = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(stock)
        
        # 2. Get option chain parameters
        chains = self.ib.reqSecDefOptParams(
            stock.symbol, '', stock.secType, stock.conId
        )
        
        if not chains:
            logger.warning(f"[ibkr] No option chains for {ticker}")
            return []
        
        # 3. Use first exchange (typically SMART)
        chain = chains[0]
        
        # 4. For each expiration and strike
        for exp in chain.expirations:
            for strike in chain.strikes:
                for right in ['C', 'P']:
                    # 5. Create option contract
                    contract = Option(
                        ticker, exp, strike, right, chain.exchange
                    )
                    
                    # 6. Qualify and request market data
                    self.ib.qualifyContracts(contract)
                    ticker_data = self.ib.reqMktData(contract, '', False, False)
                    
                    # 7. Wait for data (rate limit)
                    self.ib.sleep(0.05)
                    
                    # 8. Convert to StandardOptionTick
                    if ticker_data.bid and ticker_data.ask:
                        tick = StandardOptionTick.make(
                            root=ticker,
                            expiration=exp,
                            strike=float(strike),
                            right=right,
                            bid=float(ticker_data.bid),
                            ask=float(ticker_data.ask),
                            volume=int(ticker_data.volume or 0),
                            open_interest=0,  # IBKR doesn't provide real-time OI
                            provider=self.name
                        )
                        ticks.append(tick)
        
        logger.info(f"[ibkr] Fetched {len(ticks)} ticks for {ticker}")
        
    except Exception as e:
        logger.error(f"[ibkr] Error fetching chain: {e}")
    
    return ticks
"""
