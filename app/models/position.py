from sqlalchemy import String, Numeric, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class PositionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOPPED_OUT = "STOPPED_OUT"
    TARGET_HIT = "TARGET_HIT"
    MANUALLY_CLOSED = "MANUALLY_CLOSED"


class Position(Base, TimestampMixin):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), default="NSE", nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    stop_loss: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    target_price: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    status: Mapped[PositionStatus] = mapped_column(Enum(PositionStatus), default=PositionStatus.OPEN, nullable=False)
    entry_timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_timestamp: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paper_or_live: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="positions", lazy="selectin")
    signal: Mapped["Signal"] = relationship(back_populates="position", lazy="selectin")

    __table_args__ = (
        Index("ix_positions_account_symbol_status", "account_id", "symbol", "status"),
        Index("ix_positions_status", "status"),
    )