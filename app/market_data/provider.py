from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pandas as pd


@dataclass
class MarketData:
    symbol: str
    dataframe: pd.DataFrame
    fetched_at: datetime
    source: str
    
    def __post_init__(self):
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            if col not in self.dataframe.columns:
                raise ValueError(f"Missing required column: {col}")
        
        if self.dataframe.empty:
            raise ValueError("Dataframe is empty")
        
        if not isinstance(self.dataframe.index, pd.DatetimeIndex):
            raise ValueError("Dataframe index must be DatetimeIndex")


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_historical_data(
        self, 
        symbol: str, 
        period: str = "3mo",
        interval: str = "1d"
    ) -> MarketData:
        pass
    
    @abstractmethod
    def fetch_multiple_symbols(
        self, 
        symbols: list[str], 
        period: str = "3mo",
        interval: str = "1d"
    ) -> dict[str, MarketData]:
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class DataValidationError(Exception):
    pass


def validate_market_data(data: MarketData, min_days: int = 60) -> tuple[bool, Optional[str]]:
    df = data.dataframe
    
    if len(df) < min_days:
        return False, f"Insufficient data: {len(df)} days < {min_days} required"
    
    if df.isnull().any().any():
        null_cols = df.columns[df.isnull().any()].tolist()
        return False, f"Null values in columns: {null_cols}"
    
    if (df['Close'] <= 0).any():
        return False, "Invalid close prices (<= 0)"
    
    if (df['Volume'] < 0).any():
        return False, "Negative volume values"
    
    if (df['High'] < df['Low']).any():
        return False, "High < Low detected"
    
    if (df['Open'] > df['High']).any() or (df['Open'] < df['Low']).any():
        return False, "Open outside High-Low range"
    
    if (df['Close'] > df['High']).any() or (df['Close'] < df['Low']).any():
        return False, "Close outside High-Low range"
    
    if not df.index.is_monotonic_increasing:
        return False, "Index not monotonic increasing"
    
    return True, None