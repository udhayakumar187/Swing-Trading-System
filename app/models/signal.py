from sqlalchemy import String, Numeric, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalDecision(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"


class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType), nullable=False)
    signal_timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    stop_loss: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    target_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    risk_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    risk_reward_ratio: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[SignalDecision] = mapped_column(Enum(SignalDecision), default=SignalDecision.PENDING, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    trading_run_id: Mapped[int | None] = mapped_column(ForeignKey("trading_runs.id", ondelete="SET NULL"), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="signals", lazy="selectin")
    position: Mapped["Position"] = relationship(back_populates="signal", lazy="selectin")
    trading_run: Mapped["TradingRun"] = relationship(back_populates="signals", lazy="selectin")

    __table_args__ = (
        Index("ix_signals_account_symbol", "account_id", "symbol"),
        Index("ix_signals_decision", "decision"),
        Index("ix_signals_trading_run", "trading_run_id"),
    )