import pandas as pd
import numpy as np
from typing import Optional


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def highest(high: pd.Series, period: int) -> pd.Series:
    return high.rolling(window=period, min_periods=period).max()


def lowest(low: pd.Series, period: int) -> pd.Series:
    return low.rolling(window=period, min_periods=period).min()


def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))


def add_indicators(df: pd.DataFrame, ema_period: int = 20, sma_period: int = 50, vol_period: int = 20) -> pd.DataFrame:
    df = df.copy()
    df['EMA_20'] = ema(df['Close'], ema_period)
    df['SMA_50'] = sma(df['Close'], sma_period)
    df['SMA_50_prev'] = df['SMA_50'].shift(1)
    df['Avg_Vol_20'] = sma(df['Volume'], vol_period)
    df['Volume_Ratio'] = df['Volume'] / df['Avg_Vol_20']
    return df


def find_swing_lows(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    low = df['Low']
    swing_low = pd.Series(False, index=df.index)
    
    for i in range(lookback, len(df) - lookback):
        current_low = low.iloc[i]
        before_lows = low.iloc[i - lookback:i]
        after_lows = low.iloc[i + 1:i + 1 + lookback]
        
        if (current_low < before_lows).all() and (current_low <= after_lows).all():
            swing_low.iloc[i] = True
    
    return swing_low


def get_recent_swing_low(df: pd.DataFrame, lookback: int = 5, max_bars_back: int = 50) -> Optional[float]:
    swing_lows = find_swing_lows(df, lookback)
    swing_low_indices = swing_lows[swing_lows].index
    
    if len(swing_low_indices) == 0:
        return None
    
    last_idx = len(df) - 1
    for idx in reversed(swing_low_indices):
        idx_pos = df.index.get_loc(idx)
        bars_back = last_idx - idx_pos
        
        if bars_back > max_bars_back:
            continue
        
        if idx_pos < len(df) - 1:
            return float(df.loc[idx, 'Low'])
    
    return None