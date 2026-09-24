from sqlalchemy import String, Numeric, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    broker_name: Mapped[str] = mapped_column(String(50), nullable=False)
    client_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    total_capital: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    available_cash: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    max_risk_percent: Mapped[float] = mapped_column(Numeric(5, 4), default=0.01, nullable=False)
    max_daily_loss_percent: Mapped[float] = mapped_column(Numeric(5, 4), default=0.02, nullable=False)
    max_open_positions: Mapped[int] = mapped_column(default=3, nullable=False)
    max_stop_loss_percent: Mapped[float] = mapped_column(Numeric(5, 4), default=0.08, nullable=False)
    min_risk_reward: Mapped[float] = mapped_column(Numeric(5, 2), default=2.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    positions: Mapped[list["Position"]] = relationship(back_populates="account", lazy="selectin")
    orders: Mapped[list["Order"]] = relationship(back_populates="account", lazy="selectin")
    signals: Mapped[list["Signal"]] = relationship(back_populates="account", lazy="selectin")
    trading_runs: Mapped[list["TradingRun"]] = relationship(back_populates="account", lazy="selectin")
    daily_snapshots: Mapped[list["DailyPortfolioSnapshot"]] = relationship(back_populates="account", lazy="selectin")