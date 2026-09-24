import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

from app.strategies.ema_pullback import TradeSignal
from app.models.position import Position, PositionStatus
from app.models.account import Account
from app.models.risk_settings import RiskSettings
from app.risk.manager import RiskManager, RejectionReason, PositionSizingResult
from app.risk.event_provider import (
    EventRiskProvider, CorporateEvent, EventType, EventImpact,
    DummyEventRiskProvider, YahooFinanceEventRiskProvider, create_event_risk_provider
)
from app.core.config import get_settings



class TestRiskManager:
    def setup_method(self):
        with patch.dict('os.environ', {
            'ANGEL_ONE_API_KEY': 'test',
            'ANGEL_ONE_CLIENT_ID': 'test',
            'ANGEL_ONE_PASSWORD': 'test',
            'ANGEL_ONE_TOTP_SECRET': 'test',
            'TRADING_MODE': 'DRY_RUN',
            'MAX_RISK_PERCENT': '0.01',
            'MAX_DAILY_LOSS_PERCENT': '0.02',
            'MAX_OPEN_POSITIONS': '3',
            'MAX_STOP_LOSS_PERCENT': '0.08',
            'MIN_RISK_REWARD': '2.0',
            'SWING_LOW_LOOKBACK': '5',
        }):
            self.settings = get_settings()
            self.risk_manager = RiskManager(self.settings)
    
    def teardown_method(self):
        get_settings.cache_clear()
    
    def create_account(self, total_capital=100000, available_cash=50000):
        account = MagicMock(spec=Account)
        account.total_capital = total_capital
        account.available_cash = available_cash
        return account
    
    def create_risk_settings(self):
        settings = MagicMock(spec=RiskSettings)
        settings.max_risk_percent = 0.01
        settings.max_daily_loss_percent = 0.02
        settings.max_open_positions = 3
        settings.max_stop_loss_percent = 0.08
        settings.min_risk_reward = 2.0
        settings.max_position_concentration_percent = 0.3
        settings.max_sector_concentration_percent = 0.5
        return settings
    
    def create_signal(self, entry=500, stop=490, target=520, symbol="RELIANCE.NS"):
        signal = TradeSignal(
            symbol=symbol,
            signal_type="BUY",
            signal_timestamp=datetime.now(),
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            risk_amount=0,
            risk_reward_ratio=(target - entry) / (entry - stop),
            strategy_name="EMAPullbackStrategy",
            decision="PENDING",
            reason=None
        )
        return signal
    
    def test_position_sizing_basic(self):
        
        
        account = self.create_account(total_capital=10000, available_cash=10000)
        risk_settings = self.create_risk_settings()
        signal = self.create_signal(entry=500, stop=490, target=520)
        
        result = self.risk_manager.calculate_position_size(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            available_cash=10000,
            open_positions=[]
        )
        
        assert result.quantity == 10
        assert result.risk_amount == 100
        assert result.position_value == 5000
        assert result.actual_risk_pct == 0.01
        assert not result.adjusted
    
    def test_position_sizing_insufficient_cash(self):
        
        
        account = self.create_account(total_capital=10000, available_cash=3000)
        risk_settings = self.create_risk_settings()
        signal = self.create_signal(entry=500, stop=490, target=520)
        
        result = self.risk_manager.calculate_position_size(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            available_cash=3000,
            open_positions=[]
        )
        
        assert result.quantity == 6
        assert result.position_value == 3000
        assert result.adjusted
        assert "cash" in result.adjustment_reason.lower()
    
    def test_position_sizing_quantity_zero(self):
        
        
        account = self.create_account(total_capital=10000, available_cash=100)
        risk_settings = self.create_risk_settings()
        signal = self.create_signal(entry=500, stop=490, target=520)
        
        result = self.risk_manager.calculate_position_size(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            available_cash=100,
            open_positions=[]
        )
        
        assert result.quantity == 0
    
    def test_validate_signal_passed(self):
        
        
        account = self.create_account(total_capital=100000, available_cash=50000)
        risk_settings = self.create_risk_settings()
        risk_settings.max_risk_percent = 0.002  # Smaller risk to get smaller quantity
        signal = self.create_signal(entry=500, stop=490, target=520)
        
        check = self.risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=[],
            daily_pnl=0,
            available_cash=50000,
            event_risk=False
        )
        
        assert check.passed
        assert check.quantity > 0
        assert check.risk_amount > 0
    
    def test_validate_signal_duplicate_position(self):
        
        
        account = self.create_account()
        risk_settings = self.create_risk_settings()
        signal = self.create_signal(symbol="RELIANCE.NS")
        
        existing_pos = MagicMock(spec=Position)
        existing_pos.symbol = "RELIANCE.NS"
        existing_pos.status = PositionStatus.OPEN
        
        check = self.risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=[existing_pos],
            daily_pnl=0,
            available_cash=50000,
            event_risk=False
        )
        
        assert not check.passed
        assert check.reason == RejectionReason.DUPLICATE_POSITION
    
    def test_validate_signal_max_positions(self):
        
        
        account = self.create_account()
        risk_settings = self.create_risk_settings()
        signal = self.create_signal(symbol="TCS.NS")
        
        positions = []
        for i in range(3):
            pos = MagicMock(spec=Position)
            pos.symbol = f"STOCK{i}.NS"
            pos.status = PositionStatus.OPEN
            positions.append(pos)
        
        check = self.risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=positions,
            daily_pnl=0,
            available_cash=50000,
            event_risk=False
        )
        
        assert not check.passed
        assert check.reason == RejectionReason.MAX_POSITIONS_REACHED
    
    def test_validate_signal_daily_loss_limit(self):
        
        
        account = self.create_account(total_capital=100000)
        risk_settings = self.create_risk_settings()
        signal = self.create_signal()
        
        check = self.risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=[],
            daily_pnl=-2500,
            available_cash=50000,
            event_risk=False
        )
        
        assert not check.passed
        assert check.reason == RejectionReason.DAILY_RISK_LIMIT
    
    def test_validate_signal_stop_too_wide(self):
        
        
        account = self.create_account()
        risk_settings = self.create_risk_settings()
        signal = self.create_signal(entry=500, stop=450, target=550)
        
        check = self.risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=[],
            daily_pnl=0,
            available_cash=50000,
            event_risk=False
        )
        
        assert not check.passed
        assert check.reason == RejectionReason.STOP_TOO_WIDE
    
    def test_validate_signal_event_risk(self):
        
        
        account = self.create_account()
        risk_settings = self.create_risk_settings()
        signal = self.create_signal()
        
        check = self.risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=[],
            daily_pnl=0,
            available_cash=50000,
            event_risk=True
        )
        
        assert not check.passed
        assert check.reason == RejectionReason.EVENT_RISK
    
    def test_validate_signal_invalid_stop_loss(self):
        
        
        account = self.create_account()
        risk_settings = self.create_risk_settings()
        signal = self.create_signal(entry=500, stop=510)
        
        check = self.risk_manager.validate_signal(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            open_positions=[],
            daily_pnl=0,
            available_cash=50000,
            event_risk=False
        )
        
        assert not check.passed
        assert check.reason == RejectionReason.INVALID_DATA
    
    def test_portfolio_risk_calculation(self):
        
        
        positions = []
        for i in range(2):
            pos = MagicMock(spec=Position)
            pos.symbol = f"STOCK{i}.NS"
            pos.status = PositionStatus.OPEN
            pos.entry_price = 1000
            pos.stop_loss = 950
            pos.quantity = 10
            positions.append(pos)
        
        total_risk = self.risk_manager.calculate_portfolio_risk(positions, 100000)
        assert total_risk == 1000
    
    def test_daily_loss_limit_check(self):
        
        
        account = self.create_account(total_capital=100000)
        risk_settings = self.create_risk_settings()
        
        exceeded, msg = self.risk_manager.check_daily_loss_limit(account, risk_settings, -1500)
        assert not exceeded
        
        exceeded, msg = self.risk_manager.check_daily_loss_limit(account, risk_settings, -2500)
        assert exceeded
        assert "exceeded" in msg.lower()


class TestEventRiskProvider:
    def test_dummy_provider(self):
        provider = DummyEventRiskProvider()
        assert provider.get_provider_name() == "DummyEventRiskProvider"
        assert provider.is_healthy()
        
        events = provider.get_upcoming_events(["RELIANCE.NS"], 7)
        assert events == {"RELIANCE.NS": []}
        
        has_event, event = provider.has_high_impact_event("RELIANCE.NS", 7)
        assert not has_event
        assert event is None
    
    def test_create_provider(self):
        dummy = create_event_risk_provider("dummy")
        assert isinstance(dummy, DummyEventRiskProvider)
        
        yahoo = create_event_risk_provider("yahoo")
        assert isinstance(yahoo, YahooFinanceEventRiskProvider)
    
    def test_corporate_event_dataclass(self):
        event = CorporateEvent(
            symbol="RELIANCE.NS",
            event_type=EventType.EARNINGS,
            event_date=date.today() + timedelta(days=3),
            impact=EventImpact.HIGH,
            description="Q3 Results",
            source="NSE"
        )
        assert event.symbol == "RELIANCE.NS"
        assert event.impact == EventImpact.HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])