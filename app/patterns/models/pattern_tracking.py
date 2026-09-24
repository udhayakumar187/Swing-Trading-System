from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal


class PatternType(str, Enum):
    BREAKOUT_VOLUME = "BREAKOUT_VOLUME"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"
    TREND_PULLBACK = "TREND_PULLBACK"
    EMA_PULLBACK = "EMA_PULLBACK"
    DOUBLE_BOTTOM = "DOUBLE_BOTTOM"
    DOUBLE_TOP = "DOUBLE_TOP"
    BULL_FLAG = "BULL_FLAG"
    BEAR_FLAG = "BEAR_FLAG"
    ASCENDING_TRIANGLE_BREAKOUT = "ASCENDING_TRIANGLE_BREAKOUT"
    DESCENDING_TRIANGLE_BREAKDOWN = "DESCENDING_TRIANGLE_BREAKDOWN"
    SUPPORT_BOUNCE = "SUPPORT_BOUNCE"
    RESISTANCE_REJECTION = "RESISTANCE_REJECTION"


class PatternOutcome(str, Enum):
    PENDING = "PENDING"
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    PARTIAL = "PARTIAL"


class TrackedPattern(BaseModel):
    id: Optional[str] = None
    symbol: str
    timeframe: str
    pattern_type: PatternType
    pattern_name: str
    direction: str
    
    detection_timestamp: datetime
    detection_price: float
    detection_volume: float
    
    pattern_start_date: date
    pattern_end_date: date
    pattern_bars: int
    
    key_levels: Dict[str, float] = Field(default_factory=dict)
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    quality_score: Optional[int] = Field(None, ge=0, le=100)
    volume_confirmation: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    outcome: PatternOutcome = PatternOutcome.PENDING
    outcome_timestamp: Optional[datetime] = None
    outcome_price: Optional[float] = None
    max_favorable_move: Optional[float] = None
    max_adverse_move: Optional[float] = None
    days_to_outcome: Optional[int] = None
    
    forward_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PatternForwardTracking(BaseModel):
    id: Optional[str] = None
    tracked_pattern_id: str
    symbol: str
    
    tracking_start_date: date
    tracking_end_date: date
    tracking_days: int
    
    daily_data: List[Dict[str, Any]] = Field(default_factory=list)
    
    max_high: Optional[float] = None
    max_high_date: Optional[date] = None
    min_low: Optional[float] = None
    min_low_date: Optional[date] = None
    
    first_target_hit_date: Optional[date] = None
    first_stop_hit_date: Optional[date] = None
    
    price_at_1d: Optional[float] = None
    price_at_3d: Optional[float] = None
    price_at_5d: Optional[float] = None
    price_at_10d: Optional[float] = None
    price_at_20d: Optional[float] = None
    
    return_1d: Optional[float] = None
    return_3d: Optional[float] = None
    return_5d: Optional[float] = None
    return_10d: Optional[float] = None
    return_20d: Optional[float] = None
    
    max_drawdown: Optional[float] = None
    max_runup: Optional[float] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PatternScanConfig(BaseModel):
    symbols: List[str] = Field(default_factory=list)
    timeframe: str = "1d"
    lookback_days: int = 200
    forward_days: int = 20
    patterns_to_track: List[PatternType] = Field(default_factory=lambda: list(PatternType))
    min_quality_score: int = 60
    require_volume_confirmation: bool = True


class PatternStatistics(BaseModel):
    pattern_type: PatternType
    symbol: str
    total_detections: int = 0
    successful: int = 0
    failed: int = 0
    pending: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    avg_r_multiple: float = 0.0
    max_drawdown: float = 0.0
    avg_days_to_outcome: float = 0.0