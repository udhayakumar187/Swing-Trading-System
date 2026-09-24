from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_db
from app.core.config import get_settings
from app.services.trading_service import TradingService
from app.services.portfolio_service import PortfolioService
from app.models.account import Account
from app.models.position import Position, PositionStatus
from app.models.order import Order
from app.models.signal import Signal
from app.models.trading_run import TradingRun
from app.models.risk_settings import RiskSettings
from app.schemas.trading import (
    PositionResponse, OrderResponse, SignalResponse, TradingRunResponse,
    RiskSettingsResponse, RiskSettingsUpdate, PortfolioSummary,
    HealthResponse
)


router = APIRouter(prefix="/api", tags=["trading"])


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    account_id: int = Query(1, description="Account ID"),
    status: Optional[PositionStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    query = db.query(Position).filter(Position.account_id == account_id)
    if status:
        query = query.filter(Position.status == status)
    positions = query.order_by(desc(Position.entry_timestamp)).all()
    return positions


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    account_id: int = Query(1, description="Account ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(Order).filter(Order.account_id == account_id)
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(desc(Order.created_at)).limit(limit).all()
    return orders


@router.get("/signals", response_model=List[SignalResponse])
async def get_signals(
    account_id: int = Query(1, description="Account ID"),
    decision: Optional[str] = Query(None, description="Filter by decision"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(Signal).filter(Signal.account_id == account_id)
    if decision:
        query = query.filter(Signal.decision == decision)
    signals = query.order_by(desc(Signal.signal_timestamp)).limit(limit).all()
    return signals


@router.get("/trading-runs", response_model=List[TradingRunResponse])
async def get_trading_runs(
    account_id: int = Query(1, description="Account ID"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    runs = db.query(TradingRun).filter(
        TradingRun.account_id == account_id
    ).order_by(desc(TradingRun.run_date)).limit(limit).all()
    return runs


@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio(
    account_id: int = Query(1, description="Account ID"),
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    portfolio_service = PortfolioService()
    summary = portfolio_service.get_portfolio_summary(account_id)
    return summary


@router.get("/risk-settings", response_model=RiskSettingsResponse)
async def get_risk_settings(
    account_id: int = Query(1, description="Account ID"),
    db: Session = Depends(get_db)
):
    settings = db.query(RiskSettings).filter(RiskSettings.account_id == account_id).first()
    if not settings:
        settings = RiskSettings(account_id=account_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.post("/risk-settings", response_model=RiskSettingsResponse)
async def update_risk_settings(
    update: RiskSettingsUpdate,
    account_id: int = Query(1, description="Account ID"),
    db: Session = Depends(get_db)
):
    settings = db.query(RiskSettings).filter(RiskSettings.account_id == account_id).first()
    if not settings:
        settings = RiskSettings(account_id=account_id)
        db.add(settings)
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    return settings


@router.post("/trading/run", response_model=dict)
async def run_trading_manually(
    account_id: int = Query(1, description="Account ID"),
    db: Session = Depends(get_db)
):
    settings = get_settings()
    
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not account.is_active:
        raise HTTPException(status_code=400, detail="Account is not active")
    
    trading_service = TradingService()
    result = trading_service.run_manual_trading(account_id)
    
    return {
        "success": result.success,
        "trading_run_id": result.trading_run.id if result.trading_run else None,
        "signals_generated": result.signals_generated,
        "signals_rejected": result.signals_rejected,
        "orders_placed": result.orders_placed,
        "orders_filled": result.orders_filled,
        "error_message": result.error_message,
        "execution_mode": "DRY_RUN" if settings.is_dry_run else "LIVE"
    }


@router.get("/account", response_model=dict)
async def get_account_info(
    account_id: int = Query(1, description="Account ID"),
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return {
        "id": account.id,
        "broker_name": account.broker_name,
        "client_id": account.client_id,
        "account_name": account.account_name,
        "is_active": account.is_active,
        "is_paper": account.is_paper,
        "total_capital": account.total_capital,
        "available_cash": account.available_cash,
        "max_risk_percent": account.max_risk_percent,
        "max_daily_loss_percent": account.max_daily_loss_percent,
        "max_open_positions": account.max_open_positions,
        "max_stop_loss_percent": account.max_stop_loss_percent,
        "min_risk_reward": account.min_risk_reward,
    }


@router.get("/logs")
async def get_logs(
    account_id: int = Query(1, description="Account ID"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    from app.models.audit_log import AuditLog
    
    logs = db.query(AuditLog).filter(
        AuditLog.account_id == account_id
    ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "event_code": log.event_code,
            "message": log.message,
            "severity": log.severity,
            "symbol": log.symbol,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]