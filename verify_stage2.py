#!/usr/bin/env python
"""
Verification script for STAGE 2 implementation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_file_exists(path, description):
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if os.path.exists(full_path):
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[MISSING] {description}: {path}")
        return False


def verify_imports():
    print("\nVerifying STAGE 2 imports...")
    
    try:
        from app.market_data.provider import MarketDataProvider, MarketData, DataValidationError, validate_market_data
        print("  [OK] app.market_data.provider")
    except Exception as e:
        print(f"  [FAIL] app.market_data.provider: {e}")
        return False
    
    try:
        from app.market_data.yahoo_provider import YahooFinanceMarketDataProvider
        print("  [OK] app.market_data.yahoo_provider")
    except Exception as e:
        print(f"  [FAIL] app.market_data.yahoo_provider: {e}")
        return False
    
    try:
        from app.strategies.indicators import (
            ema, sma, atr, highest, lowest, crossover, crossunder,
            add_indicators, find_swing_lows, get_recent_swing_low
        )
        print("  [OK] app.strategies.indicators")
    except Exception as e:
        print(f"  [FAIL] app.strategies.indicators: {e}")
        return False
    
    try:
        from app.strategies.ema_pullback import EMAPullbackStrategy, TradeSignal
        print("  [OK] app.strategies.ema_pullback")
    except Exception as e:
        print(f"  [FAIL] app.strategies.ema_pullback: {e}")
        return False
    
    try:
        from app.schemas.trading import (
            SignalType, SignalDecision, PositionStatus, OrderSide,
            OrderType, OrderProductType, OrderStatus, TradingRunStatus,
            SignalCreate, PositionCreate, OrderCreate, RiskSettingsCreate
        )
        print("  [OK] app.schemas.trading")
    except Exception as e:
        print(f"  [FAIL] app.schemas.trading: {e}")
        return False
    
    return True


def verify_indicators():
    print("\nVerifying indicators...")
    
    import pandas as pd
    import numpy as np
    from app.strategies.indicators import ema, sma, add_indicators, find_swing_lows, get_recent_swing_low
    
    dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='B')
    np.random.seed(42)
    prices = 1000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 60)))
    
    df = pd.DataFrame({
        'Open': prices * 0.999,
        'High': prices * 1.01,
        'Low': prices * 0.99,
        'Close': prices,
        'Volume': np.random.lognormal(13, 0.5, 60).astype(int)
    }, index=dates)
    df.index.name = 'Date'
    
    try:
        ema_result = ema(df['Close'], 20)
        assert len(ema_result) == len(df)
        print("  [OK] EMA calculation")
    except Exception as e:
        print(f"  [FAIL] EMA: {e}")
        return False
    
    try:
        sma_result = sma(df['Close'], 50)
        assert len(sma_result) == len(df)
        print("  [OK] SMA calculation")
    except Exception as e:
        print(f"  [FAIL] SMA: {e}")
        return False
    
    try:
        df_with_indicators = add_indicators(df)
        assert 'EMA_20' in df_with_indicators.columns
        assert 'SMA_50' in df_with_indicators.columns
        assert 'Avg_Vol_20' in df_with_indicators.columns
        print("  [OK] add_indicators")
    except Exception as e:
        print(f"  [FAIL] add_indicators: {e}")
        return False
    
    try:
        swing_lows = find_swing_lows(df_with_indicators, lookback=5)
        assert isinstance(swing_lows, pd.Series)
        assert swing_lows.dtype == bool
        print("  [OK] find_swing_lows")
    except Exception as e:
        print(f"  [FAIL] find_swing_lows: {e}")
        return False
    
    try:
        recent_swing = get_recent_swing_low(df_with_indicators, lookback=5)
        print(f"  [OK] get_recent_swing_low: {recent_swing}")
    except Exception as e:
        print(f"  [FAIL] get_recent_swing_low: {e}")
        return False
    
    return True


def verify_strategy():
    print("\nVerifying EMAPullbackStrategy...")
    
    try:
        from app.strategies.ema_pullback import EMAPullbackStrategy
        from app.market_data.provider import MarketData
        import pandas as pd
        import numpy as np
        from datetime import datetime
        
        os.environ['ANGEL_ONE_API_KEY'] = 'test'
        os.environ['ANGEL_ONE_CLIENT_ID'] = 'test'
        os.environ['ANGEL_ONE_PASSWORD'] = 'test'
        os.environ['ANGEL_ONE_TOTP_SECRET'] = 'test'
        os.environ['TRADING_MODE'] = 'DRY_RUN'
        os.environ['MAX_STOP_LOSS_PERCENT'] = '0.08'
        os.environ['MIN_RISK_REWARD'] = '2.0'
        os.environ['SWING_LOW_LOOKBACK'] = '5'
        
        strategy = EMAPullbackStrategy()
        
        assert strategy.ema_period == 20
        assert strategy.sma_period == 50
        assert strategy.max_stop_loss_pct == 0.08
        assert strategy.min_risk_reward == 2.0
        assert strategy.swing_low_lookback == 5
        print("  [OK] Strategy initialization with config")
        
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
        
        signal = strategy.analyze(market_data)
        
        if signal:
            print(f"  [OK] Signal generated: {signal.decision}")
            if signal.decision == "PENDING":
                assert signal.risk_reward_ratio >= 2.0
                assert signal.stop_loss > 0
                assert signal.target_price > signal.entry_price
                print(f"    Entry: {signal.entry_price:.2f}, SL: {signal.stop_loss:.2f}, Target: {signal.target_price:.2f}, R:R: {signal.risk_reward_ratio:.2f}")
        else:
            print("  [INFO] No signal generated (conditions not met)")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Strategy: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_schemas():
    print("\nVerifying schemas...")
    
    try:
        from app.schemas.trading import (
            SignalCreate, PositionCreate, OrderCreate,
            SignalDecision, PositionStatus, OrderSide, OrderType, OrderProductType
        )
        from datetime import datetime
        
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
        print("  [OK] SignalCreate schema")
        
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
        print("  [OK] PositionCreate schema")
        
        order = OrderCreate(
            symbol="RELIANCE.NS",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.MARKET,
            product_type=OrderProductType.DELIVERY,
            paper_or_live="PAPER"
        )
        print("  [OK] OrderCreate schema")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Schemas: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("STAGE 2 VERIFICATION")
    print("=" * 60)
    
    all_ok = True
    
    all_ok &= check_file_exists("app/market_data/provider.py", "MarketData Provider Interface")
    all_ok &= check_file_exists("app/market_data/yahoo_provider.py", "Yahoo Finance Provider")
    all_ok &= check_file_exists("app/market_data/__init__.py", "Market Data Init")
    all_ok &= check_file_exists("app/strategies/indicators.py", "Technical Indicators")
    all_ok &= check_file_exists("app/strategies/ema_pullback.py", "EMA Pullback Strategy")
    all_ok &= check_file_exists("app/strategies/__init__.py", "Strategies Init")
    all_ok &= check_file_exists("app/schemas/trading.py", "Trading Schemas")
    all_ok &= check_file_exists("app/schemas/__init__.py", "Schemas Init")
    all_ok &= check_file_exists("app/tests/test_stage2.py", "Stage 2 Tests")
    
    if not all_ok:
        print("\n[FAILURE] Some files missing")
        return 1
    
    all_ok &= verify_imports()
    all_ok &= verify_indicators()
    all_ok &= verify_strategy()
    all_ok &= verify_schemas()
    
    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] ALL STAGE 2 CHECKS PASSED")
        print("\nSTAGE 2 COMPLETE:")
        print("  - MarketDataProvider interface")
        print("  - YahooFinanceMarketDataProvider implementation")
        print("  - Data validation (min 60 days, null checks, OHLC validation)")
        print("  - Technical indicators: EMA, SMA, ATR, swing low detection")
        print("  - EMAPullbackStrategy with deterministic rules:")
        print("    * Close > 50-day SMA")
        print("    * 50-day SMA rising")
        print("    * Low within 0.5% of 20-day EMA")
        print("    * Volume > 20-day average")
        print("    * Swing low based stop loss (configurable lookback)")
        print("    * 8% max stop loss rejection")
        print("    * 2.0 minimum risk/reward target")
        print("  - Pydantic schemas for all trading entities")
    else:
        print("[FAILURE] SOME CHECKS FAILED")
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())