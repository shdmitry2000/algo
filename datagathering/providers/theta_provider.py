"""
ThetaData provider with dual implementation:
- BULK API (fast): Requires ThetaData PRO subscription
- PER-STRIKE API (slow): Works with FREE tier

Configuration:
Set THETA_BULK_API=true in .env to enable bulk API mode (PRO only).
FREE tier users: leave THETA_BULK_API=false (default).
"""
import os
import sys
import logging
import requests
from datetime import date, datetime, timedelta
from typing import List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _make_client():
    from thetadata import ThetaClient
    username = os.getenv("THETA_USERNAME", "")
    password = os.getenv("THETA_PASSWORD", "")
    if username and username != "your_pro_username":
        return ThetaClient(username=username, passwd=password)
    return ThetaClient()


class ThetaProvider:
    """
    BaseProvider-compatible class for ThetaData.
    
    CONFIGURATION:
    - Set THETA_BULK_API=true in .env when using PRO subscription (fast bulk API)
    - Leave THETA_BULK_API=false for FREE tier (slow per-strike requests)
    
    PERFORMANCE:
    - Bulk mode (PRO): ~2-5 seconds per symbol (all expirations)
    - Per-strike mode (FREE): ~6 minutes per symbol (2 expirations, ~30 strikes each)
    """

    @property
    def name(self) -> str:
        return "theta"

    def fetch_chain(self, ticker: str) -> List:
        """
        Fetch option chain using either bulk API (PRO) or per-strike requests (FREE).
        Mode is controlled by THETA_BULK_API environment variable.
        """
        use_bulk = os.getenv("THETA_BULK_API", "false").lower() == "true"
        
        if use_bulk:
            logger.info(f"[theta] Using BULK API mode for {ticker} (PRO subscription)")
            return self._fetch_chain_bulk(ticker)
        else:
            logger.info(f"[theta] Using PER-STRIKE mode for {ticker} (FREE tier)")
            return self._fetch_chain_per_strike(ticker)
    
    def _fetch_chain_bulk(self, ticker: str) -> List:
        """
        Fetch ALL options for ALL expirations in ONE request using bulk API.
        
        Requirements:
        - ThetaData PRO subscription
        - THETA_BULK_API=true in .env
        
        Speed: ~2-5 seconds per symbol (all expirations).
        
        API: /v2/bulk_hist/option/quote
        - exp=0: all expirations
        - Returns all strikes for all expirations in single response
        """
        from datagathering.models import StandardOptionTick
        ticks = []
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Format dates for API (YYYYMMDD)
        yesterday_str = yesterday.strftime("%Y%m%d")

        try:
            # Bulk historical quote: get ALL options for ALL expirations
            # exp=0 means "all expirations"
            url = f"http://127.0.0.1:25510/v2/bulk_hist/option/quote?root={ticker}&exp=0&start_date={yesterday_str}&end_date={yesterday_str}"
            logger.info(f"[theta] Bulk API request: {ticker} (all expirations, date: {yesterday_str})")
            
            response = requests.get(url, timeout=120)
            if response.status_code == 471:
                logger.error(f"[theta] Permission denied (471) — Bulk API requires PRO subscription. Set THETA_BULK_API=false to use FREE tier mode.")
                return []
            if response.status_code != 200:
                logger.error(f"[theta] Bulk API returned {response.status_code} for {ticker}: {response.text[:200]}")
                return []
            
            data = response.json()
            
            # Response format: {"response": [{"contract": {...}, "ticks": [[...]]}]}
            if "response" not in data:
                logger.warning(f"[theta] No response data for {ticker}")
                return []
            
            contracts = data["response"]
            logger.info(f"[theta] {ticker}: Retrieved {len(contracts)} contracts via bulk API")
            
            # Filter to only future expirations
            exp_count = {}
            
            for contract_data in contracts:
                try:
                    contract = contract_data.get("contract", {})
                    ticks_data = contract_data.get("ticks", [])
                    
                    if not ticks_data:
                        continue
                    
                    # Parse contract details
                    strike = float(contract.get("strike", 0)) / 1000.0  # Theta uses tenths of cent
                    right = contract.get("right", "")
                    exp_int = contract.get("expiration", 0)
                    
                    # Convert expiration from YYYYMMDD int to ISO string and date object
                    exp_str = str(exp_int)
                    if len(exp_str) == 8:
                        expiration = f"{exp_str[:4]}-{exp_str[4:6]}-{exp_str[6:8]}"
                        exp_date = date(int(exp_str[:4]), int(exp_str[4:6]), int(exp_str[6:8]))
                    else:
                        continue
                    
                    # Skip expired options
                    if exp_date < today:
                        continue
                    
                    # Get the last tick (most recent quote)
                    last_tick = ticks_data[-1]
                    
                    # Parse tick data: [ms_of_day, bid_size, bid_exchange, bid, bid_condition, 
                    #                   ask_size, ask_exchange, ask, ask_condition, date]
                    if len(last_tick) < 10:
                        continue
                    
                    # Parse bid/ask from tick
                    bid = float(last_tick[3]) if last_tick[3] else 0.0
                    ask = float(last_tick[7]) if last_tick[7] else 0.0
                    
                    tick = StandardOptionTick.make(
                        root=ticker,
                        expiration=expiration,
                        strike=strike,
                        right=right,
                        bid=bid,
                        ask=ask,
                        provider=self.name,
                    )
                    ticks.append(tick)
                    
                    # Count expirations
                    exp_count[expiration] = exp_count.get(expiration, 0) + 1
                    
                except Exception as e:
                    logger.debug(f"[theta] Failed to parse contract: {e}")
            
            logger.info(f"[theta] {ticker}: {len(ticks)} future contracts across {len(exp_count)} expirations")

        except requests.Timeout:
            logger.error(f"[theta] Bulk API timeout for {ticker}")
        except Exception as e:
            logger.error(f"[theta] Bulk API error for {ticker}: {e}")

        logger.info(f"[theta] Bulk mode: Fetched {len(ticks)} ticks for {ticker}")
        return ticks
    
    def _fetch_chain_per_strike(self, ticker: str) -> List:
        """
        Fetch options using per-strike historical requests (FREE tier only).
        
        Requirements:
        - ThetaData FREE or PRO subscription
        - THETA_BULK_API=false in .env (or unset)
        
        Limitations:
        - Rate limited to 30 requests/minute (2.1s delay per strike)
        - Only fetches 2 nearest expirations to manage runtime
        
        Speed: ~6 minutes per symbol for 2 expirations (~60 strikes total).
        
        API: client.get_hist_option (per-strike historical quotes)
        """
        from thetadata import OptionReqType, OptionRight, DateRange
        from datagathering.models import StandardOptionTick
        ticks = []
        client = _make_client()
        today = date.today()

        try:
            with client.connect():
                expirations = client.get_expirations(ticker)
                if expirations is None or len(expirations) == 0:
                    logger.warning(f"[theta] No expirations found for {ticker}")
                    return []

                # Only use future expirations, limit to nearest 2 for speed (FREE tier)
                future_exps = [e for e in expirations if (e.date() if hasattr(e, 'date') else e) >= today][:2]
                logger.info(f"[theta] Checking {len(future_exps)} expirations for {ticker} (per-strike mode - FREE tier)")

                for exp in future_exps:
                    for right_enum, right_str in [
                        (OptionRight.CALL, "C"),
                        (OptionRight.PUT, "P"),
                    ]:
                        try:
                            date_range = DateRange(
                                datetime.combine(today - timedelta(days=5), datetime.min.time()),
                                datetime.combine(today, datetime.min.time())
                            )
                            
                            # Get strikes with timeout
                            import signal

                            def timeout_handler(signum, frame):
                                raise TimeoutError("get_strikes timed out")

                            signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(5)
                            try:
                                strikes_raw = client.get_strikes(ticker, exp)
                                signal.alarm(0)
                            except TimeoutError:
                                logger.warning(f"[theta] get_strikes timed out for {ticker} {exp}, skipping")
                                continue

                            if strikes_raw is None or len(strikes_raw) == 0:
                                continue

                            strikes = [float(s) / 1000.0 for s in strikes_raw]
                            logger.info(f"[theta] {ticker} {exp} {right_str}: {len(strikes)} strikes (fetching with 2.1s delay)")

                            for strike in strikes:
                                try:
                                    import time
                                    time.sleep(2.1)  # Keep under 30 req/min (FREE tier rate limit)
                                    df = client.get_hist_option(
                                        req=OptionReqType.QUOTE,
                                        root=ticker,
                                        exp=exp,
                                        strike=strike,
                                        right=right_enum,
                                        date_range=date_range,
                                    )
                                    if df is None or len(df) == 0:
                                        continue
                                    last = df.iloc[-1]
                                    bid = float(last.get("bid", 0) or 0)
                                    ask = float(last.get("ask", 0) or 0)
                                    tick = StandardOptionTick.make(
                                        root=ticker,
                                        expiration=str(exp),
                                        strike=strike,
                                        right=right_str,
                                        bid=bid,
                                        ask=ask,
                                        provider=self.name,
                                    )
                                    ticks.append(tick)
                                except Exception as e:
                                    logger.debug(f"[theta] hist skip {ticker} {exp} {strike}{right_str}: {e}")

                        except Exception as e:
                            if "PERMISSION" in str(e):
                                logger.error(f"[theta] Account permission error — check subscription: {e}")
                                return ticks
                            logger.warning(f"[theta] {ticker} {exp} {right_str}: {e}")

        except Exception as e:
            logger.error(f"[theta] Connection error: {e}")

        logger.info(f"[theta] Per-strike mode: Fetched {len(ticks)} ticks for {ticker}")
        return ticks
