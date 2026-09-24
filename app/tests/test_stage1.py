import pytest
from unittest.mock import MagicMock, patch


def test_settings_loading():
    """Test that settings can be loaded"""
    from app.core.config import Settings, get_settings
    
    with patch.dict('os.environ', {
        'ANGEL_ONE_API_KEY': 'test_key',
        'ANGEL_ONE_CLIENT_ID': 'test_client',
        'ANGEL_ONE_PASSWORD': 'test_pass',
        'ANGEL_ONE_TOTP_SECRET': 'test_totp',
        'TRADING_MODE': 'DRY_RUN',
        'TOTAL_PORTFOLIO_CAPITAL': '100000',
        'DATABASE_URL': 'sqlite:///./test.db',
    }):
        settings = Settings()
        assert settings.TRADING_MODE == "DRY_RUN"
        assert settings.is_dry_run is True
        assert settings.is_live is False
        assert settings.TOTAL_PORTFOLIO_CAPITAL == 100000.0


def test_database_models():
    """Test that all models can be imported"""
    from app.models import (
        Base, Account, Position, Order, Signal, 
        TradingRun, JournalEntry, RiskSettings, 
        AuditLog, Watchlist, DailyPortfolioSnapshot
    )
    
    # Verify all models are imported
    assert Base is not None
    assert Account is not None
    assert Position is not None
    assert Order is not None
    assert Signal is not None
    assert TradingRun is not None
    assert JournalEntry is not None
    assert RiskSettings is not None
    assert AuditLog is not None
    assert Watchlist is not None
    assert DailyPortfolioSnapshot is not None


def test_enums():
    """Test enum values"""
    from app.models.position import PositionStatus
    from app.models.order import OrderSide, OrderType, OrderProductType, OrderStatus
    from app.models.signal import SignalType, SignalDecision
    from app.models.trading_run import TradingRunStatus
    from app.models.journal_entry import JournalEntryType
    
    assert PositionStatus.OPEN == "OPEN"
    assert PositionStatus.CLOSED == "CLOSED"
    assert OrderSide.BUY == "BUY"
    assert OrderSide.SELL == "SELL"
    assert OrderType.MARKET == "MARKET"
    assert OrderProductType.DELIVERY == "DELIVERY"
    assert OrderStatus.PENDING == "PENDING"
    assert SignalType.BUY == "BUY"
    assert SignalDecision.PENDING == "PENDING"
    assert TradingRunStatus.STARTED == "STARTED"
    assert JournalEntryType.TRADE_OPEN == "TRADE_OPEN"


def test_config_defaults():
    """Test config default values"""
    from app.core.config import Settings
    
    with patch.dict('os.environ', {
        'ANGEL_ONE_API_KEY': 'test',
        'ANGEL_ONE_CLIENT_ID': 'test',
        'ANGEL_ONE_PASSWORD': 'test',
        'ANGEL_ONE_TOTP_SECRET': 'test',
    }, clear=True):
        settings = Settings()
        assert settings.MAX_RISK_PERCENT == 0.01
        assert settings.MAX_DAILY_LOSS_PERCENT == 0.02
        assert settings.MAX_OPEN_POSITIONS == 3
        assert settings.MAX_STOP_LOSS_PERCENT == 0.08
        assert settings.MIN_RISK_REWARD == 2.0
        assert settings.SWING_LOW_LOOKBACK == 5
        assert settings.EVENT_EXCLUSION_WINDOW == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])