import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from datetime import datetime

from app.patterns.models.core import Candle, OHLCVData
from app.patterns.models.enums import Timeframe


class DataValidationError(Exception):
    def __init__(self, message: str, errors: List[str]):
        super().__init__(message)
        self.errors = errors


def validate_ohlcv_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    errors = []

    required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return False, errors

    if df.empty:
        errors.append("DataFrame is empty")
        return False, errors

    if df[["open", "high", "low", "close"]].isnull().any().any():
        errors.append("OHLC columns contain null values")
        return False, errors

    if (df["high"] < df[["open", "close"]].max(axis=1)).any():
        errors.append("High is less than max(open, close) in some rows")

    if (df["low"] > df[["open", "close"]].min(axis=1)).any():
        errors.append("Low is greater than min(open, close) in some rows")

    if (df["volume"] < 0).any():
        errors.append("Volume contains negative values")

    if not df["timestamp"].is_monotonic_increasing:
        errors.append("Timestamps are not chronologically ordered")

    if df["timestamp"].duplicated().any():
        errors.append("Duplicate timestamps found")

    return len(errors) == 0, errors


def dataframe_to_ohlcv(
    df: pd.DataFrame,
    symbol: str,
    timeframe: Timeframe,
) -> OHLCVData:
    valid, errors = validate_ohlcv_dataframe(df)
    if not valid:
        raise DataValidationError("OHLCV validation failed", errors)

    candles = [
        Candle(
            timestamp=row["timestamp"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
        for _, row in df.iterrows()
    ]

    return OHLCVData(symbol=symbol, timeframe=timeframe, candles=candles)


def ohlcv_to_dataframe(data: OHLCVData) -> pd.DataFrame:
    return pd.DataFrame([c.model_dump() for c in data.candles])


def ensure_sufficient_candles(data: OHLCVData, required: int) -> bool:
    return len(data.candles) >= required


def get_live_candles(data: OHLCVData, lookback: int) -> OHLCVData:
    if len(data.candles) <= lookback:
        return data
    return OHLCVData(
        symbol=data.symbol,
        timeframe=data.timeframe,
        candles=data.candles[-lookback:],
    )