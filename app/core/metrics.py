from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response, APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.position import Position, PositionStatus
from app.models.order import Order, OrderStatus
from app.models.trading_run import TradingRun, TradingRunStatus
from app.models.account import Account


router = APIRouter(prefix="/api/metrics", tags=["metrics"])

trading_runs_total = Counter(
    'trading_runs_total',
    'Total number of trading runs',
    ['status']
)

signals_generated = Counter(
    'signals_generated_total',
    'Total signals generated',
    ['decision', 'strategy']
)

orders_placed = Counter(
    'orders_placed_total',
    'Total orders placed',
    ['status', 'side', 'type']
)

positions_open = Gauge(
    'positions_open',
    'Number of currently open positions',
    ['symbol']
)

portfolio_value = Gauge(
    'portfolio_value_inr',
    'Total portfolio value in INR'
)

available_cash = Gauge(
    'available_cash_inr',
    'Available cash in INR'
)

daily_pnl = Gauge(
    'daily_pnl_inr',
    'Daily P&L in INR'
)

max_drawdown = Gauge(
    'max_drawdown_pct',
    'Maximum drawdown percentage'
)

trade_duration = Histogram(
    'trade_duration_days',
    'Trade holding duration in days',
    buckets=[1, 2, 3, 5, 7, 10, 14, 21, 30, 60, 90]
)

r_multiple = Histogram(
    'trade_r_multiple',
    'Trade R-multiple',
    buckets=[-3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 3, 5, 10]
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type']
)


def update_metrics(db: Session):
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        
        for account in accounts:
            open_positions = db.query(Position).filter(
                Position.account_id == account.id,
                Position.status == PositionStatus.OPEN
            ).all()
            
            portfolio_value.labels().set(account.total_capital)
            available_cash.labels().set(account.available_cash)
            positions_open.labels().set(len(open_positions))
            
            for pos in open_positions:
                positions_open.labels(symbol=pos.symbol).set(pos.quantity)
        
        recent_runs = db.query(TradingRun).filter(
            TradingRun.run_date >= __import__('datetime').datetime.now() - __import__('datetime').timedelta(days=7)
        ).all()
        
        for run in recent_runs:
            trading_runs_total.labels(status=run.status.value).inc()
        
    except Exception:
        pass


@router.get("")
async def metrics(db: Session = Depends(get_db)):
    update_metrics(db)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)