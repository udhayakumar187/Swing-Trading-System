from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import numpy as np
import pandas as pd

from app.patterns.models import (
    PatternDetection,
    PatternCategory,
    PatternDirection,
    PatternStatus,
    OHLCVData,
    Timeframe,
)
from app.patterns.detectors.base import PatternDetector
from app.patterns.registry import PatternRegistry


@dataclass
class BacktestConfig:
    transaction_cost_pct: float = 0.001
    slippage_pct: float = 0.0005
    max_holding_period: int = 60
    stop_loss_pct: float = 0.05
    target_multiple: float = 2.0


@dataclass
class PatternTrade:
    pattern_name: str
    symbol: str
    timeframe: Timeframe
    entry_time: datetime
    entry_price: float
    direction: PatternDirection
    stop_loss: float
    target: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_period: int = 0
    mfe: float = 0.0
    mae: float = 0.0


@dataclass
class PatternBacktestResult:
    pattern_name: str
    symbol: str
    timeframe: Timeframe
    total_occurrences: int
    confirmed_count: int
    invalidated_count: int
    target_reached: int
    stop_reached: int
    avg_return: float
    median_return: float
    avg_mfe: float
    avg_mae: float
    avg_holding_period: float
    win_count: int
    loss_count: int
    profit_factor: float
    max_drawdown: float
    trades: List[PatternTrade] = field(default_factory=list)


class PatternBacktester:
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

    def backtest_pattern(
        self,
        detector: PatternDetector,
        data: OHLCVData,
        start_idx: int = 0,
    ) -> PatternBacktestResult:
        trades = []
        detections_by_time = {}

        for i in range(start_idx + detector.get_required_candles(), len(data.candles)):
            window_data = OHLCVData(
                symbol=data.symbol,
                timeframe=data.timeframe,
                candles=data.candles[:i+1],
            )
            try:
                detections = detector.detect(window_data)
                for det in detections:
                    if det.status in [PatternStatus.CONFIRMED, PatternStatus.FORMING]:
                        key = f"{det.pattern_name}_{det.start_timestamp}"
                        if key not in detections_by_time:
                            detections_by_time[key] = det
                            trade = self._simulate_trade(data, det, i)
                            if trade:
                                trades.append(trade)
            except Exception:
                continue

        return self._calculate_results(detector.get_name(), data.symbol, data.timeframe, trades)

    def backtest_all_patterns(
        self,
        registry: PatternRegistry,
        data: OHLCVData,
        categories: Optional[List[PatternCategory]] = None,
    ) -> Dict[str, PatternBacktestResult]:
        results = {}
        detectors = registry.detect_all(data, categories=categories)

        detector_names = set(d.pattern_name for d in detectors)
        for name in detector_names:
            detector = registry.get(name)
            if detector:
                results[name] = self.backtest_pattern(detector, data)

        return results

    def _simulate_trade(
        self,
        data: OHLCVData,
        detection: PatternDetection,
        detection_idx: int,
    ) -> Optional[PatternTrade]:
        if detection_idx + 1 >= len(data.candles):
            return None

        entry_price = data.candles[detection_idx + 1].open
        direction = detection.direction

        if direction == PatternDirection.BULLISH:
            stop_loss = detection.invalidation_level or entry_price * (1 - self.config.stop_loss_pct)
            target = detection.target_levels.get("target_1", entry_price * (1 + self.config.stop_loss_pct * self.config.target_multiple))
        elif direction == PatternDirection.BEARISH:
            stop_loss = detection.invalidation_level or entry_price * (1 + self.config.stop_loss_pct)
            target = detection.target_levels.get("target_1", entry_price * (1 - self.config.stop_loss_pct * self.config.target_multiple))
        else:
            return None

        trade = PatternTrade(
            pattern_name=detection.pattern_name,
            symbol=data.symbol,
            timeframe=data.timeframe,
            entry_time=data.candles[detection_idx + 1].timestamp,
            entry_price=entry_price,
            direction=direction,
            stop_loss=stop_loss,
            target=target,
        )

        max_idx = min(detection_idx + self.config.max_holding_period + 1, len(data.candles) - 1)
        max_favorable = 0.0
        max_adverse = 0.0

        for j in range(detection_idx + 1, max_idx + 1):
            candle = data.candles[j]
            high = candle.high
            low = candle.low

            if direction == PatternDirection.BULLISH:
                favorable = (high - entry_price) / entry_price
                adverse = (entry_price - low) / entry_price

                if low <= stop_loss:
                    trade.exit_time = candle.timestamp
                    trade.exit_price = stop_loss
                    trade.exit_reason = "STOP_LOSS"
                    break
                if high >= target:
                    trade.exit_time = candle.timestamp
                    trade.exit_price = target
                    trade.exit_reason = "TARGET"
                    break
            else:
                favorable = (entry_price - low) / entry_price
                adverse = (high - entry_price) / entry_price

                if high >= stop_loss:
                    trade.exit_time = candle.timestamp
                    trade.exit_price = stop_loss
                    trade.exit_reason = "STOP_LOSS"
                    break
                if low <= target:
                    trade.exit_time = candle.timestamp
                    trade.exit_price = target
                    trade.exit_reason = "TARGET"
                    break

            max_favorable = max(max_favorable, favorable)
            max_adverse = max(max_adverse, adverse)

        if trade.exit_time is None:
            last_candle = data.candles[max_idx]
            trade.exit_time = last_candle.timestamp
            trade.exit_price = last_candle.close
            trade.exit_reason = "TIME_EXIT"

        trade.holding_period = (trade.exit_time - trade.entry_time).days if hasattr(trade.exit_time, 'days') else max_idx - detection_idx

        if direction == PatternDirection.BULLISH:
            trade.pnl = trade.exit_price - trade.entry_price
            trade.pnl_pct = trade.pnl / trade.entry_price
            trade.mfe = max_favorable
            trade.mae = max_adverse
        else:
            trade.pnl = trade.entry_price - trade.exit_price
            trade.pnl_pct = trade.pnl / trade.entry_price
            trade.mfe = max_favorable
            trade.mae = max_adverse

        cost = self.config.transaction_cost_pct + self.config.slippage_pct
        trade.pnl_pct -= cost
        trade.pnl = trade.pnl_pct * trade.entry_price

        return trade

    def _calculate_results(
        self,
        pattern_name: str,
        symbol: str,
        timeframe: Timeframe,
        trades: List[PatternTrade],
    ) -> PatternBacktestResult:
        if not trades:
            return PatternBacktestResult(
                pattern_name=pattern_name,
                symbol=symbol,
                timeframe=timeframe,
                total_occurrences=0,
                confirmed_count=0,
                invalidated_count=0,
                target_reached=0,
                stop_reached=0,
                avg_return=0.0,
                median_return=0.0,
                avg_mfe=0.0,
                avg_mae=0.0,
                avg_holding_period=0.0,
                win_count=0,
                loss_count=0,
                profit_factor=0.0,
                max_drawdown=0.0,
            )

        returns = [t.pnl_pct for t in trades]
        mfe_vals = [t.mfe for t in trades]
        mae_vals = [t.mae for t in trades]
        holding = [t.holding_period for t in trades]

        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]

        target_hits = sum(1 for t in trades if t.exit_reason == "TARGET")
        stop_hits = sum(1 for t in trades if t.exit_reason == "STOP_LOSS")

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = abs(min(drawdown)) if len(drawdown) > 0 else 0

        return PatternBacktestResult(
            pattern_name=pattern_name,
            symbol=symbol,
            timeframe=timeframe,
            total_occurrences=len(trades),
            confirmed_count=sum(1 for t in trades if t.exit_reason in ["TARGET", "STOP_LOSS"]),
            invalidated_count=sum(1 for t in trades if t.exit_reason == "TIME_EXIT"),
            target_reached=target_hits,
            stop_reached=stop_hits,
            avg_return=float(np.mean(returns)),
            median_return=float(np.median(returns)),
            avg_mfe=float(np.mean(mfe_vals)),
            avg_mae=float(np.mean(mae_vals)),
            avg_holding_period=float(np.mean(holding)),
            win_count=len(wins),
            loss_count=len(losses),
            profit_factor=profit_factor,
            max_drawdown=max_dd,
            trades=trades,
        )


def run_backtest(
    detector: PatternDetector,
    data: OHLCVData,
    config: Optional[BacktestConfig] = None,
) -> PatternBacktestResult:
    backtester = PatternBacktester(config)
    return backtester.backtest_pattern(detector, data)