import logging
from datetime import datetime, time
from typing import Optional, List
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.database import get_db
from app.market_data import YahooFinanceMarketDataProvider
from app.strategies import EMAPullbackStrategy, TradeSignal
from app.risk import RiskManager, create_event_risk_provider
from app.services.execution_service import ExecutionService
from app.services.portfolio_service import PortfolioService
from app.models.account import Account
from app.models.position import Position, PositionStatus
from app.models.signal import Signal, SignalDecision
from app.models.trading_run import TradingRun, TradingRunStatus
from app.models.risk_settings import RiskSettings
from app.models.watchlist import Watchlist


logger = logging.getLogger(__name__)


@dataclass
class TradingRunResult:
    success: bool
    trading_run: Optional[TradingRun] = None
    signals_generated: int = 0
    signals_rejected: int = 0
    orders_placed: int = 0
    orders_filled: int = 0
    error_message: Optional[str] = None


class TradingService:
    def __init__(self):
        self.settings = get_settings()
        self.market_data_provider = YahooFinanceMarketDataProvider()
        self.strategy = EMAPullbackStrategy()
        self.risk_manager = RiskManager()
        self.event_provider = create_event_risk_provider("dummy")
        self.execution_service = ExecutionService()
        self.portfolio_service = PortfolioService()
    
    def run_daily_trading(self, account_id: int) -> TradingRunResult:
        logger.info(f"Starting daily trading run for account {account_id}")
        
        db = next(get_db())
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account or not account.is_active:
                return TradingRunResult(
                    success=False,
                    error_message="Account not found or inactive"
                )
            
            if not self._is_trading_day():
                return TradingRunResult(
                    success=False,
                    error_message="Not a trading day"
                )
            
            existing_run = db.query(TradingRun).filter(
                TradingRun.account_id == account_id,
                TradingRun.run_date >= datetime.now().date(),
                TradingRun.status.in_([
                    TradingRunStatus.COMPLETED,
                    TradingRunStatus.ORDERS_PLACED
                ])
            ).first()
            
            if existing_run:
                return TradingRunResult(
                    success=False,
                    error_message="Trading run already completed for today"
                )
            
            trading_run = TradingRun(
                account_id=account_id,
                run_date=datetime.now(),
                status=TradingRunStatus.STARTED,
                paper_or_live="DRY_RUN" if self.settings.is_dry_run else "LIVE"
            )
            db.add(trading_run)
            db.commit()
            db.refresh(trading_run)
            
            try:
                result = self._execute_trading_pipeline(account, trading_run, db)
                return result
            except Exception as e:
                trading_run.status = TradingRunStatus.FAILED
                trading_run.error_message = str(e)
                trading_run.completed_at = datetime.now()
                db.commit()
                logger.error(f"Trading run failed: {e}")
                return TradingRunResult(
                    success=False,
                    trading_run=trading_run,
                    error_message=str(e)
                )
                
        finally:
            db.close()
    
    def _is_trading_day(self) -> bool:
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        return True
    
    def _execute_trading_pipeline(
        self,
        account: Account,
        trading_run: TradingRun,
        db
    ) -> TradingRunResult:
        risk_settings = db.query(RiskSettings).filter(
            RiskSettings.account_id == account.id
        ).first()
        
        if not risk_settings:
            risk_settings = RiskSettings(account_id=account.id)
            db.add(risk_settings)
            db.commit()
            db.refresh(risk_settings)
        
        watchlist = db.query(Watchlist).filter(
            Watchlist.account_id == account.id,
            Watchlist.is_active == True
        ).all()
        
        symbols = [w.symbol for w in watchlist]
        
        if not symbols:
            symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS", "HDFCBANK.NS"]
        
        logger.info(f"Scanning {len(symbols)} symbols")
        
        trading_run.status = TradingRunStatus.MARKET_DATA_FETCHED
        trading_run.symbols_scanned = len(symbols)
        db.commit()
        
        market_data_dict = self.market_data_provider.fetch_multiple_symbols(symbols)
        valid_symbols = list(market_data_dict.keys())
        trading_run.symbols_scanned = len(valid_symbols)
        db.commit()
        
        if not valid_symbols:
            trading_run.status = TradingRunStatus.COMPLETED
            trading_run.completed_at = datetime.now()
            db.commit()
            return TradingRunResult(success=True, trading_run=trading_run)
        
        signals = self.strategy.analyze_batch(market_data_dict)
        
        trading_run.status = TradingRunStatus.SIGNALS_GENERATED
        trading_run.signals_generated = len(signals)
        db.commit()
        
        open_positions = db.query(Position).filter(
            Position.account_id == account.id,
            Position.status == PositionStatus.OPEN
        ).all()
        
        daily_pnl = 0.0
        
        event_risk_symbols = set()
        if not self.settings.is_dry_run:
            event_check = self.event_provider.get_upcoming_events(valid_symbols, risk_settings.event_exclusion_window)
            for symbol, events in event_check.items():
                for event in events:
                    if event.impact.value == "HIGH":
                        event_risk_symbols.add(symbol)
        
        accepted_signals = []
        rejected_signals = []
        
        for signal in signals:
            if signal.decision == "REJECTED":
                rejected_signals.append(signal)
                continue
            
            event_risk = signal.symbol in event_risk_symbols
            
            risk_check = self.risk_manager.validate_signal(
                signal=signal,
                account=account,
                risk_settings=risk_settings,
                open_positions=open_positions,
                daily_pnl=daily_pnl,
                available_cash=account.available_cash,
                event_risk=event_risk
            )
            
            signal_obj = Signal(
                account_id=account.id,
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                signal_timestamp=signal.signal_timestamp,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                target_price=signal.target_price,
                risk_amount=signal.risk_amount,
                risk_reward_ratio=signal.risk_reward_ratio,
                strategy_name=signal.strategy_name,
                decision=SignalDecision.ACCEPTED if risk_check.passed else SignalDecision.REJECTED,
                reason=risk_check.details if not risk_check.passed else None,
                trading_run_id=trading_run.id
            )
            db.add(signal_obj)
            
            if risk_check.passed:
                signal.quantity = risk_check.quantity
                signal.risk_amount = risk_check.risk_amount
                accepted_signals.append(signal)
                open_positions.append(type('MockPos', (), {
                    'symbol': signal.symbol,
                    'status': PositionStatus.OPEN,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'quantity': signal.quantity
                })())
            else:
                signal.decision = "REJECTED"
                signal.reason = risk_check.reason.value if risk_check.reason else "UNKNOWN"
                rejected_signals.append(signal)
        
        db.commit()
        
        trading_run.signals_rejected = len(rejected_signals)
        trading_run.status = TradingRunStatus.RISK_CHECKED
        db.commit()
        
        orders_filled = 0
        for signal in accepted_signals:
            trading_run.orders_attempted += 1
            db.commit()
            
            result = self.execution_service.execute_signal(signal, trading_run, account.id)
            
            if result.success:
                orders_filled += 1
                trading_run.orders_completed += 1
                account.available_cash -= signal.quantity * signal.entry_price
            else:
                trading_run.orders_rejected += 1
            
            db.commit()
        
        trading_run.status = TradingRunStatus.ORDERS_PLACED
        trading_run.orders_completed = orders_filled
        db.commit()
        
        trading_run.status = TradingRunStatus.COMPLETED
        trading_run.completed_at = datetime.now()
        db.commit()
        
        logger.info(
            f"Trading run completed: scanned={trading_run.symbols_scanned}, "
            f"signals={trading_run.signals_generated}, rejected={trading_run.signals_rejected}, "
            f"orders={trading_run.orders_completed}/{trading_run.orders_attempted}"
        )
        
        return TradingRunResult(
            success=True,
            trading_run=trading_run,
            signals_generated=trading_run.signals_generated,
            signals_rejected=trading_run.signals_rejected,
            orders_placed=trading_run.orders_attempted,
            orders_filled=orders_filled
        )
    
    def run_manual_trading(self, account_id: int) -> TradingRunResult:
        return self.run_daily_trading(account_id)
    
    def reconcile_and_check_positions(self, account_id: int):
        self.execution_service.reconcile_orders(account_id)
        self.portfolio_service.check_stop_loss_targets(account_id)
        self.portfolio_service.create_daily_snapshot(account_id)