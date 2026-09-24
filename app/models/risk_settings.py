from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class RiskSettings(Base, TimestampMixin):
    __tablename__ = "risk_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, unique=True)
    max_risk_percent: Mapped[float] = mapped_column(Numeric(5, 4), default=0.01, nullable=False)
    max_daily_loss_percent: Mapped[float] = mapped_column(Numeric(5, 4), default=0.02, nullable=False)
    max_open_positions: Mapped[int] = mapped_column(default=3, nullable=False)
    max_stop_loss_percent: Mapped[float] = mapped_column(Numeric(5, 4), default=0.08, nullable=False)
    min_risk_reward: Mapped[float] = mapped_column(Numeric(5, 2), default=2.0, nullable=False)
    swing_low_lookback: Mapped[int] = mapped_column(default=5, nullable=False)
    event_exclusion_window: Mapped[int] = mapped_column(default=7, nullable=False)
    daily_loss_action: Mapped[str] = mapped_column(String(50), default="STOP_NEW_ORDERS", nullable=False)
    max_position_concentration_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.3, nullable=False)
    max_sector_concentration_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.5, nullable=False)

    account: Mapped["Account"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_risk_settings_account", "account_id"),
    )