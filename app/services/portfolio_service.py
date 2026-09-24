import logging
from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass

from app.models.position import Position, PositionStatus
from app.models.account import Account
from app.models.daily_portfolio_snapshot import DailyPortfolioSnapshot
from app.core.database import get_db
from app.core.config import get_settings
from app.brokers import create_broker_provider


logger = logging.getLogger(__name__)


@dataclass
class PortfolioSummary:
    total_equity: float
    cash: float
    invested_value: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    open_positions_count: int
    risk_utilization_pct: float
    daily_loss_pct: float


class PortfolioService:
    def __init__(self):
        self.settings = get_settings()
        self.broker = create_broker_provider()
    
    def get_portfolio_summary(self, account_id: int) -> PortfolioSummary:
        db = next(get_db())
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            positions = db.query(Position).filter(
                Position.account_id == account_id,
                Position.status == PositionStatus.OPEN
            ).all()
            
            self._update_position_prices(positions)
            
            invested_value = sum(p.quantity * p.entry_price for p in positions)
            current_value = sum(p.quantity * p.current_price for p in positions if p.current_price > 0)
            unrealized_pnl = current_value - invested_value
            
            total_equity = account.available_cash + current_value
            
            today_snapshot = db.query(DailyPortfolioSnapshot).filter(
                DailyPortfolioSnapshot.account_id == account_id,
                DailyPortfolioSnapshot.snapshot_date >= date.today()
            ).first()
            
            prev_snapshot = db.query(DailyPortfolioSnapshot).filter(
                DailyPortfolioSnapshot.account_id == account_id,
                DailyPortfolioSnapshot.snapshot_date < date.today()
            ).order_by(DailyPortfolioSnapshot.snapshot_date.desc()).first()
            
            daily_pnl = 0.0
            if today_snapshot and prev_snapshot:
                daily_pnl = today_snapshot.total_equity - prev_snapshot.total_equity
            
            risk_utilization = 0.0
            if account.total_capital > 0:
                risk_utilization = invested_value / account.total_capital
            
            daily_loss_pct = 0.0
            if prev_snapshot and prev_snapshot.total_equity > 0:
                daily_loss_pct = -daily_pnl / prev_snapshot.total_equity if daily_pnl < 0 else 0.0
            
            return PortfolioSummary(
                total_equity=total_equity,
                cash=account.available_cash,
                invested_value=invested_value,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=0.0,
                daily_pnl=daily_pnl,
                open_positions_count=len(positions),
                risk_utilization_pct=risk_utilization * 100,
                daily_loss_pct=daily_loss_pct * 100
            )
            
        finally:
            db.close()
    
    def _update_position_prices(self, positions: list[Position]):
        try:
            if self.settings.is_dry_run:
                from app.brokers.paper_broker import PaperBrokerProvider
                if isinstance(self.broker, PaperBrokerProvider):
                    for pos in positions:
                        self.broker.update_market_price(pos.symbol, pos.current_price)
            else:
                broker_positions = self.broker.get_positions()
                broker_map = {p.symbol: p for p in broker_positions}
                
                for pos in positions:
                    if pos.symbol in broker_map:
                        bp = broker_map[pos.symbol]
                        pos.current_price = bp.current_price
                        pos.unrealized_pnl = bp.unrealized_pnl
                        
        except Exception as e:
            logger.warning(f"Failed to update position prices: {e}")
    
    def check_stop_loss_targets(self, account_id: int) -> list[Position]:
        db = next(get_db())
        try:
            positions = db.query(Position).filter(
                Position.account_id == account_id,
                Position.status == PositionStatus.OPEN
            ).all()
            
            self._update_position_prices(positions)
            
            triggered = []
            for pos in positions:
                if pos.current_price <= pos.stop_loss:
                    pos.status = PositionStatus.STOPPED_OUT
                    pos.exit_timestamp = datetime.now()
                    pos.exit_price = pos.stop_loss
                    pos.realized_pnl = (pos.stop_loss - pos.entry_price) * pos.quantity
                    triggered.append(pos)
                    logger.warning(f"STOP LOSS TRIGGERED: {pos.symbol} @ {pos.stop_loss}")
                
                elif pos.current_price >= pos.target_price:
                    pos.status = PositionStatus.TARGET_HIT
                    pos.exit_timestamp = datetime.now()
                    pos.exit_price = pos.target_price
                    pos.realized_pnl = (pos.target_price - pos.entry_price) * pos.quantity
                    triggered.append(pos)
                    logger.info(f"TARGET HIT: {pos.symbol} @ {pos.target_price}")
            
            if triggered:
                db.commit()
            
            return triggered
            
        finally:
            db.close()
    
    def close_position(self, account_id: int, symbol: str, reason: str = "MANUALLY_CLOSED") -> bool:
        db = next(get_db())
        try:
            position = db.query(Position).filter(
                Position.account_id == account_id,
                Position.symbol == symbol,
                Position.status == PositionStatus.OPEN
            ).first()
            
            if not position:
                return False
            
            self._update_position_prices([position])
            
            position.status = PositionStatus.MANUALLY_CLOSED
            position.exit_timestamp = datetime.now()
            position.exit_price = position.current_price
            position.realized_pnl = (position.current_price - position.entry_price) * position.quantity
            
            account = db.query(Account).filter(Account.id == account_id).first()
            if account:
                account.available_cash += position.quantity * position.current_price
            
            db.commit()
            logger.info(f"Position closed: {symbol} @ {position.current_price} ({reason})")
            return True
            
        except Exception as e:
            logger.error(f"Close position failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def create_daily_snapshot(self, account_id: int) -> DailyPortfolioSnapshot:
        db = next(get_db())
        try:
            summary = self.get_portfolio_summary(account_id)
            
            snapshot = DailyPortfolioSnapshot(
                account_id=account_id,
                snapshot_date=datetime.now(),
                total_equity=summary.total_equity,
                cash=summary.cash,
                invested_value=summary.invested_value,
                unrealized_pnl=summary.unrealized_pnl,
                realized_pnl=summary.realized_pnl,
                daily_pnl=summary.daily_pnl,
                open_positions_count=summary.open_positions_count
            )
            
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            
            logger.info(f"Daily snapshot created: equity={summary.total_equity:.2f}")
            return snapshot
            
        finally:
            db.close()
    
    def get_open_positions(self, account_id: int) -> list[Position]:
        db = next(get_db())
        try:
            positions = db.query(Position).filter(
                Position.account_id == account_id,
                Position.status == PositionStatus.OPEN
            ).all()
            
            self._update_position_prices(positions)
            return positions
            
        finally:
            db.close()
    
    def get_position_r_multiple(self, position: Position) -> Optional[float]:
        if position.current_price <= 0 or position.entry_price <= position.stop_loss:
            return None
        
        risk_per_share = position.entry_price - position.stop_loss
        current_r = (position.current_price - position.entry_price) / risk_per_share
        return current_r
    
    def get_holding_duration_days(self, position: Position) -> int:
        if position.entry_timestamp:
            return (datetime.now() - position.entry_timestamp).days
        return 0