from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum
import pandas as pd
import numpy as np
import logging

from app.strategies.indicators import add_indicators, get_recent_swing_low
from app.strategies.ema_pullback import TradeSignal, EMAPullbackStrategy
from app.risk.manager import RiskManager, RejectionReason
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class BacktestPositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOPPED_OUT = "STOPPED_OUT"
    TARGET_HIT = "TARGET_HIT"


@dataclass
class BacktestPosition:
    symbol: str
    entry_date: date
    entry_price: float
    stop_loss: float
    target_price: float
    quantity: int
    risk_amount: float
    risk_reward_ratio: float
    status: BacktestPositionStatus = BacktestPositionStatus.OPEN
    exit_date: Optional[date] = None
    exit_price: Optional[float] = None
    realized_pnl: float = 0.0
    r_multiple: float = 0.0
    holding_days: int = 0


@dataclass
class BacktestTrade:
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


@dataclass
class BacktestResult:
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
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)


class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100000,
        max_risk_percent: float = 0.01,
        max_daily_loss_percent: float = 0.02,
        max_open_positions: int = 3,
        max_stop_loss_percent: float = 0.08,
        min_risk_reward: float = 2.0,
        swing_low_lookback: int = 5,
        transaction_cost_bps: float = 10.0,
        slippage_bps: float = 5.0,
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_risk_percent = max_risk_percent
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_open_positions = max_open_positions
        self.max_stop_loss_percent = max_stop_loss_percent
        self.min_risk_reward = min_risk_reward
        self.swing_low_lookback = swing_low_lookback
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps
        
        self.settings = get_settings()
        self.strategy = EMAPullbackStrategy(self.settings)
        self.risk_manager = RiskManager(self.settings)
        
        self.open_positions: List[BacktestPosition] = []
        self.closed_trades: List[BacktestTrade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.daily_equity: dict[date, float] = {}
        self.daily_pnl: dict[date, float] = {}
    
    def run(self, historical_data: dict[str, pd.DataFrame]) -> BacktestResult:
        all_dates = set()
        for df in historical_data.values():
            all_dates.update(df.index.date)
        
        sorted_dates = sorted(all_dates)
        
        for current_date in sorted_dates:
            self._process_date(current_date, historical_data)
            self._update_equity(current_date, historical_data)
        
        self._close_all_positions(sorted_dates[-1], historical_data)
        
        return self._calculate_results()
    
    def _process_date(self, current_date: date, historical_data: dict[str, pd.DataFrame]):
        daily_pnl = 0.0
        
        positions_to_close = []
        for i, pos in enumerate(self.open_positions):
            if pos.symbol not in historical_data:
                continue
            
            df = historical_data[pos.symbol]
            day_data = df[df.index.date == current_date]
            
            if day_data.empty:
                continue
            
            day_low = day_data['Low'].iloc[0]
            day_high = day_data['High'].iloc[0]
            day_close = day_data['Close'].iloc[0]
            
            if day_low <= pos.stop_loss:
                exit_price = pos.stop_loss * (1 - self.slippage_bps / 10000)
                positions_to_close.append((i, exit_price, current_date, "STOP_LOSS", BacktestPositionStatus.STOPPED_OUT))
            elif day_high >= pos.target_price:
                exit_price = pos.target_price * (1 - self.slippage_bps / 10000)
                positions_to_close.append((i, exit_price, current_date, "TARGET", BacktestPositionStatus.TARGET_HIT))
        
        for idx, exit_price, exit_date, reason, status in reversed(positions_to_close):
            pos = self.open_positions.pop(idx)
            self._close_position(pos, exit_price, exit_date, reason, status)
            daily_pnl += pos.realized_pnl
        
        if len(self.open_positions) < self.max_open_positions:
            daily_loss_limit = self.capital * self.max_daily_loss_percent
            if sum(self.daily_pnl.get(d, 0) for d in self.daily_pnl if d <= current_date) > -daily_loss_limit:
                for symbol, df in historical_data.items():
                    if any(p.symbol == symbol for p in self.open_positions):
                        continue
                    
                    day_data = df[df.index.date == current_date]
                    if day_data.empty:
                        continue
                    
                    historical_up_to_date = df[df.index.date <= current_date].copy()
                    if len(historical_up_to_date) < 60:
                        continue
                    
                    from app.market_data.provider import MarketData
                    market_data = MarketData(
                        symbol=symbol,
                        dataframe=historical_up_to_date,
                        fetched_at=datetime.now(),
                        source="BACKTEST"
                    )
                    
                    signal = self.strategy.analyze(market_data)
                    
                    if signal and signal.decision == "PENDING":
                        class MockAccount:
                            total_capital = self.capital
                            available_cash = self.capital
                        
                        class MockRiskSettings:
                            max_risk_percent = self.max_risk_percent
                            max_daily_loss_percent = self.max_daily_loss_percent
                            max_open_positions = self.max_open_positions
                            max_stop_loss_percent = self.max_stop_loss_percent
                            min_risk_reward = self.min_risk_reward
                            max_position_concentration_percent = 0.3
                            max_sector_concentration_percent = 0.5
                        
                        risk_check = self.risk_manager.validate_signal(
                            signal=signal,
                            account=MockAccount(),
                            risk_settings=MockRiskSettings(),
                            open_positions=[
                                type('MockPos', (), {
                                    'symbol': p.symbol,
                                    'status': 'OPEN',
                                    'entry_price': p.entry_price,
                                    'stop_loss': p.stop_loss,
                                    'quantity': p.quantity
                                })() for p in self.open_positions
                            ],
                            daily_pnl=sum(t.pnl for t in self.closed_trades if t.exit_date == current_date),
                            available_cash=self.capital,
                            event_risk=False
                        )
                        
                        if risk_check.passed:
                            signal.quantity = risk_check.quantity
                            signal.risk_amount = risk_check.risk_amount
                            
                            cost = signal.quantity * signal.entry_price * (1 + self.transaction_cost_bps / 10000)
                            if cost <= self.capital:
                                self.capital -= cost
                                
                                new_pos = BacktestPosition(
                                    symbol=signal.symbol,
                                    entry_date=current_date,
                                    entry_price=signal.entry_price * (1 + self.slippage_bps / 10000),
                                    stop_loss=signal.stop_loss,
                                    target_price=signal.target_price,
                                    quantity=signal.quantity,
                                    risk_amount=signal.risk_amount,
                                    risk_reward_ratio=signal.risk_reward_ratio
                                )
                                self.open_positions.append(new_pos)
    
    def _close_position(self, pos: BacktestPosition, exit_price: float, exit_date: date, reason: str, status: BacktestPositionStatus):
        pos.status = status
        pos.exit_date = exit_date
        pos.exit_price = exit_price * (1 - self.transaction_cost_bps / 10000)
        pos.realized_pnl = (pos.exit_price - pos.entry_price) * pos.quantity
        pos.r_multiple = pos.realized_pnl / pos.risk_amount if pos.risk_amount > 0 else 0
        pos.holding_days = (exit_date - pos.entry_date).days
        
        self.capital += pos.quantity * pos.exit_price
        
        trade = BacktestTrade(
            symbol=pos.symbol,
            entry_date=pos.entry_date,
            entry_price=pos.entry_price,
            exit_date=exit_date,
            exit_price=pos.exit_price,
            quantity=pos.quantity,
            pnl=pos.realized_pnl,
            r_multiple=pos.r_multiple,
            holding_days=pos.holding_days,
            exit_reason=reason
        )
        self.closed_trades.append(trade)
    
    def _close_all_positions(self, last_date: date, historical_data: dict[str, pd.DataFrame]):
        for pos in self.open_positions[:]:
            if pos.symbol in historical_data:
                df = historical_data[pos.symbol]
                last_data = df[df.index.date <= last_date]
                if not last_data.empty:
                    exit_price = last_data['Close'].iloc[-1]
                else:
                    exit_price = pos.entry_price
            else:
                exit_price = pos.entry_price
            
            self._close_position(pos, exit_price, last_date, "END_OF_DATA", BacktestPositionStatus.CLOSED)
        
        self.open_positions.clear()
    
    def _update_equity(self, current_date: date, historical_data: dict[str, pd.DataFrame]):
        portfolio_value = self.capital
        
        for pos in self.open_positions:
            if pos.symbol in historical_data:
                df = historical_data[pos.symbol]
                day_data = df[df.index.date == current_date]
                if not day_data.empty:
                    portfolio_value += pos.quantity * day_data['Close'].iloc[0]
                else:
                    portfolio_value += pos.quantity * pos.entry_price
        
        self.equity_curve.append(portfolio_value)
        self.daily_equity[current_date] = portfolio_value
        
        prev_equity = list(self.daily_equity.values())[-2] if len(self.daily_equity) > 1 else self.initial_capital
        self.daily_pnl[current_date] = portfolio_value - prev_equity
    
    def _calculate_results(self) -> BacktestResult:
        if not self.closed_trades:
            return BacktestResult(
                initial_capital=self.initial_capital,
                final_capital=self.capital,
                total_return=0,
                total_return_pct=0,
                max_drawdown=0,
                max_drawdown_pct=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                profit_factor=0,
                avg_r_multiple=0,
                avg_holding_days=0,
                sharpe_ratio=0
            )
        
        total_return = self.capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = running_max - equity_array
        max_drawdown = np.max(drawdown)
        max_drawdown_pct = (max_drawdown / np.max(running_max)) * 100 if np.max(running_max) > 0 else 0
        
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(self.closed_trades) * 100 if self.closed_trades else 0
        
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_r_multiple = np.mean([t.r_multiple for t in self.closed_trades])
        avg_holding_days = np.mean([t.holding_days for t in self.closed_trades])
        
        daily_returns = np.array(list(self.daily_pnl.values()))
        if len(daily_returns) > 1 and np.std(daily_returns) > 0:
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            total_trades=len(self.closed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_r_multiple=avg_r_multiple,
            avg_holding_days=avg_holding_days,
            sharpe_ratio=sharpe_ratio,
            trades=self.closed_trades,
            equity_curve=self.equity_curve,
            daily_returns=list(self.daily_pnl.values())
        )


def run_backtest(
    symbols: List[str],
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    **kwargs
) -> BacktestResult:
    import yfinance as yf
    
    historical_data = {}
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date, interval="1d")
        if not hist.empty:
            hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            hist.index = pd.to_datetime(hist.index)
            hist = hist.sort_index()
            historical_data[symbol] = hist
    
    engine = BacktestEngine(initial_capital=initial_capital, **kwargs)
    return engine.run(historical_data)