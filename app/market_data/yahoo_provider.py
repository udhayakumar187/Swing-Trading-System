import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.market_data.provider import MarketDataProvider, MarketData, DataValidationError, validate_market_data
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class YahooFinanceMarketDataProvider(MarketDataProvider):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._cache: dict[str, MarketData] = {}
        self._cache_ttl = timedelta(minutes=15)
    
    def get_provider_name(self) -> str:
        return "YahooFinance"
    
    def is_healthy(self) -> bool:
        try:
            ticker = yf.Ticker("RELIANCE.NS")
            hist = ticker.history(period="5d", interval="1d")
            return not hist.empty
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def fetch_historical_data(
        self, 
        symbol: str, 
        period: str = "3mo",
        interval: str = "1d"
    ) -> MarketData:
        cache_key = f"{symbol}_{period}_{interval}"
        
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now() - cached.fetched_at < self._cache_ttl:
                logger.debug(f"Returning cached data for {symbol}")
                return cached
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval, timeout=self.timeout)
            
            if hist.empty:
                raise DataValidationError(f"No data returned for {symbol}")
            
            hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            hist.index = pd.to_datetime(hist.index)
            hist = hist.sort_index()
            
            market_data = MarketData(
                symbol=symbol,
                dataframe=hist,
                fetched_at=datetime.now(),
                source=self.get_provider_name()
            )
            
            is_valid, error = validate_market_data(market_data, min_days=60)
            if not is_valid:
                logger.warning(f"Data validation failed for {symbol}: {error}")
                raise DataValidationError(f"Validation failed for {symbol}: {error}")
            
            self._cache[cache_key] = market_data
            logger.info(f"Fetched {len(hist)} days of data for {symbol}")
            return market_data
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            raise DataValidationError(f"Fetch failed for {symbol}: {e}")
    
    def fetch_multiple_symbols(
        self, 
        symbols: list[str], 
        period: str = "3mo",
        interval: str = "1d"
    ) -> dict[str, MarketData]:
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.fetch_historical_data(symbol, period, interval)
            except DataValidationError as e:
                logger.warning(f"Skipping {symbol}: {e}")
                continue
        return results
    
    def clear_cache(self):
        self._cache.clear()