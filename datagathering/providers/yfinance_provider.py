"""
Yahoo Finance provider — free, no credentials required.
Used as the default provider during development and testing.
"""
import logging
from typing import List
import yfinance as yf
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class YFinanceProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "yfinance"

    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        ticks = []
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            if not expirations:
                logger.warning(f"[yfinance] No expirations found for {ticker}")
                return []

            for exp in expirations:
                chain = stock.option_chain(exp)
                for df, right in [(chain.calls, "C"), (chain.puts, "P")]:
                    for _, row in df.iterrows():
                        try:
                            tick = StandardOptionTick.make(
                                root=ticker,
                                expiration=exp,
                                strike=row.get("strike", 0),
                                right=right,
                                bid=row.get("bid", 0),
                                ask=row.get("ask", 0),
                                volume=row.get("volume", 0) or 0,
                                open_interest=row.get("openInterest", 0) or 0,
                                provider=self.name,
                            )
                            ticks.append(tick)
                        except Exception as e:
                            logger.debug(f"[yfinance] Skipping row: {e}")

            logger.info(f"[yfinance] Fetched {len(ticks)} ticks for {ticker} across {len(expirations)} expirations.")
        except Exception as e:
            logger.error(f"[yfinance] Error fetching chain for {ticker}: {e}")
        return ticks
