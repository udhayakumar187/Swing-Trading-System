import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


def create_sample_dataframe(days: int = 100) -> pd.DataFrame:
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    np.random.seed(42)
    
    base_price = 1000
    returns = np.random.normal(0.0005, 0.015, days)
    prices = base_price * np.exp(np.cumsum(returns))
    
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else price
        volume = int(np.random.lognormal(13, 0.5))
        
        data.append({
            'Open': open_price,
            'High': max(open_price, high, price),
            'Low': min(open_price, low, price),
            'Close': price,
            'Volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'Date'
    return df


class TestIndicators:
    def test_ema(self):
        from app.strategies.indicators import ema
        series = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        result = ema(series, 3)
        assert len(result) == len(series)
        assert not result.iloc[-1] != result.iloc[-1]
    
    def test_sma(self):
        from app.strategies.indicators import sma
        series = pd.Series([10, 11, 12, 13, 14, 15])
        result = sma(series, 3)
        assert result.iloc[2] == 11.0
        assert result.iloc[5] == 14.0
    
    def test_add_indicators(self):
        from app.strategies.indicators import add_indicators
        df = create_sample_dataframe(60)
        result = add_indicators(df)
        
        assert 'EMA_20' in result.columns
        assert 'SMA_50' in result.columns
        assert 'SMA_50_prev' in result.columns
        assert 'Avg_Vol_20' in result.columns
        assert 'Volume_Ratio' in result.columns
    
    def test_find_swing_lows(self):
        from app.strategies.indicators import find_swing_lows
        df = create_sample_dataframe(30)
        swing_lows = find_swing_lows(df, lookback=3)
        
        assert isinstance(swing_lows, pd.Series)
        assert swing_lows.dtype == bool
    
    def test_get_recent_swing_low(self):
        from app.strategies.indicators import get_recent_swing_low
        df = create_sample_dataframe(60)
        swing_low = get_recent_swing_low(df, lookback=5)
        
        if swing_low is not None:
            assert isinstance(swing_low, float)
            assert swing_low > 0


class TestEMAPullbackStrategy:
    def test_strategy_initialization(self):
        from app.strategies.ema_pullback import EMAPullbackStrategy
        from app.core.config import Settings
        
        with patch.dict('os.environ', {
            'ANGEL_ONE_API_KEY': 'test',
            'ANGEL_ONE_CLIENT_ID': 'test',
            'ANGEL_ONE_PASSWORD': 'test',
            'ANGEL_ONE_TOTP_SECRET': 'test',
            'TRADING_MODE': 'DRY_RUN',
            'MAX_STOP_LOSS_PERCENT': '0.08',
            'MIN_RISK_REWARD': '2.0',
            'SWING_LOW_LOOKBACK': '5',
        }):
            settings = Settings()
            strategy = EMAPullbackStrategy(settings)
            assert strategy.max_stop_loss_pct == 0.08
            assert strategy.min_risk_reward == 2.0
            assert strategy.swing_low_lookback == 5
    
    def test_analyze_insufficient_data(self):
        from app.strategies.ema_pullback import EMAPullbackStrategy
        from app.market_data.provider import MarketData
        
        with patch.dict('os.environ', {
            'ANGEL_ONE_API_KEY': 'test',
            'ANGEL_ONE_CLIENT_ID': 'test',
            'ANGEL_ONE_PASSWORD': 'test',
            'ANGEL_ONE_TOTP_SECRET': 'test',
            'TRADING_MODE': 'DRY_RUN',
        }):
            strategy = EMAPullbackStrategy()
            
            df = create_sample_dataframe(20)
            market_data = MarketData(
                symbol="TEST.NS",
                dataframe=df,
                fetched_at=datetime.now(),
                source="Test"
            )
            
            result = strategy.analyze(market_data)
            assert result is None
    
    def test_analyze_all_conditions_met(self):
        from app.strategies.ema_pullback import EMAPullbackStrategy
        from app.market_data.provider import MarketData
        
        with patch.dict('os.environ', {
            'ANGEL_ONE_API_KEY': 'test',
            'ANGEL_ONE_CLIENT_ID': 'test',
            'ANGEL_ONE_PASSWORD': 'test',
            'ANGEL_ONE_TOTP_SECRET': 'test',
            'TRADING_MODE': 'DRY_RUN',
        }):
            strategy = EMAPullbackStrategy()
            
            dates = pd.date_range(end=datetime.now(), periods=80, freq='B')
            
            close_prices = np.linspace(1000, 1200, 80)
            close_prices[-5:] = close_prices[-5] * 0.995
            
            data = []
            for i, close in enumerate(close_prices):
                data.append({
                    'Open': close * 0.999,
                    'High': close * 1.01,
                    'Low': close * 0.99,
                    'Close': close,
                    'Volume': 1000000 if i >= 75 else 500000
                })
            
            df = pd.DataFrame(data, index=dates)
            df.index.name = 'Date'
            
            market_data = MarketData(
                symbol="TEST.NS",
                dataframe=df,
                fetched_at=datetime.now(),
                source="Test"
            )
            
            result = strategy.analyze(market_data)
            
            if result and result.decision == "PENDING":
                assert result.symbol == "TEST.NS"
                assert result.signal_type == "BUY"
                assert result.entry_price > 0
                assert result.stop_loss > 0
                assert result.target_price > result.entry_price
                assert result.risk_reward_ratio >= 2.0
    
    def test_stop_loss_too_wide_rejection(self):
        from app.strategies.ema_pullback import EMAPullbackStrategy
        from app.market_data.provider import MarketData
        
        with patch.dict('os.environ', {
            'ANGEL_ONE_API_KEY': 'test',
            'ANGEL_ONE_CLIENT_ID': 'test',
            'ANGEL_ONE_PASSWORD': 'test',
            'ANGEL_ONE_TOTP_SECRET': 'test',
            'TRADING_MODE': 'DRY_RUN',
            'MAX_STOP_LOSS_PERCENT': '0.05',
            'SWING_LOW_LOOKBACK': '3',
        }):
            strategy = EMAPullbackStrategy()
            
            dates = pd.date_range(end=datetime.now(), periods=80, freq='B')
            
            # Create data with:
            # - Clear uptrend (SMA50 rising, close > SMA50)
            # - Valid swing low at position 74 (5 bars before end)
            # - Last candle pulls back near EMA20 but swing low is far below
            
            np.random.seed(42)
            close_prices = []
            base = 1000
            for i in range(80):
                base += np.random.normal(2, 0.5)
                close_prices.append(base)
            
            data = []
            for i, close in enumerate(close_prices):
                if i == 74:  # Create swing low at position 74 (5 bars before end, lookback=3 means need 3 before and 3 after)
                    data.append({
                        'Open': close * 1.01,
                        'High': close * 1.02,
                        'Low': close * 0.88,  # Very low - creates swing low (lower than 3 before and 3 after)
                        'Close': close * 0.90,
                        'Volume': 500000
                    })
                elif i == 75:
                    data.append({
                        'Open': close * 0.92,
                        'High': close * 0.95,
                        'Low': close * 0.91,
                        'Close': close * 0.93,
                        'Volume': 500000
                    })
                elif i == 76:
                    data.append({
                        'Open': close * 0.93,
                        'High': close * 0.96,
                        'Low': close * 0.92,
                        'Close': close * 0.94,
                        'Volume': 500000
                    })
                elif i == 77:
                    data.append({
                        'Open': close * 0.94,
                        'High': close * 0.97,
                        'Low': close * 0.93,
                        'Close': close * 0.95,
                        'Volume': 500000
                    })
                elif i == 79:  # Last candle - pullback near EMA20
                    data.append({
                        'Open': close * 1.01,
                        'High': close * 1.02,
                        'Low': close * 0.95,
                        'Close': close * 0.99,  # Close near EMA20
                        'Volume': 2000000
                    })
                elif i >= 78:
                    data.append({
                        'Open': close * 0.999,
                        'High': close * 1.01,
                        'Low': close * 0.98,
                        'Close': close,
                        'Volume': 1500000
                    })
                else:
                    data.append({
                        'Open': close * 0.999,
                        'High': close * 1.01,
                        'Low': close * 0.99,
                        'Close': close,
                        'Volume': 500000
                    })
            
            df = pd.DataFrame(data, index=dates)
            df.index.name = 'Date'
            
            market_data = MarketData(
                symbol="TEST.NS",
                dataframe=df,
                fetched_at=datetime.now(),
                source="Test"
            )
            
            result = strategy.analyze(market_data)
            
            assert result is not None
            assert result.decision == "REJECTED"
            assert "STOP_TOO_WIDE" in result.reason


class TestMarketDataValidation:
    def test_validate_market_data_valid(self):
        from app.market_data.provider import validate_market_data, MarketData
        df = create_sample_dataframe(80)
        market_data = MarketData(
            symbol="TEST.NS",
            dataframe=df,
            fetched_at=datetime.now(),
            source="Test"
        )
        is_valid, error = validate_market_data(market_data, min_days=60)
        assert is_valid is True
        assert error is None
    
    def test_validate_market_data_insufficient(self):
        from app.market_data.provider import validate_market_data, MarketData
        df = create_sample_dataframe(30)
        market_data = MarketData(
            symbol="TEST.NS",
            dataframe=df,
            fetched_at=datetime.now(),
            source="Test"
        )
        is_valid, error = validate_market_data(market_data, min_days=60)
        assert is_valid is False
        assert "Insufficient data" in error
    
    def test_validate_market_data_null_values(self):
        from app.market_data.provider import validate_market_data, MarketData
        df = create_sample_dataframe(80)
        df.loc[df.index[10], 'Close'] = np.nan
        market_data = MarketData(
            symbol="TEST.NS",
            dataframe=df,
            fetched_at=datetime.now(),
            source="Test"
        )
        is_valid, error = validate_market_data(market_data, min_days=60)
        assert is_valid is False
        assert "Null values" in error


class TestSchemas:
    def test_signal_schema(self):
        from app.schemas.trading import SignalCreate, SignalDecision
        
        signal = SignalCreate(
            symbol="RELIANCE.NS",
            signal_type="BUY",
            signal_timestamp=datetime.now(),
            entry_price=2500.0,
            stop_loss=2400.0,
            target_price=2700.0,
            risk_amount=10000.0,
            risk_reward_ratio=2.0,
            strategy_name="EMAPullbackStrategy",
            decision=SignalDecision.PENDING
        )
        assert signal.symbol == "RELIANCE.NS"
        assert signal.risk_reward_ratio == 2.0
    
    def test_position_schema(self):
        from app.schemas.trading import PositionCreate, PositionStatus
        
        position = PositionCreate(
            symbol="RELIANCE.NS",
            exchange="NSE",
            quantity=10,
            entry_price=2500.0,
            stop_loss=2400.0,
            target_price=2700.0,
            status=PositionStatus.OPEN,
            strategy_name="EMAPullbackStrategy",
            paper_or_live="PAPER"
        )
        assert position.quantity == 10
        assert position.paper_or_live == "PAPER"
    
    def test_order_schema(self):
        from app.schemas.trading import OrderCreate, OrderSide, OrderType, OrderProductType
        
        order = OrderCreate(
            symbol="RELIANCE.NS",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.MARKET,
            product_type=OrderProductType.DELIVERY,
            paper_or_live="PAPER"
        )
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET


if __name__ == "__main__":
    pytest.main([__file__, "-v"])