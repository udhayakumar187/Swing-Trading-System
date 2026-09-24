from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from app.patterns.models import (
    OHLCVData,
    PatternDetection,
    PatternDefinition,
    PatternCategory,
    PatternDirection,
    Timeframe,
)


@dataclass
class DetectorContext:
    symbol: str
    timeframe: Timeframe
    current_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    indicators: Dict[str, Any] = field(default_factory=dict)
    pivots: List[Any] = field(default_factory=list)
    market_regime: Optional[str] = None


class PatternDetector(ABC):
    @property
    @abstractmethod
    def definition(self) -> PatternDefinition:
        pass

    @abstractmethod
    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        pass

    def get_required_candles(self) -> int:
        return self.definition.required_candles

    def get_name(self) -> str:
        return self.definition.name

    def get_category(self) -> PatternCategory:
        return self.definition.category

    def validate_data(self, data: OHLCVData) -> bool:
        return len(data.candles) >= self.get_required_candles()

    def create_detection(
        self,
        data: OHLCVData,
        start_idx: int,
        end_idx: int,
        direction: PatternDirection,
        status: str,
        price_levels: Dict[str, float],
        invalidation_level: Optional[float] = None,
        target_levels: Optional[Dict[str, float]] = None,
        quality_score: Optional[int] = None,
        volume_confirmation: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        explanation: Optional[List[str]] = None,
        confirmation_idx: Optional[int] = None,
    ) -> PatternDetection:
        from datetime import datetime

        start_ts = data.candles[start_idx].timestamp
        detection_ts = datetime.utcnow()
        confirmation_ts = data.candles[confirmation_idx].timestamp if confirmation_idx is not None else None
        completion_ts = data.candles[end_idx].timestamp if end_idx < len(data.candles) else None

        return PatternDetection(
            symbol=data.symbol,
            timeframe=data.timeframe,
            pattern_name=self.get_name(),
            pattern_category=self.get_category(),
            direction=direction,
            status=status,
            start_timestamp=start_ts,
            confirmation_timestamp=confirmation_ts,
            completion_timestamp=completion_ts,
            detection_timestamp=detection_ts,
            price_levels=price_levels,
            invalidation_level=invalidation_level,
            target_levels=target_levels or {},
            quality_score=quality_score,
            volume_confirmation=volume_confirmation,
            metadata=metadata or {},
            explanation=explanation or [],
        )