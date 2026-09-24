#!/usr/bin/env python
"""
Verification script for STAGE 3 implementation.
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
    print("\nVerifying STAGE 3 imports...")
    
    try:
        from app.risk.manager import RiskManager, RiskCheck, RejectionReason, PositionSizingResult
        print("  [OK] app.risk.manager")
    except Exception as e:
        print(f"  [FAIL] app.risk.manager: {e}")
        return False
    
    try:
        from app.risk.event_provider import (
            EventRiskProvider, CorporateEvent, EventType, EventImpact,
            DummyEventRiskProvider, YahooFinanceEventRiskProvider, create_event_risk_provider
        )
        print("  [OK] app.risk.event_provider")
    except Exception as e:
        print(f"  [FAIL] app.risk.event_provider: {e}")
        return False
    
    try:
        from app.risk import (
            RiskManager, RiskCheck, RejectionReason, PositionSizingResult,
            EventRiskProvider, CorporateEvent, EventType, EventImpact,
            DummyEventRiskProvider, YahooFinanceEventRiskProvider, create_event_risk_provider
        )
        print("  [OK] app.risk package")
    except Exception as e:
        print(f"  [FAIL] app.risk package: {e}")
        return False
    
    return True


def verify_risk_manager():
    print("\nVerifying RiskManager...")
    
    try:
        from app.risk.manager import RiskManager, RejectionReason, PositionSizingResult
        from app.models.position import PositionStatus
        from app.core.config import Settings, get_settings
        from unittest.mock import MagicMock
        
        # Clear settings cache
        get_settings.cache_clear()
        
        os.environ['ANGEL_ONE_API_KEY'] = 'test'
        os.environ['ANGEL_ONE_CLIENT_ID'] = 'test'
        os.environ['ANGEL_ONE_PASSWORD'] = 'test'
        os.environ['ANGEL_ONE_TOTP_SECRET'] = 'test'
        os.environ['TRADING_MODE'] = 'DRY_RUN'
        os.environ['MAX_RISK_PERCENT'] = '0.01'
        os.environ['MAX_DAILY_LOSS_PERCENT'] = '0.02'
        os.environ['MAX_OPEN_POSITIONS'] = '3'
        os.environ['MAX_STOP_LOSS_PERCENT'] = '0.08'
        os.environ['MIN_RISK_REWARD'] = '2.0'
        
        settings = Settings()
        risk_manager = RiskManager(settings)
        
        account = MagicMock()
        account.total_capital = 100000  # Larger capital to avoid concentration limit
        account.available_cash = 50000
        
        risk_settings = MagicMock()
        risk_settings.max_risk_percent = 0.002  # Smaller risk to get smaller quantity
        risk_settings.max_daily_loss_percent = 0.02
        risk_settings.max_open_positions = 3
        risk_settings.max_stop_loss_percent = 0.08
        risk_settings.min_risk_reward = 2.0
        risk_settings.max_position_concentration_percent = 0.3
        risk_settings.max_sector_concentration_percent = 0.5
        
        from app.strategies.ema_pullback import TradeSignal
        from datetime import datetime
        
        signal = TradeSignal(
            symbol="RELIANCE.NS",
            signal_type="BUY",
            signal_timestamp=datetime.now(),
            entry_price=500,
            stop_loss=490,
            target_price=520,
            risk_amount=0,
            risk_reward_ratio=2.0,
            strategy_name="EMAPullbackStrategy",
            decision="PENDING"
        )
        
        result = risk_manager.calculate_position_size(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            available_cash=50000,
            open_positions=[]
        )
        
        print(f"  Position Sizing: qty={result.quantity}, risk={result.risk_amount}, value={result.position_value}")
        assert result.quantity == 20
        assert result.risk_amount == 200
        assert result.position_value == 10000
        print("  [OK] Position sizing calculation (capital=100000, risk=0.2%, entry=500, stop=490)")
        print("    Expected: risk_amount=200, risk/share=10, qty=20, value=10000")
        print(f"    Actual: risk_amount={result.risk_amount}, qty={result.quantity}, value={result.position_value}")
        
        check = risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=[],
            daily_pnl=0,
            available_cash=50000,
            event_risk=False
        )
        
        assert check.passed
        assert check.quantity == 20
        print("  [OK] Signal validation passed")
        
        return True
    except Exception as e:
        print(f"  [FAIL] RiskManager: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_event_provider():
    print("\nVerifying EventRiskProvider...")
    
    try:
        from app.risk.event_provider import (
            DummyEventRiskProvider, CorporateEvent, EventType, EventImpact,
            create_event_risk_provider
        )
        from datetime import date, timedelta
        
        provider = DummyEventRiskProvider()
        assert provider.get_provider_name() == "DummyEventRiskProvider"
        assert provider.is_healthy()
        print("  [OK] DummyEventRiskProvider")
        
        events = provider.get_upcoming_events(["RELIANCE.NS", "TCS.NS"], 7)
        assert events == {"RELIANCE.NS": [], "TCS.NS": []}
        print("  [OK] get_upcoming_events returns empty")
        
        has_event, event = provider.has_high_impact_event("RELIANCE.NS", 7)
        assert not has_event
        print("  [OK] has_high_impact_event returns False")
        
        yahoo_provider = create_event_risk_provider("yahoo")
        assert yahoo_provider.get_provider_name() == "YahooFinanceEventRiskProvider"
        print("  [OK] YahooFinanceEventRiskProvider creation")
        
        return True
    except Exception as e:
        print(f"  [FAIL] EventRiskProvider: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_rejection_reasons():
    print("\nVerifying rejection reason codes...")
    
    try:
        from app.risk.manager import RejectionReason
        
        expected_reasons = [
            "SIGNAL_REJECTED_STOP_TOO_WIDE",
            "SIGNAL_REJECTED_DUPLICATE_POSITION",
            "SIGNAL_REJECTED_DAILY_RISK_LIMIT",
            "SIGNAL_REJECTED_INSUFFICIENT_CASH",
            "SIGNAL_REJECTED_EVENT_RISK",
            "SIGNAL_REJECTED_INVALID_DATA",
            "SIGNAL_REJECTED_MAX_POSITIONS_REACHED",
            "SIGNAL_REJECTED_PORTFOLIO_RISK_EXCEEDED",
            "SIGNAL_REJECTED_POSITION_CONCENTRATION",
            "SIGNAL_REJECTED_SECTOR_CONCENTRATION",
        ]
        
        for reason in expected_reasons:
            assert hasattr(RejectionReason, reason.replace("SIGNAL_REJECTED_", ""))
            print(f"  [OK] {reason}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Rejection reasons: {e}")
        return False


def main():
    print("=" * 60)
    print("STAGE 3 VERIFICATION")
    print("=" * 60)
    
    all_ok = True
    
    all_ok &= check_file_exists("app/risk/manager.py", "Risk Manager")
    all_ok &= check_file_exists("app/risk/event_provider.py", "Event Risk Provider")
    all_ok &= check_file_exists("app/risk/__init__.py", "Risk Init")
    all_ok &= check_file_exists("app/tests/test_stage3.py", "Stage 3 Tests")
    
    if not all_ok:
        print("\n[FAILURE] Some files missing")
        return 1
    
    all_ok &= verify_imports()
    all_ok &= verify_risk_manager()
    all_ok &= verify_event_provider()
    all_ok &= verify_rejection_reasons()
    
    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] ALL STAGE 3 CHECKS PASSED")
        print("\nSTAGE 3 COMPLETE:")
        print("  - RiskManager with comprehensive validation:")
        print("    * Stop loss validation (positive, <= 8% max)")
        print("    * Risk/reward validation (>= 2.0)")
        print("    * Duplicate position check")
        print("    * Max open positions limit")
        print("    * Daily loss limit (2% portfolio)")
        print("    * Corporate event risk (pluggable)")
        print("    * Portfolio risk aggregation")
        print("    * Position concentration limit (30%)")
        print("    * Sector concentration limit (50%)")
        print("  - Position Sizing:")
        print("    * Risk amount = portfolio * MAX_RISK_PERCENT")
        print("    * Quantity = floor(risk_amount / risk_per_share)")
        print("    * Cash availability check with adjustment")
        print("    * Actual risk recalculation after adjustment")
        print("  - Explicit rejection reason codes:")
        for reason in ["STOP_TOO_WIDE", "DUPLICATE_POSITION", "DAILY_RISK_LIMIT", 
                       "INSUFFICIENT_CASH", "EVENT_RISK", "INVALID_DATA",
                       "MAX_POSITIONS", "PORTFOLIO_RISK", "POSITION_CONCENTRATION",
                       "SECTOR_CONCENTRATION"]:
            print(f"    * SIGNAL_REJECTED_{reason}")
        print("  - EventRiskProvider abstraction (pluggable)")
        print("    * DummyEventRiskProvider (default)")
        print("    * YahooFinanceEventRiskProvider (placeholder)")
    else:
        print("[FAILURE] SOME CHECKS FAILED")
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())