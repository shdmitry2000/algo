"""
Abstract base class for all data providers.
Every provider must implement fetch_chain() to return a list of StandardOptionTick objects.
"""
from abc import ABC, abstractmethod
from typing import List
from datagathering.models import StandardOptionTick


class BaseProvider(ABC):
    """Each provider must implement these methods."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name used in StandardOptionTick.provider field."""
        ...

    @abstractmethod
    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        """
        Fetch the full option chain for a given ticker.
        Returns a list of StandardOptionTick, one per contract.
        """
        ...
