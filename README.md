# Swing Trading System

Autonomous swing-trading backend for Indian NSE equities.

## Overview

This system implements a deterministic swing-trading strategy for highly liquid large-cap Indian stocks using:
- Daily timeframe
- Multi-day delivery positions
- Technical trend/pullback setup
- Strict predefined risk management
- No intraday trading, no F&O, no options, no leverage

## Architecture

```
app/
├── api/            # FastAPI endpoints
├── core/           # Configuration, database, logging
├── models/         # SQLAlchemy models
├── schemas/        # Pydantic schemas
├── services/       # Business logic services
├── strategies/     # Trading strategies
├── risk/           # Risk management
├── brokers/        # Broker adapters
├── market_data/    # Market data providers
├── scheduler/      # APScheduler jobs
├── repositories/   # Data access layer
├── utils/          # Utilities
└── tests/          # Unit tests
```

## Safety Features

- **DRY_RUN mode is default** - No real orders executed
- Explicit configuration required for LIVE mode
- All credentials protected via environment variables
- Comprehensive audit logging
- Duplicate signal protection
- Daily loss limits
- Portfolio risk limits

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required settings:
- `ANGEL_ONE_API_KEY`, `ANGEL_ONE_CLIENT_ID`, `ANGEL_ONE_PASSWORD`, `ANGEL_ONE_TOTP_SECRET`
- `TRADING_MODE=DRY_RUN` (default) or `LIVE`
- `TOTAL_PORTFOLIO_CAPITAL`
- Risk parameters: `MAX_RISK_PERCENT`, `MAX_DAILY_LOSS_PERCENT`, `MAX_OPEN_POSITIONS`, `MAX_STOP_LOSS_PERCENT`, `MIN_RISK_REWARD`

## Quick Start

### Local Development (SQLite)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### With Docker

```bash
# Configure environment
cp .env.example .env
# Edit .env

# Start services
docker-compose up -d
```

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/health/db` - Database health
- `GET /api/positions` - Open positions
- `GET /api/orders` - Order history
- `GET /api/signals` - Generated signals
- `GET /api/trading-runs` - Trading run history
- `GET /api/portfolio` - Portfolio summary
- `GET /api/risk-settings` - Risk configuration
- `POST /api/risk-settings` - Update risk settings
- `POST /api/trading/run` - Manual trading run

## Strategy: EMA Pullback

**BUY Conditions (ALL must be true):**
1. Close > 50-day SMA
2. 50-day SMA > Previous day's 50-day SMA (rising)
3. Low within 0.5% of 20-day EMA
4. Volume > 20-day average volume

**Risk Management:**
- Stop loss = Recent swing low
- Max stop loss distance = 8% from entry
- Target = Entry + 2R (risk/reward >= 2.0)
- Position size = Portfolio * MAX_RISK_PERCENT / Risk per share

## Database Models

- `accounts` - Broker accounts
- `positions` - Open/closed positions
- `orders` - Order history
- `signals` - Generated signals
- `trading_runs` - Daily execution runs
- `journal_entries` - Trading journal
- `risk_settings` - Risk parameters
- `audit_logs` - Audit trail
- `watchlist` - Symbols to monitor
- `daily_portfolio_snapshots` - Daily equity curves

## Testing

```bash
# Run tests
pytest app/tests/ -v

# Run with coverage
pytest app/tests/ --cov=app --cov-report=html
```

## Deployment

### VPS Setup (Ubuntu)

1. Install Docker & Docker Compose
2. Clone repository
3. Configure `.env`
4. Run `docker-compose up -d`
5. Set up reverse proxy (nginx) with HTTPS
6. Configure systemd for auto-restart

### Health Checks

- Application: `GET /api/health`
- Database: `GET /api/health/db`

## Security

- Never commit `.env` file
- Never log credentials
- Dashboard is read-only
- Admin endpoints protected
- CORS restricted

## License

Proprietary - For internal use only.