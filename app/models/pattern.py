from __future__ import annotations
from sqlalchemy import String, Numeric, DateTime, Enum, ForeignKey, Index, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class PatternCategoryEnum(str, enum.Enum):
    CANDLESTICK = "CANDLESTICK"
    CHART_PATTERN = "CHART_PATTERN"
    HARMONIC = "HARMONIC"
    MARKET_STRUCTURE = "MARKET_STRUCTURE"
    INDICATOR_PATTERN = "INDICATOR_PATTERN"
    WAVE = "WAVE"
    VOLUME = "VOLUME"
    VOLATILITY = "VOLATILITY"


class PatternDirectionEnum(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class PatternStatusEnum(str, enum.Enum):
    FORMING = "FORMING"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    COMPLETED = "COMPLETED"


class TimeframeEnum(str, enum.Enum):
    MIN_5 = "5m"
    MIN_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1D"
    WEEK_1 = "1W"


class MarketRegimeEnum(str, enum.Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    RANGE = "RANGE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"


class PatternDetectionModel(Base, TimestampMixin):
    __tablename__ = "pattern_detections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[TimeframeEnum] = mapped_column(Enum(TimeframeEnum), nullable=False, index=True)
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pattern_category: Mapped[PatternCategoryEnum] = mapped_column(Enum(PatternCategoryEnum), nullable=False)
    direction: Mapped[PatternDirectionEnum] = mapped_column(Enum(PatternDirectionEnum), nullable=False)
    status: Mapped[PatternStatusEnum] = mapped_column(Enum(PatternStatusEnum), default=PatternStatusEnum.FORMING, nullable=False)

    start_timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmation_timestamp: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_timestamp: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detection_timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    price_levels: Mapped[dict] = mapped_column(JSON, nullable=False)
    invalidation_level: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    target_levels: Mapped[dict] = mapped_column(JSON, nullable=False)

    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume_confirmation: Mapped[bool] = mapped_column(default=False, nullable=False)

    pattern_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    explanation: Mapped[list] = mapped_column(JSON, nullable=False)

    market_regime: Mapped[MarketRegimeEnum | None] = mapped_column(Enum(MarketRegimeEnum), nullable=True)

    outcomes: Mapped[list["PatternOutcomeModel"]] = relationship(
        back_populates="detection", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_pattern_detections_symbol_timeframe", "symbol", "timeframe"),
        Index("ix_pattern_detections_pattern_status", "pattern_name", "status"),
        Index("ix_pattern_detections_detection_time", "detection_timestamp"),
    )


class PatternDefinitionModel(Base, TimestampMixin):
    __tablename__ = "pattern_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[PatternCategoryEnum] = mapped_column(Enum(PatternCategoryEnum), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_candles: Mapped[int] = mapped_column(Integer, nullable=False)
    timeframe: Mapped[TimeframeEnum | None] = mapped_column(Enum(TimeframeEnum), nullable=True)
    direction: Mapped[PatternDirectionEnum] = mapped_column(Enum(PatternDirectionEnum), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    confirmation_rules: Mapped[list] = mapped_column(JSON, nullable=False)
    invalidation_rules: Mapped[list] = mapped_column(JSON, nullable=False)
    quality_factors: Mapped[list] = mapped_column(JSON, nullable=False)


class PatternOutcomeModel(Base, TimestampMixin):
    __tablename__ = "pattern_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("pattern_detections.id", ondelete="CASCADE"), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    exit_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    stop_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    target_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    return_pct: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    holding_period: Mapped[int] = mapped_column(Integer, nullable=False)
    mfe: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    mae: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    exit_reason: Mapped[str] = mapped_column(String(50), nullable=False)

    detection: Mapped["PatternDetectionModel"] = relationship(back_populates="outcomes")

    __table_args__ = (
        Index("ix_pattern_outcomes_detection", "detection_id"),
    )


class PatternBacktestModel(Base, TimestampMixin):
    __tablename__ = "pattern_backtests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[TimeframeEnum] = mapped_column(Enum(TimeframeEnum), nullable=False)

    total_occurrences: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    invalidated_count: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reached: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_reached: Mapped[int] = mapped_column(Integer, nullable=False)

    avg_return: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    median_return: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    avg_mfe: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    avg_mae: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    avg_holding_period: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    win_count: Mapped[int] = mapped_column(Integer, nullable=False)
    loss_count: Mapped[int] = mapped_column(Integer, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    config: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index("ix_pattern_backtests_pattern_symbol", "pattern_name", "symbol"),
    )