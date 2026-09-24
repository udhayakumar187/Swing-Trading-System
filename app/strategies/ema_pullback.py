from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pandas as pd
import logging

from app.market_data.provider import MarketData, DataValidationError
from app.strategies.indicators import (
    add_indicators, 
    find_swing_lows, 
    get_recent_swing_low
)
from app.core.config import get_settings


logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    symbol: str
    signal_type: str
    signal_timestamp: datetime
    entry_price: float
    stop_loss: float
    target_price: float
    risk_amount: float
    risk_reward_ratio: float
    strategy_name: str
    decision: str = "PENDING"
    reason: Optional[str] = None


class EMAPullbackStrategy:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.ema_period = 20
        self.sma_period = 50
        self.vol_period = 20
        self.ema_pullback_pct = 0.005
        self.volume_multiplier = 1.0
        self.swing_low_lookback = self.settings.SWING_LOW_LOOKBACK
        self.max_stop_loss_pct = self.settings.MAX_STOP_LOSS_PERCENT
        self.min_risk_reward = self.settings.MIN_RISK_REWARD
    
    def analyze(self, market_data: MarketData) -> Optional[TradeSignal]:
        df = market_data.dataframe.copy()
        
        if len(df) < max(self.sma_period, self.ema_period, self.vol_period) + 5:
            logger.warning(f"{market_data.symbol}: Insufficient data for indicators")
            return None
        
        df = add_indicators(df, self.ema_period, self.sma_period, self.vol_period)
        
        if df.iloc[-1:].isnull().any().any():
            logger.warning(f"{market_data.symbol}: NaN in latest indicators")
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        
        if prev is None:
            return None
        
        conditions = {
            'close_above_sma50': latest['Close'] > latest['SMA_50'],
            'sma50_rising': latest['SMA_50'] > latest['SMA_50_prev'],
            'low_near_ema20': latest['Low'] <= latest['EMA_20'] * (1 + self.ema_pullback_pct),
            'volume_confirmed': latest['Volume'] > latest['Avg_Vol_20'] * self.volume_multiplier,
        }
        
        all_met = all(conditions.values())
        
        logger.info(
            f"{market_data.symbol} Conditions: "
            f"Close>SMA50={conditions['close_above_sma50']}, "
            f"SMA50 Rising={conditions['sma50_rising']}, "
            f"Low near EMA20={conditions['low_near_ema20']}, "
            f"Vol Confirmed={conditions['volume_confirmed']}"
        )
        
        if not all_met:
            failed = [k for k, v in conditions.items() if not v]
            return TradeSignal(
                symbol=market_data.symbol,
                signal_type="BUY",
                signal_timestamp=market_data.dataframe.index[-1].to_pydatetime(),
                entry_price=0.0,
                stop_loss=0.0,
                target_price=0.0,
                risk_amount=0.0,
                risk_reward_ratio=0.0,
                strategy_name="EMAPullbackStrategy",
                decision="REJECTED",
                reason=f"Conditions not met: {', '.join(failed)}"
            )
        
        swing_low = get_recent_swing_low(df, self.swing_low_lookback)
        
        if swing_low is None:
            logger.warning(f"{market_data.symbol}: No valid swing low found")
            return TradeSignal(
                symbol=market_data.symbol,
                signal_type="BUY",
                signal_timestamp=market_data.dataframe.index[-1].to_pydatetime(),
                entry_price=0.0,
                stop_loss=0.0,
                target_price=0.0,
                risk_amount=0.0,
                risk_reward_ratio=0.0,
                strategy_name="EMAPullbackStrategy",
                decision="REJECTED",
                reason="SIGNAL_REJECTED_NO_SWING_LOW"
            )
        
        entry_price = float(latest['Close'])
        stop_loss = float(swing_low)
        
        if stop_loss <= 0:
            logger.warning(f"{market_data.symbol}: Invalid stop loss <= 0")
            return TradeSignal(
                symbol=market_data.symbol,
                signal_type="BUY",
                signal_timestamp=market_data.dataframe.index[-1].to_pydatetime(),
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=0.0,
                risk_amount=0.0,
                risk_reward_ratio=0.0,
                strategy_name="EMAPullbackStrategy",
                decision="REJECTED",
                reason="SIGNAL_REJECTED_STOP_INVALID"
            )
        
        stop_loss_distance = entry_price - stop_loss
        stop_loss_pct = stop_loss_distance / entry_price
        
        if stop_loss_pct > self.max_stop_loss_pct:
            logger.warning(
                f"{market_data.symbol}: Stop loss too wide: "
                f"{stop_loss_pct:.2%} > {self.max_stop_loss_pct:.2%}"
            )
            return TradeSignal(
                symbol=market_data.symbol,
                signal_type="BUY",
                signal_timestamp=market_data.dataframe.index[-1].to_pydatetime(),
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=0.0,
                risk_amount=0.0,
                risk_reward_ratio=0.0,
                strategy_name="EMAPullbackStrategy",
                decision="REJECTED",
                reason="SIGNAL_REJECTED_STOP_TOO_WIDE"
            )
        
        risk_per_share = stop_loss_distance
        target_price = entry_price + (risk_per_share * self.min_risk_reward)
        risk_reward_ratio = (target_price - entry_price) / risk_per_share
        
        return TradeSignal(
            symbol=market_data.symbol,
            signal_type="BUY",
            signal_timestamp=market_data.dataframe.index[-1].to_pydatetime(),
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            risk_amount=0.0,
            risk_reward_ratio=risk_reward_ratio,
            strategy_name="EMAPullbackStrategy",
            decision="PENDING",
            reason=None
        )
    
    def analyze_batch(self, market_data_dict: dict[str, MarketData]) -> list[TradeSignal]:
        signals = []
        for symbol, data in market_data_dict.items():
            try:
                signal = self.analyze(data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        return signals