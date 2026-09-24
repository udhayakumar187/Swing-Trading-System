from sqlalchemy import String, DateTime, Enum, ForeignKey, Index, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class TradingRunStatus(str, enum.Enum):
    STARTED = "STARTED"
    MARKET_DATA_FETCHED = "MARKET_DATA_FETCHED"
    SIGNALS_GENERATED = "SIGNALS_GENERATED"
    RISK_CHECKED = "RISK_CHECKED"
    ORDERS_PLACED = "ORDERS_PLACED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TradingRun(Base, TimestampMixin):
    __tablename__ = "trading_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    run_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TradingRunStatus] = mapped_column(Enum(TradingRunStatus), default=TradingRunStatus.STARTED, nullable=False)
    symbols_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signals_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signals_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paper_or_live: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="trading_runs", lazy="selectin")
    signals: Mapped[list["Signal"]] = relationship(back_populates="trading_run", lazy="selectin")

    __table_args__ = (
        Index("ix_trading_runs_account_date", "account_id", "run_date"),
        Index("ix_trading_runs_status", "status"),
    )