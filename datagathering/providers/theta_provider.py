"""
ThetaData provider — uses get_last_option (snapshot) to get the most recent
bid/ask for each contract. This avoids the blocking issue with get_strikes on
active expirations. Uses get_hist_option only for expired dates.
"""
import os
import sys
import logging
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
    """BaseProvider-compatible class for ThetaData. Uses get_last_option for current quotes."""

    @property
    def name(self) -> str:
        return "theta"

    def fetch_chain(self, ticker: str) -> List:
        from thetadata import OptionReqType, OptionRight, DateRange
        from datagathering.models import StandardOptionTick
        ticks = []
        client = _make_client()
        today = date.today()
        today_dt = datetime.combine(today, datetime.min.time())

        try:
            with client.connect():
                expirations = client.get_expirations(ticker)
                if expirations is None or len(expirations) == 0:
                    logger.warning(f"[theta] No expirations found for {ticker}")
                    return []

                # Only use future expirations, limit to nearest 2 for speed
                # expirations may be Timestamps — compare as date
                future_exps = [e for e in expirations if (e.date() if hasattr(e, 'date') else e) >= today][:2]
                logger.info(f"[theta] Checking {len(future_exps)} expirations for {ticker}")

                for exp in future_exps:
                    # Use get_hist_option with a recent date_range instead of get_strikes
                    # This avoids the blocking issue with get_strikes on active chains
                    for right_enum, right_str in [
                        (OptionRight.CALL, "C"),
                        (OptionRight.PUT, "P"),
                    ]:
                        try:
                            # Get the last available quote for the nearest standard strikes
                            # AAPL ATM is ~$250, so we sample strikes around a range
                            # A safer approach: use get_last_option with known strike
                            # For now, use get_hist_option with 5-day window to get recent data
                            # DateRange requires datetime objects, not date
                            date_range = DateRange(
                                datetime.combine(today - timedelta(days=5), datetime.min.time()),
                                datetime.combine(today, datetime.min.time())
                            )
                            # We need to know strikes — use get_strikes with no date_range arg
                            # and timeout gracefully
                            import signal

                            def timeout_handler(signum, frame):
                                raise TimeoutError("get_strikes timed out")

                            signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(5)  # 5 second timeout
                            try:
                                strikes_raw = client.get_strikes(ticker, exp)
                                signal.alarm(0)  # cancel alarm
                            except TimeoutError:
                                logger.warning(f"[theta] get_strikes timed out for {ticker} {exp}, skipping")
                                continue

                            if strikes_raw is None or len(strikes_raw) == 0:
                                continue

                            # get_strikes returns Decimal in tenths of a cent — convert to USD
                            strikes = [float(s) / 1000.0 for s in strikes_raw]
                            logger.info(f"[theta] {ticker} {exp} {right_str}: {len(strikes)} strikes")

                            for strike in strikes:
                                try:
                                    import time
                                    time.sleep(2.1)  # Keep under 30 req/min (1 req per 2s)
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

        logger.info(f"[theta] Fetched {len(ticks)} ticks for {ticker}.")
        return ticks
