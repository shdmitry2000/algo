"""
Schwab provider — stub for data gathering.
Primary role: Schwab is used to PLACE ORDERS in Phase 3 (Open) and Phase 4 (Close).
This provider interface is implemented here for completeness and possible
supplementary data retrieval via schwab-py.
""" 
import logging
from typing import List
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class SchwabProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "schwab"

    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        """
        NOTE: Schwab's PRIMARY role is order execution (Phase 3 & 4).
        Option chain data gathering may be supplemented here via schwab-py
        once the auth token flow in schwab_auth.py is completed.
        """
        logger.warning("[schwab] SchwabProvider.fetch_chain() is a stub — "
                       "Schwab is primarily used for order execution in Phase 3 & 4.")
        return []
