from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from enum import Enum


class EventType(str, Enum):
    EARNINGS = "EARNINGS"
    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    BOARD_MEETING = "BOARD_MEETING"
    AGM = "AGM"
    BUYBACK = "BUYBACK"
    RESULT = "RESULT"
    OTHER = "OTHER"


class EventImpact(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class CorporateEvent:
    symbol: str
    event_type: EventType
    event_date: date
    impact: EventImpact
    description: str
    source: str


class EventRiskProvider(ABC):
    @abstractmethod
    def get_upcoming_events(
        self, 
        symbols: list[str], 
        window_days: int
    ) -> dict[str, list[CorporateEvent]]:
        pass
    
    @abstractmethod
    def has_high_impact_event(
        self, 
        symbol: str, 
        window_days: int
    ) -> tuple[bool, Optional[CorporateEvent]]:
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class DummyEventRiskProvider(EventRiskProvider):
    def __init__(self):
        self._events: dict[str, list[CorporateEvent]] = {}
    
    def get_provider_name(self) -> str:
        return "DummyEventRiskProvider"
    
    def is_healthy(self) -> bool:
        return True
    
    def get_upcoming_events(
        self, 
        symbols: list[str], 
        window_days: int
    ) -> dict[str, list[CorporateEvent]]:
        return {symbol: [] for symbol in symbols}
    
    def has_high_impact_event(
        self, 
        symbol: str, 
        window_days: int
    ) -> tuple[bool, Optional[CorporateEvent]]:
        return False, None


class YahooFinanceEventRiskProvider(EventRiskProvider):
    def __init__(self):
        self._cache: dict[str, list[CorporateEvent]] = {}
        self._cache_ttl_hours = 24
    
    def get_provider_name(self) -> str:
        return "YahooFinanceEventRiskProvider"
    
    def is_healthy(self) -> bool:
        return True
    
    def get_upcoming_events(
        self, 
        symbols: list[str], 
        window_days: int
    ) -> dict[str, list[CorporateEvent]]:
        return {symbol: [] for symbol in symbols}
    
    def has_high_impact_event(
        self, 
        symbol: str, 
        window_days: int
    ) -> tuple[bool, Optional[CorporateEvent]]:
        return False, None


def create_event_risk_provider(provider_type: str = "dummy") -> EventRiskProvider:
    if provider_type.lower() == "yahoo":
        return YahooFinanceEventRiskProvider()
    return DummyEventRiskProvider()