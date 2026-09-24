# Volume / Spread Patterns Documentation

## Overview
Volume-based patterns using explicit mathematical formulas. All thresholds configurable. Where terminology is subjective (climax, accumulation), exact formulas provided.

## Core Calculations

### Volume SMA
- Period: 20 (configurable)
- `vol_sma = SMA(volume, period)`

### Volume Ratio
- `vol_ratio = current_volume / vol_sma`

### OBV (On-Balance Volume)
- `direction = sign(close - close_prev)`
- `obv = cumulative_sum(direction * volume)`

### Accumulation/Distribution Line
- `MFM = ((close - low) - (high - close)) / (high - low)` (Money Flow Multiplier)
- `MFV = MFM * volume` (Money Flow Volume)
- `AD = cumulative_sum(MFV)`

## Pattern Definitions

### Volume Spike
```
vol_ratio > volume_spike_mult (default 2.0)
```
- Single bar volume > 2x average
- Neutral direction
- Unusual activity alert

### Volume Expansion
```
recent_5_bar_avg_volume > vol_sma * volume_expansion_mult (default 1.5)
```
- Sustained volume increase over 5 bars
- Neutral direction
- Growing interest

### Volume Contraction
```
recent_5_bar_avg_volume < vol_sma * volume_contraction_mult (default 0.7)
```
- Sustained volume decrease
- Neutral direction
- Waning interest / calm before storm

### Volume Climax
```
vol_ratio > climax_mult (default 3.0)
```
- Extreme volume spike (3x+ average)
- Direction = candle direction (close > open = bullish)
- Potential exhaustion signal
- Often at trend extremes

### High Volume Breakout
```
|price_change| > 2% AND vol_ratio > breakout_volume_mult (default 1.5)
```
- Significant price move with volume confirmation
- Direction = price move direction
- Validates breakout legitimacy

### Low Volume Breakout
```
|price_change| > 2% AND vol_ratio < low_volume_mult (default 0.5)
```
- Price move without volume support
- Suspect breakout
- Higher false breakout probability
- Status: FORMING (not confirmed)

### Volume Confirmation
**Bullish**: Price rising (3-bar) AND volume rising
**Bearish**: Price falling (3-bar) AND volume rising
- Trend confirmation
- Volume validates price direction

### Volume Divergence
**Bullish Divergence (Bearish signal)**: Price rising BUT volume falling
**Bearish Divergence (Bullish signal)**: Price falling BUT volume falling
- Warning signals
- Potential reversal ahead

## OBV Patterns

### OBV Bullish Divergence
```
obv_5_bar_slope > 0 AND price_5_bar_slope <= 0
```
- OBV accumulating while price flat/declining
- Smart money buying
- Bullish signal

### OBV Bearish Divergence
```
obv_5_bar_slope < 0 AND price_5_bar_slope >= 0
```
- OBV distributing while price flat/rising
- Smart money selling
- Bearish signal

### OBV Breakout
```
obv_current >= 20_bar_high * 0.99
```
- OBV at 20-bar high
- Strong buying pressure
- Bullish

### OBV Breakdown
```
obv_current <= 20_bar_low * 1.01
```
- OBV at 20-bar low
- Strong selling pressure
- Bearish

## Accumulation / Distribution

### Accumulation
```
ad_10_bar_slope > 0 AND price_10_bar_slope <= 0
```
- AD line rising, price not
- Institutional accumulation
- Bullish (forming)

### Distribution
```
ad_10_bar_slope < 0 AND price_10_bar_slope >= 0
```
- AD line falling, price not
- Institutional distribution
- Bearish (forming)

## Confirmation Rules
- Volume signals confirmed by price action
- Breakouts require volume expansion
- Climax requires extreme volume + reversal candle
- OBV/AD divergences need price pivot confirmation

## Invalidation Rules
- Volume pattern fails if price reverses immediately
- OBV/AD divergence invalidated if price makes new extreme in original direction

## Quality Factors
- Volume magnitude (ratio vs average)
- Price-volume alignment
- Trend context (volume in trend direction = stronger)
- Persistence (sustained vs single bar)

## Limitations
- Volume data quality varies by source
- Intraday volume patterns differ from daily
- Low float stocks have erratic volume
- No volume data for some instruments (forex, crypto)
- Relative volume more meaningful than absolute