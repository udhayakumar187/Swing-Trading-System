from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalDecision(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOPPED_OUT = "STOPPED_OUT"
    TARGET_HIT = "TARGET_HIT"
    MANUALLY_CLOSED = "MANUALLY_CLOSED"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class OrderProductType(str, Enum):
    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class TradingRunStatus(str, Enum):
    STARTED = "STARTED"
    MARKET_DATA_FETCHED = "MARKET_DATA_FETCHED"
    SIGNALS_GENERATED = "SIGNALS_GENERATED"
    RISK_CHECKED = "RISK_CHECKED"
    ORDERS_PLACED = "ORDERS_PLACED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JournalEntryType(str, Enum):
    TRADE_OPEN = "TRADE_OPEN"
    TRADE_CLOSE = "TRADE_CLOSE"
    RISK_EVENT = "RISK_EVENT"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    ERROR = "ERROR"
    NOTE = "NOTE"


class SignalBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    signal_type: SignalType
    signal_timestamp: datetime
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0)
    risk_amount: float = Field(..., ge=0)
    risk_reward_ratio: float = Field(..., gt=0)
    strategy_name: str = Field(..., min_length=1, max_length=100)
    decision: SignalDecision = SignalDecision.PENDING
    reason: Optional[str] = None


class SignalCreate(SignalBase):
    pass


class SignalResponse(SignalBase):
    id: int
    account_id: int
    trading_run_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PositionBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    exchange: str = Field(default="NSE", max_length=20)
    quantity: int = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0)
    status: PositionStatus = PositionStatus.OPEN
    strategy_name: str = Field(..., min_length=1, max_length=100)
    paper_or_live: str = Field(..., pattern="^(PAPER|LIVE)$")


class PositionCreate(PositionBase):
    signal_id: Optional[int] = None
    broker_order_id: Optional[str] = None


class PositionUpdate(BaseModel):
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    status: Optional[PositionStatus] = None
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    realized_pnl: Optional[float] = None


class PositionResponse(PositionBase):
    id: int
    account_id: int
    signal_id: Optional[int] = None
    broker_order_id: Optional[str] = None
    entry_timestamp: datetime
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    side: OrderSide
    quantity: int = Field(..., gt=0)
    order_type: OrderType
    product_type: OrderProductType
    price: Optional[float] = Field(None, gt=0)
    paper_or_live: str = Field(..., pattern="^(PAPER|LIVE)$")


class OrderCreate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id: int
    account_id: int
    status: OrderStatus
    broker_order_id: Optional[str] = None
    filled_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TradingRunBase(BaseModel):
    run_date: datetime
    paper_or_live: str = Field(..., pattern="^(PAPER|LIVE|DRY_RUN)$")


class TradingRunCreate(TradingRunBase):
    pass


class TradingRunResponse(TradingRunBase):
    id: int
    account_id: int
    status: TradingRunStatus
    symbols_scanned: int
    signals_generated: int
    signals_rejected: int
    orders_attempted: int
    orders_completed: int
    orders_rejected: int
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountBase(BaseModel):
    broker_name: str = Field(..., max_length=50)
    client_id: str = Field(..., max_length=50)
    account_name: str = Field(..., max_length=100)
    total_capital: float = Field(..., gt=0)
    available_cash: float = Field(..., ge=0)
    max_risk_percent: float = Field(default=0.01, ge=0, le=1)
    max_daily_loss_percent: float = Field(default=0.02, ge=0, le=1)
    max_open_positions: int = Field(default=3, ge=1, le=50)
    max_stop_loss_percent: float = Field(default=0.08, ge=0, le=1)
    min_risk_reward: float = Field(default=2.0, gt=0)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    total_capital: Optional[float] = None
    available_cash: Optional[float] = None
    max_risk_percent: Optional[float] = None
    max_daily_loss_percent: Optional[float] = None
    max_open_positions: Optional[int] = None
    max_stop_loss_percent: Optional[float] = None
    min_risk_reward: Optional[float] = None
    is_active: Optional[bool] = None


class AccountResponse(AccountBase):
    id: int
    is_active: bool
    is_paper: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RiskSettingsBase(BaseModel):
    max_risk_percent: float = Field(default=0.01, ge=0, le=1)
    max_daily_loss_percent: float = Field(default=0.02, ge=0, le=1)
    max_open_positions: int = Field(default=3, ge=1, le=50)
    max_stop_loss_percent: float = Field(default=0.08, ge=0, le=1)
    min_risk_reward: float = Field(default=2.0, gt=0)
    swing_low_lookback: int = Field(default=5, ge=1, le=20)
    event_exclusion_window: int = Field(default=7, ge=0, le=30)
    daily_loss_action: str = Field(default="STOP_NEW_ORDERS", max_length=50)
    max_position_concentration_percent: float = Field(default=0.3, ge=0, le=1)
    max_sector_concentration_percent: float = Field(default=0.5, ge=0, le=1)


class RiskSettingsCreate(RiskSettingsBase):
    pass


class RiskSettingsUpdate(BaseModel):
    max_risk_percent: Optional[float] = None
    max_daily_loss_percent: Optional[float] = None
    max_open_positions: Optional[int] = None
    max_stop_loss_percent: Optional[float] = None
    min_risk_reward: Optional[float] = None
    swing_low_lookback: Optional[int] = None
    event_exclusion_window: Optional[int] = None
    daily_loss_action: Optional[str] = None
    max_position_concentration_percent: Optional[float] = None
    max_sector_concentration_percent: Optional[float] = None


class RiskSettingsResponse(RiskSettingsBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WatchlistBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    exchange: str = Field(default="NSE", max_length=20)
    name: Optional[str] = Field(None, max_length=200)
    sector: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    min_volume: Optional[int] = None
    min_market_cap: Optional[float] = None


class WatchlistCreate(WatchlistBase):
    pass


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    is_active: Optional[bool] = None
    min_volume: Optional[int] = None
    min_market_cap: Optional[float] = None


class WatchlistResponse(WatchlistBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyPortfolioSnapshotBase(BaseModel):
    snapshot_date: datetime
    total_equity: float = Field(..., ge=0)
    cash: float = Field(..., ge=0)
    invested_value: float = Field(..., ge=0)
    unrealized_pnl: float = Field(default=0.0)
    realized_pnl: float = Field(default=0.0)
    daily_pnl: float = Field(default=0.0)
    open_positions_count: int = Field(default=0, ge=0)
    max_drawdown: Optional[float] = None


class DailyPortfolioSnapshotResponse(DailyPortfolioSnapshotBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    trading_mode: str
    timezone: str
    database: dict
    checks: dict


class PortfolioSummary(BaseModel):
    total_equity: float
    cash: float
    invested_value: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    open_positions_count: int
    max_drawdown: Optional[float] = None
    risk_utilization_pct: float
    daily_loss_pct: float