import logging
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from app.core.config import get_settings
from app.services.trading_service import TradingService
from app.core.database import get_db
from app.models.account import Account


logger = logging.getLogger(__name__)


class TradingScheduler:
    def __init__(self):
        self.settings = get_settings()
        self.scheduler = BackgroundScheduler(timezone=timezone(self.settings.TIMEZONE))
        self.trading_service = TradingService()
        self._running = False
    
    def start(self):
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        execution_time = self.settings.SIGNAL_EXECUTION_TIME
        hour, minute = map(int, execution_time.split(":"))
        
        self.scheduler.add_job(
            self._run_daily_trading,
            CronTrigger(hour=hour, minute=minute, timezone=self.settings.TIMEZONE),
            id="daily_trading",
            name="Daily Swing Trading Run",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300
        )
        
        self.scheduler.add_job(
            self._reconcile_and_check,
            CronTrigger(hour=15, minute=50, timezone=self.settings.TIMEZONE),
            id="reconcile_positions",
            name="Position Reconciliation & Stop/Target Check",
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.add_job(
            self._create_daily_snapshot,
            CronTrigger(hour=16, minute=0, timezone=self.settings.TIMEZONE),
            id="daily_snapshot",
            name="Daily Portfolio Snapshot",
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.start()
        self._running = True
        logger.info(f"Trading scheduler started. Daily run at {execution_time} {self.settings.TIMEZONE}")
    
    def stop(self):
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Trading scheduler stopped")
    
    def _run_daily_trading(self):
        logger.info("Starting scheduled daily trading run")
        db = next(get_db())
        try:
            accounts = db.query(Account).filter(Account.is_active == True).all()
            for account in accounts:
                try:
                    result = self.trading_service.run_daily_trading(account.id)
                    if result.success:
                        logger.info(f"Daily trading completed for account {account.id}")
                    else:
                        logger.warning(f"Daily trading failed for account {account.id}: {result.error_message}")
                except Exception as e:
                    logger.error(f"Error in daily trading for account {account.id}: {e}")
        finally:
            db.close()
    
    def _reconcile_and_check(self):
        logger.info("Running position reconciliation and stop/target check")
        db = next(get_db())
        try:
            accounts = db.query(Account).filter(Account.is_active == True).all()
            for account in accounts:
                try:
                    self.trading_service.reconcile_and_check_positions(account.id)
                    logger.info(f"Reconciliation completed for account {account.id}")
                except Exception as e:
                    logger.error(f"Error in reconciliation for account {account.id}: {e}")
        finally:
            db.close()
    
    def _create_daily_snapshot(self):
        logger.info("Creating daily portfolio snapshots")
        db = next(get_db())
        try:
            accounts = db.query(Account).filter(Account.is_active == True).all()
            for account in accounts:
                try:
                    self.trading_service.portfolio_service.create_daily_snapshot(account.id)
                except Exception as e:
                    logger.error(f"Error creating snapshot for account {account.id}: {e}")
        finally:
            db.close()
    
    def trigger_manual_run(self, account_id: int):
        logger.info(f"Manual trading run triggered for account {account_id}")
        return self.trading_service.run_manual_trading(account_id)
    
    def get_next_run_time(self) -> datetime | None:
        job = self.scheduler.get_job("daily_trading")
        if job:
            return job.next_run_time
        return None
    
    def is_running(self) -> bool:
        return self._running and self.scheduler.running


_scheduler_instance: TradingScheduler | None = None


def get_scheduler() -> TradingScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TradingScheduler()
    return _scheduler_instance


def start_scheduler():
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None