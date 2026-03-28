"""
Tradier.com provider — fetches option chains via Tradier REST API.

Environment (.env):
  TRADIER_ACCESS_TOKEN — required; Bearer token from Tradier developer dashboard
    (https://developer.tradier.com — production token for api.tradier.com).
  TRADIER_SANDBOX — optional; set to 1/true/yes to use sandbox.tradier.com
    (use a sandbox access token from the same dashboard).
"""
import os
import logging
import requests
from typing import Any, List, Optional
from dotenv import load_dotenv
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

load_dotenv()
logger = logging.getLogger(__name__)

TRADIER_BASE_URL = "https://api.tradier.com/v1"
TRADIER_SANDBOX_URL = "https://sandbox.tradier.com/v1"


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _as_list(value: Any) -> List[Any]:
    """Tradier JSON can return a single object where docs show an array (XML→JSON quirk)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class TradierProvider(BaseProvider):

    def __init__(self, sandbox: Optional[bool] = None):
        self.token = (os.getenv("TRADIER_ACCESS_TOKEN") or "").strip()
        use_sandbox = _env_bool("TRADIER_SANDBOX", False) if sandbox is None else sandbox
        self.base_url = TRADIER_SANDBOX_URL if use_sandbox else TRADIER_BASE_URL
        if not self.token:
            logger.warning("[tradier] TRADIER_ACCESS_TOKEN not set in .env")

    @property
    def name(self) -> str:
        return "tradier"

    def _get(self, path: str, params: dict = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        resp = requests.get(f"{self.base_url}{path}", headers=headers, params=params or {})
        resp.raise_for_status()
        return resp.json()

    def fetch_expirations(self, ticker: str) -> List[str]:
        data = self._get("/markets/options/expirations", {"symbol": ticker, "includeAllRoots": "true"})
        dates = data.get("expirations", {}).get("date")
        return [str(d) for d in _as_list(dates)]

    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        ticks = []
        if not self.token:
            logger.error("[tradier] Missing TRADIER_ACCESS_TOKEN; skipping chain fetch.")
            return ticks
        try:
            expirations = self.fetch_expirations(ticker)
            if not expirations:
                logger.warning(f"[tradier] No expirations for {ticker}")
                return ticks
            for exp in expirations:
                data = self._get("/markets/options/chains", {"symbol": ticker, "expiration": exp, "greeks": "false"})
                raw = data.get("options", {}).get("option")
                options = _as_list(raw)
                for opt in options:
                    if not isinstance(opt, dict):
                        continue
                    right = "C" if opt.get("option_type", "").lower() == "call" else "P"
                    tick = StandardOptionTick.make(
                        root=ticker,
                        expiration=exp,
                        strike=opt.get("strike", 0),
                        right=right,
                        bid=opt.get("bid", 0) or 0,
                        ask=opt.get("ask", 0) or 0,
                        volume=opt.get("volume", 0) or 0,
                        open_interest=opt.get("open_interest", 0) or 0,
                        provider=self.name,
                    )
                    ticks.append(tick)
            logger.info(f"[tradier] Fetched {len(ticks)} ticks for {ticker}.")
        except Exception as e:
            logger.error(f"[tradier] Error fetching chain for {ticker}: {e}")
        return ticks
