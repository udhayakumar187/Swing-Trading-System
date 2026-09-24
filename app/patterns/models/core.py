from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app.patterns.models.enums import (
    PatternCategory,
    PatternDirection,
    PatternStatus,
    Timeframe,
    MarketRegime,
    PivotType,
    DivergenceType,
    WaveType,
)


class Candle(BaseModel):
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: float, info) -> float:
        if info.data:
            open_val = info.data.get("open")
            close_val = info.data.get("close")
            if open_val is not None and close_val is not None:
                if v < max(open_val, close_val):
                    raise ValueError("high must be >= max(open, close)")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v: float, info) -> float:
        if info.data:
            open_val = info.data.get("open")
            close_val = info.data.get("close")
            if open_val is not None and close_val is not None:
                if v > min(open_val, close_val):
                    raise ValueError("low must be <= min(open, close)")
        return v


class OHLCVData(BaseModel):
    symbol: str
    timeframe: Timeframe
    candles: List[Candle]

    @field_validator("candles")
    @classmethod
    def validate_candles(cls, v: List[Candle]) -> List[Candle]:
        if len(v) < 2:
            raise ValueError("At least 2 candles required")
        for i in range(1, len(v)):
            if v[i].timestamp <= v[i - 1].timestamp:
                raise ValueError("Candles must be chronologically ordered with unique timestamps")
        return v


class PriceLevel(BaseModel):
    name: str
    price: float
    timestamp: Optional[datetime] = None
    description: Optional[str] = None


class PivotPoint(BaseModel):
    index: int
    timestamp: datetime
    price: float
    pivot_type: PivotType
    left_bars: int
    right_bars: int
    confirmed: bool = True


class FibonacciRatio(BaseModel):
    name: str
    expected_min: float
    expected_max: float
    actual: float
    within_tolerance: bool


class PatternMetadata(BaseModel):
    pattern_name: str
    pattern_category: PatternCategory
    required_candles: int
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confirmation_rules: List[str] = Field(default_factory=list)
    invalidation_rules: List[str] = Field(default_factory=list)


class PatternDetection(BaseModel):
    id: Optional[str] = None
    symbol: str
    timeframe: Timeframe
    pattern_name: str
    pattern_category: PatternCategory
    direction: PatternDirection
    status: PatternStatus
    start_timestamp: datetime
    confirmation_timestamp: Optional[datetime] = None
    completion_timestamp: Optional[datetime] = None
    detection_timestamp: datetime = Field(default_factory=datetime.utcnow)
    price_levels: Dict[str, float] = Field(default_factory=dict)
    invalidation_level: Optional[float] = None
    target_levels: Dict[str, float] = Field(default_factory=dict)
    quality_score: Optional[int] = Field(None, ge=0, le=100)
    volume_confirmation: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    explanation: List[str] = Field(default_factory=list)
    market_regime: Optional[MarketRegime] = None
    pivots: List[PivotPoint] = Field(default_factory=list)
    fibonacci_ratios: List[FibonacciRatio] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class PatternDefinition(BaseModel):
    name: str
    category: PatternCategory
    description: str
    required_candles: int
    timeframe: Optional[Timeframe] = None
    direction: PatternDirection
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confirmation_rules: List[str] = Field(default_factory=list)
    invalidation_rules: List[str] = Field(default_factory=list)
    quality_factors: List[str] = Field(default_factory=list)


class ConfluencePattern(BaseModel):
    pattern_name: str
    category: PatternCategory
    direction: PatternDirection
    quality_score: int
    weight: float


class ConfluenceResult(BaseModel):
    symbol: str
    timeframe: Timeframe
    patterns: List[ConfluencePattern]
    technical_confluence_score: int
    explanation: List[str]
    market_regime: Optional[MarketRegime] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)