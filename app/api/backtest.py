from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

from app.backtesting import run_backtest, BacktestResult


router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    symbols: List[str] = Field(..., min_items=1, max_items=50)
    start_date: date
    end_date: date
    initial_capital: float = Field(default=100000, gt=0)
    max_risk_percent: float = Field(default=0.01, ge=0, le=1)
    max_daily_loss_percent: float = Field(default=0.02, ge=0, le=1)
    max_open_positions: int = Field(default=3, ge=1, le=20)
    max_stop_loss_percent: float = Field(default=0.08, ge=0, le=1)
    min_risk_reward: float = Field(default=2.0, gt=0)
    swing_low_lookback: int = Field(default=5, ge=1, le=20)
    transaction_cost_bps: float = Field(default=10.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)


class TradeResponse(BaseModel):
    symbol: str
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    quantity: int
    pnl: float
    r_multiple: float
    holding_days: int
    exit_reason: str


class BacktestResponse(BaseModel):
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_r_multiple: float
    avg_holding_days: float
    sharpe_ratio: float
    trades: List[TradeResponse]
    equity_curve: List[float]
    daily_returns: List[float]


@router.post("/run", response_model=BacktestResponse)
async def run_backtest_endpoint(request: BacktestRequest):
    try:
        result = run_backtest(
            symbols=request.symbols,
            start_date=request.start_date.isoformat(),
            end_date=request.end_date.isoformat(),
            initial_capital=request.initial_capital,
            max_risk_percent=request.max_risk_percent,
            max_daily_loss_percent=request.max_daily_loss_percent,
            max_open_positions=request.max_open_positions,
            max_stop_loss_percent=request.max_stop_loss_percent,
            min_risk_reward=request.min_risk_reward,
            swing_low_lookback=request.swing_low_lookback,
            transaction_cost_bps=request.transaction_cost_bps,
            slippage_bps=request.slippage_bps,
        )
        
        return BacktestResponse(
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return=result.total_return,
            total_return_pct=result.total_return_pct,
            max_drawdown=result.max_drawdown,
            max_drawdown_pct=result.max_drawdown_pct,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor if result.profit_factor != float('inf') else 999,
            avg_r_multiple=result.avg_r_multiple,
            avg_holding_days=result.avg_holding_days,
            sharpe_ratio=result.sharpe_ratio,
            trades=[
                TradeResponse(
                    symbol=t.symbol,
                    entry_date=t.entry_date,
                    entry_price=t.entry_price,
                    exit_date=t.exit_date,
                    exit_price=t.exit_price,
                    quantity=t.quantity,
                    pnl=t.pnl,
                    r_multiple=t.r_multiple,
                    holding_days=t.holding_days,
                    exit_reason=t.exit_reason
                )
                for t in result.trades
            ],
            equity_curve=result.equity_curve,
            daily_returns=result.daily_returns
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def get_backtest_presets():
    return {
        "presets": [
            {
                "name": "NSE Large Cap 1 Year",
                "symbols": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
            {
                "name": "NSE Large Cap 2 Years",
                "symbols": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"],
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
            },
            {
                "name": "Quick Test (3 months)",
                "symbols": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
                "start_date": "2023-10-01",
                "end_date": "2023-12-31",
            }
        ]
    }