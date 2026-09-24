# TODO - Pattern Tracking System

## ✅ Completed

### Core Pattern Tracking Infrastructure
- [x] 12 Pattern Types defined (PatternType enum)
  - BREAKOUT_VOLUME
  - BREAKOUT_RETEST
  - TREND_PULLBACK
  - EMA_PULLBACK
  - DOUBLE_BOTTOM
  - DOUBLE_TOP
  - BULL_FLAG
  - BEAR_FLAG
  - ASCENDING_TRIANGLE_BREAKOUT
  - DESCENDING_TRIANGLE_BREAKDOWN
  - SUPPORT_BOUNCE
  - RESISTANCE_REJECTION

- [x] Pattern Tracking Models (Pydantic)
  - TrackedPattern - stores detection details, key levels, stop/target
  - PatternForwardTracking - stores 20-day forward price movement
  - PatternStatistics - win rates, returns, R-multiples
  - PatternScanConfig - configurable scan parameters

- [x] Supabase Integration
  - SupabasePatternRepository with CRUD operations
  - Pattern statistics aggregation
  - Forward tracking persistence

- [x] Pattern Scanner Service
  - yfinance data fetching for NSE symbols
  - Pattern detection using existing registry
  - Mapping from detector names to PatternType enum
  - Forward tracking creation (20 days)

- [x] Outcome Evaluation
  - Target hit / Stop hit / Expired / Invalidated detection
  - Max favorable/adverse excursion tracking
  - Daily price snapshots at 1d, 3d, 5d, 10d, 20d
  - R-multiple calculation

- [x] REST API Endpoints
  - POST /api/patterns/scan - Trigger pattern scan
  - POST /api/patterns/scan/background - Async scan
  - POST /api/patterns/update-outcomes - Update outcomes
  - GET /api/patterns/list - Filter patterns
  - GET /api/patterns/pending - Get pending patterns
  - GET /api/patterns/statistics - Aggregated stats
  - GET /api/patterns/forward-tracking/{id} - Detailed tracking
  - GET /api/patterns/config - Scanner configuration

- [x] Supabase Schema
  - tracked_patterns table with indexes
  - pattern_forward_tracking table
  - pattern_scan_config table
  - pattern_statistics view
  - pattern_performance_summary view

- [x] Configuration
  - Added Supabase settings to config.py
  - Pattern scanner settings (symbols, timeframe, lookback, forward days)
  - Updated .env.example with Supabase credentials

- [x] Scripts
  - app/scripts/run_pattern_scanner.py - CLI runner

---

## 🔧 Required Setup (Before Running)

### 1. Supabase Project Setup
```bash
# 1. Create project at https://supabase.com
# 2. Go to SQL Editor
# 3. Run: deployment/supabase_pattern_tables.sql
# 4. Get credentials from Settings > API
```

### 2. Environment Configuration
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your credentials:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
SUPABASE_DB_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Pattern Scanner (adjust as needed)
PATTERN_SCAN_SYMBOLS=RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS
PATTERN_SCAN_TIMEFRAME=1d
PATTERN_SCAN_LOOKBACK_DAYS=200
PATTERN_FORWARD_DAYS=20
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
# Includes: supabase>=2.0.0
```

---

## 🚀 Usage

### Run Pattern Scanner (Manual)
```bash
python app/scripts/run_pattern_scanner.py
```

### Run via API
```bash
# Start server
uvicorn app.main:app --reload

# Trigger scan
curl -X POST http://localhost:8000/api/patterns/scan \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["RELIANCE.NS", "TCS.NS"], "timeframe": "1d"}'

# Get statistics
curl http://localhost:8000/api/patterns/statistics

# List patterns for a symbol
curl "http://localhost:8000/api/patterns/list?symbol=RELIANCE.NS&limit=50"

# Get pending patterns
curl http://localhost:8000/api/patterns/pending

# Update outcomes (run daily via cron/scheduler)
curl -X POST http://localhost:8000/api/patterns/update-outcomes
```

---

## 📋 Pending / Future Enhancements

### Pattern Detection Improvements
- [ ] Add explicit detectors for each of the 12 pattern types
  - [ ] Breakout + Volume detector (volume spike on breakout)
  - [ ] Breakout + Retest detector (breakout then pullback to level)
  - [ ] Trend Pullback detector (EMA pullback in trending market)
  - [ ] Support/Resistance bounce/rejection detectors
  - [ ] Volume confirmation logic for all patterns
- [ ] Add pattern quality scoring (0-100) based on:
  - [ ] Volume confirmation
  - [ ] Pattern symmetry
  - [ ] Time symmetry
  - [ ] Trend alignment
  - [ ] Multiple touch points
- [ ] Add candlestick pattern confirmations (engulfing, hammer, doji at key levels)

### Scanner Enhancements
- [ ] Add intraday timeframe support (1h, 15m, 5m)
- [ ] Add pre-market / post-market data handling
- [ ] Implement rate limiting for yfinance API
- [ ] Add caching layer for fetched data
- [ ] Parallel processing for multiple symbols/timeframes
- [ ] Add scheduled scanning (APScheduler integration)

### Data & Tracking
- [ ] Add sector/industry classification for patterns
- [ ] Track market regime (trending/range/volatile) at detection time
- [ ] Add fundamental data snapshot at detection (P/E, earnings date)
- [ ] Implement pattern clustering (same pattern across multiple symbols)
- [ ] Add correlation tracking (pattern success vs market regime)

### API & Dashboard
- [ ] Frontend dashboard for pattern visualization
  - [ ] Pattern list with filters
  - [ ] Chart with pattern annotations
  - [ ] Forward tracking chart (price path after detection)
  - [ ] Statistics dashboard (win rate by pattern/symbol)
- [ ] Webhook notifications for new patterns
- [ ] Email/Telegram alerts for high-quality setups
- [ ] Export patterns to CSV/Excel

### Backtesting
- [ ] Historical backtest for all 12 patterns
- [ ] Walk-forward optimization
- [ ] Monte Carlo simulation for position sizing
- [ ] Pattern combination analysis (confluence)

### Risk & Position Sizing Integration
- [ ] Integrate with existing RiskManager
- [ ] Auto-calculate position size from pattern risk/reward
- [ ] Portfolio-level pattern exposure limits
- [ ] Sector concentration from pattern signals

### Data Quality
- [ ] Add data validation for yfinance (split/dividend adjustments)
- [ ] Handle symbol changes / delistings
- [ ] Add data freshness checks
- [ ] Implement data gap detection

### Testing
- [ ] Unit tests for PatternScannerService
- [ ] Integration tests with Supabase (test project)
- [ ] Mock yfinance for deterministic tests
- [ ] Test outcome evaluation logic
- [ ] Load test API endpoints

---

## 🐛 Known Issues / Limitations

1. **yfinance rate limits** - May hit limits with many symbols/timeframes
2. **Pattern mapping** - Current mapping from detector names to PatternType is heuristic; may misclassify
3. **Forward tracking** - Only runs when `update_outcomes` is called; needs scheduler
4. **Supabase RLS** - Row Level Security not configured; adjust for production
5. **Timezone** - Detection timestamps in UTC; consider IST for NSE
6. **Weekends/holidays** - Forward tracking counts calendar days, not trading days

---

## 📊 Priority Order

| Priority | Task | Effort |
|----------|------|--------|
| P0 | Run Supabase SQL migration | 5 min |
| P0 | Configure .env with Supabase credentials | 5 min |
| P0 | Test scanner with 1-2 symbols | 10 min |
| P1 | Add explicit 12 pattern detectors | 2-3 days |
| P1 | Add APScheduler for daily scan + outcome update | 1 day |
| P1 | Frontend pattern dashboard | 3-5 days |
| P2 | Backtesting framework for patterns | 2-3 days |
| P2 | Alert system (email/Telegram) | 1 day |
| P3 | Intraday timeframe support | 2 days |
| P3 | Advanced quality scoring | 2 days |

---

## 📝 Notes

- Default symbols: RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS, ICICIBANK.NS (highly liquid NSE large-caps)
- Default timeframe: Daily (1d) - swing trading focus
- Forward tracking: 20 trading days (~1 month)
- All patterns use existing ChartPatternDetector + EMA Pullback Strategy
- Volume confirmation uses 20-day average volume comparison
- Stop loss = pattern invalidation level
- Target = measured move from pattern