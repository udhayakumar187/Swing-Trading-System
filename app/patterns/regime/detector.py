from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd

from app.patterns.models import (
    MarketRegime,
    OHLCVData,
)
from app.patterns.indicators.technical import adx, atr, sma


@dataclass
class RegimeConfig:
    adx_period: int = 14
    adx_trend_threshold: float = 25
    atr_period: int = 14
    volatility_lookback: int = 50
    volatility_high_threshold: float = 0.75
    volatility_low_threshold: float = 0.25
    sma_period: int = 50


class MarketRegimeDetector:
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()

    def detect(self, data: OHLCVData) -> MarketRegime:
        if len(data.candles) < max(self.config.adx_period, self.config.atr_period, self.config.sma_period, self.config.volatility_lookback) + 10:
            return MarketRegime.RANGE

        df = self._to_dataframe(data)

        adx_val, plus_di, minus_di = adx(
            df["high"], df["low"], df["close"], self.config.adx_period
        )
        atr_val = atr(df["high"], df["low"], df["close"], self.config.atr_period)
        sma_val = sma(df["close"], self.config.sma_period)

        current_adx = adx_val.iloc[-1] if not pd.isna(adx_val.iloc[-1]) else 0
        current_plus_di = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0
        current_minus_di = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0
        current_atr = atr_val.iloc[-1] if not pd.isna(atr_val.iloc[-1]) else 0
        current_close = df["close"].iloc[-1]
        current_sma = sma_val.iloc[-1] if not pd.isna(sma_val.iloc[-1]) else current_close

        atr_history = atr_val.dropna().values
        if len(atr_history) >= self.config.volatility_lookback:
            atr_percentile = np.percentile(atr_history[-self.config.volatility_lookback:], [self.config.volatility_low_threshold * 100, self.config.volatility_high_threshold * 100])
            atr_low, atr_high = atr_percentile[0], atr_percentile[1]
        else:
            atr_low, atr_high = 0, float('inf')

        is_high_vol = current_atr > atr_high
        is_low_vol = current_atr < atr_low

        is_uptrend = current_adx > self.config.adx_trend_threshold and current_plus_di > current_minus_di and current_close > current_sma
        is_downtrend = current_adx > self.config.adx_trend_threshold and current_minus_di > current_plus_di and current_close < current_sma

        if is_high_vol:
            return MarketRegime.HIGH_VOLATILITY
        elif is_low_vol:
            return MarketRegime.LOW_VOLATILITY
        elif is_uptrend:
            return MarketRegime.BULL_TREND
        elif is_downtrend:
            return MarketRegime.BEAR_TREND
        else:
            return MarketRegime.RANGE

    def detect_with_details(self, data: OHLCVData) -> dict:
        if len(data.candles) < max(self.config.adx_period, self.config.atr_period, self.config.sma_period, self.config.volatility_lookback) + 10:
            return {"regime": MarketRegime.RANGE, "details": "Insufficient data"}

        df = self._to_dataframe(data)

        adx_val, plus_di, minus_di = adx(
            df["high"], df["low"], df["close"], self.config.adx_period
        )
        atr_val = atr(df["high"], df["low"], df["close"], self.config.atr_period)
        sma_val = sma(df["close"], self.config.sma_period)

        current_adx = adx_val.iloc[-1] if not pd.isna(adx_val.iloc[-1]) else 0
        current_plus_di = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0
        current_minus_di = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0
        current_atr = atr_val.iloc[-1] if not pd.isna(atr_val.iloc[-1]) else 0
        current_close = df["close"].iloc[-1]
        current_sma = sma_val.iloc[-1] if not pd.isna(sma_val.iloc[-1]) else current_close

        atr_history = atr_val.dropna().values
        if len(atr_history) >= self.config.volatility_lookback:
            atr_percentile = np.percentile(atr_history[-self.config.volatility_lookback:], [self.config.volatility_low_threshold * 100, self.config.volatility_high_threshold * 100])
            atr_low, atr_high = atr_percentile[0], atr_percentile[1]
        else:
            atr_low, atr_high = 0, float('inf')

        is_high_vol = current_atr > atr_high
        is_low_vol = current_atr < atr_low
        is_uptrend = current_adx > self.config.adx_trend_threshold and current_plus_di > current_minus_di and current_close > current_sma
        is_downtrend = current_adx > self.config.adx_trend_threshold and current_minus_di > current_plus_di and current_close < current_sma

        if is_high_vol:
            regime = MarketRegime.HIGH_VOLATILITY
        elif is_low_vol:
            regime = MarketRegime.LOW_VOLATILITY
        elif is_uptrend:
            regime = MarketRegime.BULL_TREND
        elif is_downtrend:
            regime = MarketRegime.BEAR_TREND
        else:
            regime = MarketRegime.RANGE

        return {
            "regime": regime,
            "adx": float(current_adx),
            "plus_di": float(current_plus_di),
            "minus_di": float(current_minus_di),
            "atr": float(current_atr),
            "atr_low_threshold": float(atr_low),
            "atr_high_threshold": float(atr_high),
            "close": float(current_close),
            "sma": float(current_sma),
            "is_uptrend": is_uptrend,
            "is_downtrend": is_downtrend,
            "is_high_vol": is_high_vol,
            "is_low_vol": is_low_vol,
        }

    def _to_dataframe(self, data: OHLCVData) -> pd.DataFrame:
        return pd.DataFrame([{
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        } for c in data.candles]).set_index("timestamp")