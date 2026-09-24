from sqlalchemy import String, DateTime, ForeignKey, Index, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_code: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trading_run_id: Mapped[int | None] = mapped_column(ForeignKey("trading_runs.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    account: Mapped["Account"] = relationship(lazy="selectin")
    trading_run: Mapped["TradingRun"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_audit_logs_account_date", "account_id", "created_at"),
        Index("ix_audit_logs_event_code", "event_code"),
        Index("ix_audit_logs_severity", "severity"),
    )