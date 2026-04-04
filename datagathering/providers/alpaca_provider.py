"""
Alpaca Market Data provider — fetches option chain snapshots via Alpaca REST API.

Environment (.env):
  APCA_API_KEY_ID      — required; Alpaca API key id
  APCA_API_SECRET_KEY  — required; Alpaca API secret key
  ALPACA_DATA_BASE_URL — optional; defaults to https://data.alpaca.markets/v1beta1
  ALPACA_OPTION_FEED   — optional; market data feed name
  ALPACA_PAGE_LIMIT    — optional; pagination limit per request (default 1000)
"""
import logging
import os
from typing import Any, Dict, List, Mapping, Optional

import requests
from dotenv import load_dotenv

from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

load_dotenv()
logger = logging.getLogger(__name__)


class AlpacaProvider(BaseProvider):
    def __init__(self) -> None:
        self.key_id = (os.getenv("APCA_API_KEY_ID") or "").strip()
        self.secret_key = (os.getenv("APCA_API_SECRET_KEY") or "").strip()
        self.base_url = (os.getenv("ALPACA_DATA_BASE_URL") or "https://data.alpaca.markets/v1beta1").rstrip("/")
        self.feed = (os.getenv("ALPACA_OPTION_FEED") or "").strip() or None
        self.page_limit = int(os.getenv("ALPACA_PAGE_LIMIT") or "1000")

        if not self.key_id or not self.secret_key:
            logger.warning("[alpaca] APCA_API_KEY_ID/APCA_API_SECRET_KEY not set in .env")

    @property
    def name(self) -> str:
        return "alpaca"

    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        ticks: List[StandardOptionTick] = []

        if not self.key_id or not self.secret_key:
            logger.error("[alpaca] Missing Alpaca credentials; skipping chain fetch.")
            return ticks

        headers = {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Accept": "application/json",
        }

        params: Dict[str, Any] = {"limit": self.page_limit}
        if self.feed:
            params["feed"] = self.feed

        next_page_token: Optional[str] = None
        url = f"{self.base_url}/options/snapshots/{ticker.upper()}"

        try:
            while True:
                if next_page_token:
                    params["page_token"] = next_page_token
                else:
                    params.pop("page_token", None)

                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                payload = response.json()

                snapshots = _extract_snapshots(payload)
                for option_symbol, snapshot in snapshots.items():
                    tick = self._build_tick(ticker.upper(), option_symbol, snapshot)
                    if tick is not None:
                        ticks.append(tick)

                next_page_token = payload.get("next_page_token")
                if not next_page_token:
                    break

            logger.info(f"[alpaca] Fetched {len(ticks)} ticks for {ticker}.")
        except Exception as e:
            logger.error(f"[alpaca] Error fetching chain for {ticker}: {e}")

        return ticks

    def _build_tick(
        self,
        ticker: str,
        option_symbol: str,
        snapshot: object,
    ) -> Optional[StandardOptionTick]:
        if not isinstance(snapshot, Mapping):
            return None

        details = _parse_occ_option_symbol(option_symbol)
        if not details:
            return None

        quote_payload = snapshot.get("latestQuote") or snapshot.get("latest_quote") or snapshot.get("quote") or {}
        if not isinstance(quote_payload, Mapping):
            return None

        bid = _to_float(quote_payload.get("bp", quote_payload.get("bid_price", quote_payload.get("bid"))))
        ask = _to_float(quote_payload.get("ap", quote_payload.get("ask_price", quote_payload.get("ask"))))
        if bid is None or ask is None:
            return None

        bid_size = _to_int(quote_payload.get("bs", quote_payload.get("bid_size"))) or 0
        ask_size = _to_int(quote_payload.get("as", quote_payload.get("ask_size"))) or 0
        open_interest = _to_int(snapshot.get("open_interest")) or 0

        return StandardOptionTick.make(
            root=ticker,
            expiration=details["expiration"],
            strike=details["strike"],
            right=details["right"],
            bid=bid,
            ask=ask,
            volume=bid_size + ask_size,
            open_interest=open_interest,
            provider=self.name,
        )


def _extract_snapshots(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    snapshots = payload.get("snapshots")
    if isinstance(snapshots, Mapping):
        return snapshots

    option_chain = payload.get("option_chain")
    if isinstance(option_chain, Mapping):
        return option_chain

    return {
        key: value
        for key, value in payload.items()
        if isinstance(key, str) and _parse_occ_option_symbol(key) is not None
    }


def _parse_occ_option_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    text = symbol.strip().upper()
    if len(text) < 16:
        return None

    tail = text[-15:]
    root = text[:-15]
    exp = tail[:6]
    right = tail[6]
    strike_raw = tail[7:]

    if not root or not exp.isdigit() or right not in {"C", "P"} or not strike_raw.isdigit():
        return None

    return {
        "root": root,
        "expiration": f"20{exp[:2]}-{exp[2:4]}-{exp[4:6]}",
        "strike": int(strike_raw) / 1000.0,
        "right": right,
    }


def _to_float(value: object) -> Optional[float]:
    if value in (None, ""):
        return None
    return float(value)


def _to_int(value: object) -> Optional[int]:
    if value in (None, ""):
        return None
    return int(value)
