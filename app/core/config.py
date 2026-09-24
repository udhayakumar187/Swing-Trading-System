from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    # Angel One Credentials
    ANGEL_ONE_API_KEY: str = Field(default="", description="Angel One API Key")
    ANGEL_ONE_CLIENT_ID: str = Field(default="", description="Angel One Client ID")
    ANGEL_ONE_PASSWORD: str = Field(default="", description="Angel One Password")
    ANGEL_ONE_TOTP_SECRET: str = Field(default="", description="Angel One TOTP Secret")

    # Trading Mode
    TRADING_MODE: str = Field(default="DRY_RUN", description="Trading mode: DRY_RUN or LIVE")

    # Portfolio Configuration
    TOTAL_PORTFOLIO_CAPITAL: float = Field(default=100000.0, description="Total portfolio capital in INR")
    MAX_RISK_PERCENT: float = Field(default=0.01, description="Maximum risk per trade as percentage of portfolio")
    MAX_DAILY_LOSS_PERCENT: float = Field(default=0.02, description="Maximum daily loss as percentage of portfolio")
    MAX_OPEN_POSITIONS: int = Field(default=3, description="Maximum number of open positions")
    MAX_STOP_LOSS_PERCENT: float = Field(default=0.08, description="Maximum stop loss percentage from entry")
    MIN_RISK_REWARD: float = Field(default=2.0, description="Minimum risk/reward ratio")

    # Execution Settings
    SIGNAL_EXECUTION_TIME: str = Field(default="15:45", description="Time to execute signals (HH:MM in TIMEZONE)")
    TIMEZONE: str = Field(default="Asia/Kolkata", description="Timezone for scheduling")

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./trading.db", description="Database URL")

    # Strategy Parameters
    SWING_LOW_LOOKBACK: int = Field(default=5, description="Number of candles for swing low detection")
    EVENT_EXCLUSION_WINDOW: int = Field(default=7, description="Days to exclude around corporate events")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    @property
    def is_dry_run(self) -> bool:
        return self.TRADING_MODE.upper() == "DRY_RUN"

    @property
    def is_live(self) -> bool:
        return self.TRADING_MODE.upper() == "LIVE"


@lru_cache
def get_settings() -> Settings:
    return Settings()