import time
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.market_data import YahooFinanceMarketDataProvider
from app.brokers import create_broker_provider
from app.models.trading_run import TradingRun, TradingRunStatus
from app.models.account import Account


@dataclass
class HealthCheckResult:
    name: str
    status: str
    message: str
    duration_ms: float
    timestamp: datetime


class HealthChecker:
    def __init__(self):
        self.settings = get_settings()
        self.market_data_provider = YahooFinanceMarketDataProvider()
        self.broker = create_broker_provider()
    
    def check_database(self, db: Session) -> HealthCheckResult:
        start = time.time()
        try:
            db.execute(text("SELECT 1"))
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name="database",
                status="healthy",
                message="Database connection successful",
                duration_ms=duration,
                timestamp=datetime.now()
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name="database",
                status="unhealthy",
                message=f"Database connection failed: {str(e)}",
                duration_ms=duration,
                timestamp=datetime.now()
            )
    
    def check_market_data(self) -> HealthCheckResult:
        start = time.time()
        try:
            healthy = self.market_data_provider.is_healthy()
            duration = (time.time() - start) * 1000
            if healthy:
                return HealthCheckResult(
                    name="market_data",
                    status="healthy",
                    message="Market data provider responding",
                    duration_ms=duration,
                    timestamp=datetime.now()
                )
            else:
                return HealthCheckResult(
                    name="market_data",
                    status="degraded",
                    message="Market data provider health check failed",
                    duration_ms=duration,
                    timestamp=datetime.now()
                )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name="market_data",
                status="unhealthy",
                message=f"Market data check failed: {str(e)}",
                duration_ms=duration,
                timestamp=datetime.now()
            )
    
    def check_broker(self) -> HealthCheckResult:
        start = time.time()
        try:
            if self.settings.is_dry_run:
                duration = (time.time() - start) * 1000
                return HealthCheckResult(
                    name="broker",
                    status="healthy",
                    message="Paper broker (DRY_RUN mode)",
                    duration_ms=duration,
                    timestamp=datetime.now()
                )
            
            connected = self.broker.is_connected()
            duration = (time.time() - start) * 1000
            
            if connected:
                return HealthCheckResult(
                    name="broker",
                    status="healthy",
                    message="Angel One broker connected",
                    duration_ms=duration,
                    timestamp=datetime.now()
                )
            else:
                return HealthCheckResult(
                    name="broker",
                    status="unhealthy",
                    message="Angel One broker not connected",
                    duration_ms=duration,
                    timestamp=datetime.now()
                )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name="broker",
                status="unhealthy",
                message=f"Broker check failed: {str(e)}",
                duration_ms=duration,
                timestamp=datetime.now()
            )
    
    def check_last_trading_run(self, db: Session) -> HealthCheckResult:
        start = time.time()
        try:
            account = db.query(Account).filter(Account.is_active == True).first()
            if not account:
                return HealthCheckResult(
                    name="last_trading_run",
                    status="warning",
                    message="No active accounts found",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now()
                )
            
            last_run = db.query(TradingRun).filter(
                TradingRun.account_id == account.id
            ).order_by(TradingRun.run_date.desc()).first()
            
            if not last_run:
                return HealthCheckResult(
                    name="last_trading_run",
                    status="warning",
                    message="No trading runs recorded yet",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now()
                )
            
            days_since = (datetime.now().date() - last_run.run_date.date()).days
            
            if last_run.status == TradingRunStatus.FAILED:
                status = "unhealthy"
                message = f"Last run failed: {last_run.error_message}"
            elif days_since > 3:
                status = "warning"
                message = f"Last run was {days_since} days ago"
            elif last_run.status == TradingRunStatus.COMPLETED:
                status = "healthy"
                message = f"Last run completed successfully {days_since} day(s) ago"
            else:
                status = "warning"
                message = f"Last run status: {last_run.status.value}"
            
            return HealthCheckResult(
                name="last_trading_run",
                status=status,
                message=message,
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now()
            )
        except Exception as e:
            return HealthCheckResult(
                name="last_trading_run",
                status="unhealthy",
                message=f"Check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now()
            )
    
    def check_market_data_freshness(self, db: Session) -> HealthCheckResult:
        start = time.time()
        try:
            from app.market_data import YahooFinanceMarketDataProvider
            provider = YahooFinanceMarketDataProvider()
            
            account = db.query(Account).filter(Account.is_active == True).first()
            if not account:
                return HealthCheckResult(
                    name="market_data_freshness",
                    status="warning",
                    message="No active accounts",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now()
                )
            
            from app.models.watchlist import Watchlist
            watchlist = db.query(Watchlist).filter(
                Watchlist.account_id == account.id,
                Watchlist.is_active == True
            ).first()
            
            if not watchlist:
                return HealthCheckResult(
                    name="market_data_freshness",
                    status="warning",
                    message="No watchlist symbols",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now()
                )
            
            data = provider.fetch_historical_data(watchlist.symbol, period="5d")
            latest_date = data.dataframe.index[-1].date()
            days_old = (datetime.now().date() - latest_date).days
            
            if days_old <= 1:
                status = "healthy"
                message = f"Latest data from {latest_date} ({days_old} day(s) old)"
            elif days_old <= 3:
                status = "warning"
                message = f"Data is {days_old} days old (latest: {latest_date})"
            else:
                status = "unhealthy"
                message = f"Stale data: {days_old} days old (latest: {latest_date})"
            
            return HealthCheckResult(
                name="market_data_freshness",
                status=status,
                message=message,
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now()
            )
        except Exception as e:
            return HealthCheckResult(
                name="market_data_freshness",
                status="unhealthy",
                message=f"Freshness check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now()
            )
    
    def run_all_checks(self, db: Session) -> dict:
        checks = [
            self.check_database(db),
            self.check_market_data(),
            self.check_broker(),
            self.check_last_trading_run(db),
            self.check_market_data_freshness(db),
        ]
        
        overall_status = "healthy"
        for check in checks:
            if check.status == "unhealthy":
                overall_status = "unhealthy"
                break
            elif check.status == "warning" and overall_status == "healthy":
                overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "duration_ms": round(c.duration_ms, 2)
                }
                for c in checks
            ],
            "trading_mode": self.settings.TRADING_MODE,
            "timezone": self.settings.TIMEZONE
        }


health_checker = HealthChecker()