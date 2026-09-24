from sqlalchemy import Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class DailyPortfolioSnapshot(Base, TimestampMixin):
    __tablename__ = "daily_portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    snapshot_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_equity: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    cash: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    invested_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    daily_pnl: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    open_positions_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="daily_snapshots", lazy="selectin")

    __table_args__ = (
        Index("ix_daily_portfolio_snapshots_account_date", "account_id", "snapshot_date", unique=True),
    )