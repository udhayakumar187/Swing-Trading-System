# Indicator-Based Patterns Documentation

## Overview
Patterns derived from technical indicator calculations and their interactions with price. All indicators use standard mathematical definitions with configurable periods.

## Moving Averages

### Implemented MAs
- **SMA**: Simple Moving Average
- **EMA**: Exponential Moving Average (span-based)
- **WMA**: Weighted Moving Average (linear weights)

### Patterns

#### Golden Cross
- EMA(20) crosses above SMA(50)
- Bullish trend change signal
- Confirmation: Price above both MAs

#### Death Cross
- EMA(20) crosses below SMA(50)
- Bearish trend change signal
- Confirmation: Price below both MAs

#### Bullish MA Alignment
- EMA(9) > EMA(21) > EMA(50) AND prior bars not aligned
- Strong bullish trend structure

#### Bearish MA Alignment
- EMA(9) < EMA(21) < EMA(50) AND prior bars not aligned
- Strong bearish trend structure

#### EMA Pullback
- Price in uptrend (above EMA(21))
- Pullback: low touches or dips below EMA(21)
- Next candle closes above EMA(21)
- Bullish continuation setup

#### MA Support/Resistance
- Price respects MA as dynamic S/R
- Multiple touches without clear break
- Support: bounces off rising MA
- Resistance: rejects at falling MA

#### MA Compression
- Multiple MAs converging (max spread < 1% of price)
- Precedes volatility expansion
- Direction unknown until breakout

#### MA Expansion
- MAs fanning out rapidly
- Confirms trend acceleration

## RSI (Relative Strength Index)

### Calculation
- Period: 14 (configurable)
- Wilder's smoothing
- Range: 0-100

### Patterns

#### RSI Overbought
- RSI ≥ 70 (configurable)
- Bearish warning
- Not a sell signal alone

#### RSI Oversold
- RSI ≤ 30 (configurable)
- Bullish warning
- Not a buy signal alone

#### Bullish RSI Divergence
- Price: Lower Low
- RSI: Higher Low (at corresponding pivots)
- Regular divergence at pivot points only
- Lookback: 5-14 bars (configurable)
- Bullish reversal signal

#### Bearish RSI Divergence
- Price: Higher High
- RSI: Lower High
- Regular divergence at pivot points
- Bearish reversal signal

#### RSI Failure Swing
- RSI exceeds 70, pulls back, fails to reach 70 again, breaks below prior low
- Or inverse for oversold
- Stronger than simple divergence

## MACD (Moving Average Convergence Divergence)

### Calculation
- Fast EMA: 12, Slow EMA: 26, Signal: 9 (all configurable)
- MACD Line = Fast - Slow
- Signal Line = EMA(MACD, 9)
- Histogram = MACD - Signal

### Patterns

#### Bullish MACD Crossover
- MACD line crosses above Signal line
- Momentum turning bullish

#### Bearish MACD Crossover
- MACD line crosses below Signal line
- Momentum turning bearish

#### MACD Zero Line Cross
- Histogram crosses zero
- Up cross: bullish acceleration
- Down cross: bearish acceleration

#### Bullish MACD Divergence
- Price lower low, MACD higher low (at pivots)
- Regular divergence

#### Bearish MACD Divergence
- Price higher high, MACD lower high
- Regular divergence

## Bollinger Bands

### Calculation
- Period: 20, Std Dev: 2.0 (configurable)
- Middle = SMA(20)
- Upper = Middle + 2*Std
- Lower = Middle - 2*Std
- Bandwidth = (Upper - Lower) / Middle

### Patterns

#### Upper Band Breakout
- Close > Upper Band
- Bullish breakout signal
- Invalidation: Close back below Middle

#### Lower Band Breakdown
- Close < Lower Band
- Bearish breakdown signal
- Invalidation: Close back above Middle

#### Bollinger Squeeze
- Bandwidth < 0.05 (configurable)
- Volatility compression
- Breakout imminent (direction unknown)
- Status: FORMING

#### Bollinger Expansion
- Bandwidth increasing rapidly (> 1.5x recent)
- Volatility expansion
- Trend acceleration

#### Mean Reversion Setup
- Price at extreme band with reversal candle
- Target: Middle band
- Higher probability in ranging markets

## Stochastic Oscillator

### Calculation
- %K Period: 14, %D Period: 3, Smooth: 3
- %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
- %D = SMA(%K, 3)

### Patterns

#### Bullish Crossover
- %K crosses above %D
- Both < 20 (oversold zone)
- Bullish reversal

#### Bearish Crossover
- %K crosses below %D
- Both > 80 (overbought zone)
- Bearish reversal

#### Overbought/Oversold
- %K and %D > 80 / < 20
- Warning levels, not signals alone

## ATR (Average True Range)

### Calculation
- Period: 14
- TR = max(H-L, |H-C_prev|, |L-C_prev|)
- ATR = SMA(TR, 14)

### Patterns

#### ATR Expansion
- Current ATR > 1.5x recent 10-bar average
- Volatility spike
- Often precedes trend moves

#### ATR Contraction
- Current ATR < 0.7x recent average
- Volatility compression
- Precedes breakout

## VWAP (Volume Weighted Average Price)
- Intraday only
- Cumulative (TP * Volume) / Cumulative Volume
- Used for intraday mean reversion

## Confirmation Rules
- Price action confirmation required
- Volume confirmation for breakouts
- Trend alignment check
- Multi-timeframe agreement preferred

## Invalidation Rules
- Price reverses beyond key level
- Indicator reverses signal
- Failed follow-through

## Quality Factors
- Multiple indicator alignment
- Volume confirmation
- Trend strength (ADX)
- Risk/reward ratio
- Timeframe confluence

## Limitations
- Lagging indicators (all MAs, MACD)
- False signals in ranging markets
- Parameter sensitivity
- No fundamental consideration
- Overbought/oversold can persist in strong trends