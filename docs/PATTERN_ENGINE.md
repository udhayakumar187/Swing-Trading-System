# Pattern Engine Architecture

## Overview

The Pattern Engine is a deterministic, plugin-based technical analysis system for detecting trading patterns in financial markets. It is designed for research and signal generation only - it does not execute trades.

## Core Components

### PatternDetector (Base Interface)
All pattern detectors inherit from `PatternDetector` abstract base class:
- `detect(data, context) -> List[PatternDetection]`
- Each detector declares metadata via `PatternDefinition`

### PatternRegistry
Central registry managing all detectors:
- `register(detector)` - Add new detector
- `get(name)` - Get detector by name
- `get_by_category(category)` - Get all detectors in category
- `detect_all(data)` - Run all detectors on data

### PatternDetection
Standardized detection result containing:
- Pattern identity (name, category, direction)
- Timestamps (start, confirmation, completion, detection)
- Price levels, invalidation, targets
- Quality score (0-100) based on explicit rules
- Volume confirmation flag
- Detailed explanation (deterministic, not LLM-generated)
- Market regime at detection time

## Pattern Categories

1. **Candlestick** - Single, double, triple candle patterns
2. **Chart Patterns** - Classical formations (H&S, triangles, flags, etc.)
3. **Harmonic** - Fibonacci-based geometric patterns
4. **Market Structure** - Swings, trends, BOS/CHOCH, S/R
5. **Indicator Patterns** - MA, RSI, MACD, BB, Stochastic patterns
6. **Wave** - Elliott-style wave candidates (labeled as candidates only)
7. **Volume** - Volume spikes, climax, OBV, accumulation/distribution
8. **Volatility** - ATR expansion/contraction, BB squeeze/expansion

## Key Design Principles

### Deterministic Detection
- No LLM involvement in pattern recognition
- All thresholds configurable
- Mathematical definitions documented
- Reproducible results

### No Look-Ahead Bias
- Live detection respects pivot confirmation delays
- Historical/offline detection clearly separated
- Tests prevent future-data leakage

### Separation of Concerns
- Pattern Detection ≠ Trading Signal ≠ Risk Management ≠ Execution
- Each layer independent
- Confluence engine combines detections with configurable weights

### Quality Scoring
- Based on explicit measurable factors
- Not a probability of profit
- Documented calculation per pattern

## Configuration

All thresholds externalized:
- `pivot_left_bars`, `pivot_right_bars`
- `volume_multiplier`, `EMA_period`, `RSI_period`
- `pattern_tolerance`, `breakout_confirmation_percentage`
- `harmonic_ratio_tolerance`

## API Endpoints

- `GET /api/patterns` - List all patterns
- `GET /api/patterns/{name}` - Pattern details
- `GET /api/patterns/categories` - Categories summary
- `POST /api/patterns/detect` - Detect patterns on data
- `POST /api/patterns/scan` - Multi-symbol scan
- `POST /api/confluence` - Confluence analysis
- `POST /api/market-regime` - Regime detection
- `POST /api/backtests` - Run backtest
- `GET /api/patterns/pivots/{symbol}` - Get pivots

## Adding New Patterns

1. Create new detector class inheriting `PatternDetector`
2. Implement `detect()` method
3. Define `PatternDefinition` with metadata
4. Register in `initialize_pattern_engine()`

No core engine modifications needed.