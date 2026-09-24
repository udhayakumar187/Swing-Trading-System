from sqlalchemy import String, Numeric, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class JournalEntryType(str, enum.Enum):
    TRADE_OPEN = "TRADE_OPEN"
    TRADE_CLOSE = "TRADE_CLOSE"
    RISK_EVENT = "RISK_EVENT"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    ERROR = "ERROR"
    NOTE = "NOTE"


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    entry_type: Mapped[JournalEntryType] = mapped_column(Enum(JournalEntryType), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pnl: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    risk_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_journal_entries_account_date", "account_id", "created_at"),
        Index("ix_journal_entries_type", "entry_type"),
    )