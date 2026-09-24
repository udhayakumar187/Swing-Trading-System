import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class IndicatorConfig:
    sma_period: int = 20
    ema_period: int = 20
    wma_period: int = 20
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_smooth: int = 3
    atr_period: int = 14
    adx_period: int = 14


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1)
    return series.rolling(window=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
    smooth: int = 3
) -> Tuple[pd.Series, pd.Series]:
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    k_raw = 100 * (close - lowest_low) / (highest_high - lowest_low)
    k = k_raw.rolling(window=smooth, min_periods=smooth).mean()
    d = k.rolling(window=d_period, min_periods=d_period).mean()
    return k, d


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    plus_dm = high.diff()
    minus_dm = low.diff().mul(-1)

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_val = tr.rolling(window=period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period, min_periods=period).mean() / atr_val)
    minus_di = 100 * (minus_dm.rolling(window=period, min_periods=period).mean() / atr_val)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_val = dx.rolling(window=period, min_periods=period).mean()

    return adx_val, plus_di, minus_di


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def pivot_points(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series
) -> Dict[str, pd.Series]:
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)
    return {
        "PP": pp, "R1": r1, "S1": s1,
        "R2": r2, "S2": s2, "R3": r3, "S3": s3
    }


def donchian_channel(
    high: pd.Series,
    low: pd.Series,
    period: int = 20
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    upper = high.rolling(window=period, min_periods=period).max()
    lower = low.rolling(window=period, min_periods=period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower


def keltner_channel(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20,
    atr_mult: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    middle = ema(close, period)
    atr_val = atr(high, low, close, period)
    upper = middle + atr_mult * atr_val
    lower = middle - atr_mult * atr_val
    return upper, middle, lower


def ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b: int = 52
) -> Dict[str, pd.Series]:
    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_b = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2).shift(kijun)
    chikou = close.shift(-kijun)
    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_a,
        "senkou_span_b": senkou_b,
        "chikou_span": chikou,
    }


def add_all_indicators(
    df: pd.DataFrame,
    config: Optional[IndicatorConfig] = None
) -> pd.DataFrame:
    cfg = config or IndicatorConfig()
    df = df.copy()

    df[f"SMA_{cfg.sma_period}"] = sma(df["close"], cfg.sma_period)
    df[f"EMA_{cfg.ema_period}"] = ema(df["close"], cfg.ema_period)
    df[f"WMA_{cfg.wma_period}"] = wma(df["close"], cfg.wma_period)

    df[f"RSI_{cfg.rsi_period}"] = rsi(df["close"], cfg.rsi_period)

    macd_line, signal_line, histogram = macd(
        df["close"], cfg.macd_fast, cfg.macd_slow, cfg.macd_signal
    )
    df[f"MACD_{cfg.macd_fast}_{cfg.macd_slow}_{cfg.macd_signal}"] = macd_line
    df[f"MACD_SIGNAL_{cfg.macd_fast}_{cfg.macd_slow}_{cfg.macd_signal}"] = signal_line
    df[f"MACD_HIST_{cfg.macd_fast}_{cfg.macd_slow}_{cfg.macd_signal}"] = histogram

    bb_upper, bb_middle, bb_lower = bollinger_bands(df["close"], cfg.bb_period, cfg.bb_std)
    df[f"BB_UPPER_{cfg.bb_period}_{cfg.bb_std}"] = bb_upper
    df[f"BB_MIDDLE_{cfg.bb_period}_{cfg.bb_std}"] = bb_middle
    df[f"BB_LOWER_{cfg.bb_period}_{cfg.bb_std}"] = bb_lower
    df[f"BB_WIDTH_{cfg.bb_period}_{cfg.bb_std}"] = (bb_upper - bb_lower) / bb_middle

    stoch_k, stoch_d = stochastic(
        df["high"], df["low"], df["close"],
        cfg.stoch_k, cfg.stoch_d, cfg.stoch_smooth
    )
    df[f"STOCH_K_{cfg.stoch_k}_{cfg.stoch_d}_{cfg.stoch_smooth}"] = stoch_k
    df[f"STOCH_D_{cfg.stoch_k}_{cfg.stoch_d}_{cfg.stoch_smooth}"] = stoch_d

    df[f"ATR_{cfg.atr_period}"] = atr(df["high"], df["low"], df["close"], cfg.atr_period)

    adx_val, plus_di, minus_di = adx(df["high"], df["low"], df["close"], cfg.adx_period)
    df[f"ADX_{cfg.adx_period}"] = adx_val
    df[f"PLUS_DI_{cfg.adx_period}"] = plus_di
    df[f"MINUS_DI_{cfg.adx_period}"] = minus_di

    df["OBV"] = obv(df["close"], df["volume"])
    df["VWAP"] = vwap(df["high"], df["low"], df["close"], df["volume"])

    return df


def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))