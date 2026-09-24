# Market Structure / Price Action Patterns Documentation

## Overview
Deterministic market structure analysis using confirmed pivot points. Identifies trends, swings, structural breaks, and key levels without subjective interpretation.

## Pivot Foundation
All structure patterns use shared `PivotDetector`:
- `left_bars`: Bars before pivot (default 5)
- `right_bars`: Bars after pivot for confirmation (default 5)
- Only confirmed pivots used for live detection

## Swing Definitions

### Higher High (HH)
- Current pivot high > Previous pivot high
- Both pivots confirmed
- Bullish signal

### Higher Low (HL)
- Current pivot low > Previous pivot low
- Both pivots confirmed
- Bullish signal

### Lower High (LH)
- Current pivot high < Previous pivot high
- Bearish signal

### Lower Low (LL)
- Current pivot low < Previous pivot low
- Bearish signal

## Trend Detection

### Uptrend
- Minimum 3 consecutive HH + HL pairs
- Configurable `trend_min_swings` (default 3)
- Confirmed when sequence complete

### Downtrend
- Minimum 3 consecutive LH + LL pairs
- Same swing count requirement

### Ranging / Sideways
- Last 3 pivot highs within `range_threshold` (default 5%)
- Last 3 pivot lows within `range_threshold`
- No clear HH/HL or LH/LL sequence

## Structural Breaks

### Break of Structure (BOS)
**Bullish BOS**:
- Prior: Uptrend (HH/HL sequence intact)
- Price closes above most recent swing high
- Higher low remains intact
- Confirms trend continuation

**Bearish BOS**:
- Prior: Downtrend (LH/LL sequence intact)
- Price closes below most recent swing low
- Lower high remains intact
- Confirms trend continuation

### Change of Character (CHOCH)
**Bullish CHOCH**:
- Prior: Downtrend (LH/LL sequence)
- Price closes above most recent swing high
- Lower low was in place
- Signals potential trend reversal to bullish

**Bearish CHOCH**:
- Prior: Uptrend (HH/HL sequence)
- Price closes below most recent swing low
- Higher high was in place
- Signals potential trend reversal to bearish

## Support & Resistance

### Support
- Pivot low tested ≥ 2 times
- Tests within 1% price tolerance
- Current price within 5% above level
- Strength = number of touches

### Resistance
- Pivot high tested ≥ 2 times
- Same criteria as support
- Current price within 5% below level

### Support Break
- Confirmed support level
- Previous close ≥ support
- Current close < support * (1 - breakout_threshold)
- Volume confirmation preferred

### Resistance Break
- Confirmed resistance level
- Previous close ≤ resistance
- Current close > resistance * (1 + breakout_threshold)
- Volume confirmation preferred

## Breakout Patterns

### Breakout
- Resistance break with bullish candle
- Volume > 1.2x previous
- Target = resistance + (resistance - nearest support)

### Breakdown
- Support break with bearish candle
- Volume > 1.2x previous
- Target = support - (nearest resistance - support)

### Breakout Retest
- After breakout, price returns to broken level
- Holds within `retest_tolerance` (default 0.3%)
- Confirms level flip (resistance→support or support→resistance)
- High quality entry signal

### Failed Breakout
- Breakout occurs but price closes back inside pattern
- Within 3 bars of breakout
- Invalidates breakout signal

### Failed Breakdown
- Inverse of failed breakout

## Liquidity Concepts

### Liquidity Sweep High
- Price spikes above recent swing high
- Closes back below that high
- Indicates stop hunt / liquidity grab above highs
- Bearish signal (trapped longs)

### Liquidity Sweep Low
- Price spikes below recent swing low
- Closes back above that low
- Bullish signal (trapped shorts)

## Swing Failure Pattern

### Bearish Swing Failure
- Higher high formed (HH)
- Followed by lower low (LL) breaking prior HL
- Confirms trend reversal to bearish
- Entry on LL confirmation

### Bullish Swing Failure
- Lower low formed (LL)
- Followed by higher high (HH) breaking prior LH
- Confirms trend reversal to bullish
- Entry on HH confirmation

## Confirmation Rules
- All swings require confirmed pivots
- Breaks require close beyond level (not just wick)
- Retests must hold within tolerance
- Volume confirmation increases quality

## Invalidation Rules
- BOS/CHOCH invalidated if price closes back beyond broken level
- Support/Resistance invalidated if broken with volume
- Trend invalidated if structure sequence breaks

## Quality Factors
- Number of confirming swings
- Volume on breakout/breakdown
- Time at level (older = stronger)
- Multiple timeframe alignment
- Confluence with other patterns

## Limitations
- Pivot lag: `right_bars` delay for confirmation
- Parameter sensitivity (left/right bars, thresholds)
- Whipsaws in ranging markets
- No fundamental context
- Timeframe dependent