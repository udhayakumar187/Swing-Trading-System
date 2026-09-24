# Classic Chart Patterns Documentation

## Overview
Deterministic detection of classical chart patterns using pivot points, trendline fitting, and price/time symmetry rules. All tolerances configurable.

## Pivot-Based Detection
All chart patterns use the shared `PivotDetector` with configurable `left_bars` and `right_bars`. Pivots must be confirmed (right bars elapsed) for live detection.

## Common Parameters

```python
ChartPatternConfig:
    tolerance: 0.02              # 2% price tolerance for equality
    min_pattern_bars: 10         # Minimum bars between pattern points
    max_pattern_bars: 100        # Maximum pattern duration
    breakout_threshold: 0.01     # 1% close beyond level for confirmation
    time_symmetry_tolerance: 0.3 # 30% time symmetry allowance
```

## Pattern Definitions

### Double Top
- Two pivot highs at similar price (`|H1-H2|/max(H1,H2) <= tolerance`)
- Separated by `min_pattern_bars` to `max_pattern_bars`
- Neckline = lowest pivot low between peaks
- **Confirmation**: Close below neckline * (1 - breakout_threshold)
- **Target**: Neckline - (Peak - Neckline)
- **Invalidation**: Above max(Peak1, Peak2)

### Double Bottom
- Two pivot lows at similar price
- Neckline = highest pivot high between troughs
- **Confirmation**: Close above neckline * (1 + breakout_threshold)
- **Target**: Neckline + (Neckline - Trough)
- **Invalidation**: Below min(Trough1, Trough2)

### Triple Top / Triple Bottom
- Three peaks/troughs at similar price
- Same confirmation/invalidation as double variants
- More reliable but rarer

### Head and Shoulders
- Three peaks: Left Shoulder (LS), Head (H), Right Shoulder (RS)
- H > LS and H > RS, |LS - RS|/max(LS,RS) <= tolerance
- Neckline = line connecting low after LS and low after H
- Neckline slopes allowed within tolerance
- **Confirmation**: Close below neckline
- **Target**: Neckline - (Head - Neckline)
- **Invalidation**: Above Head

### Inverse Head and Shoulders
- Three troughs: LS, Head, RS
- Head < LS and Head < RS, |LS - RS| <= tolerance
- Neckline connects highs
- **Confirmation**: Close above neckline
- **Target**: Neckline + (Neckline - Head)
- **Invalidation**: Below Head

### Ascending Triangle
- Flat resistance (pivot highs horizontal within tolerance)
- Rising support (pivot lows trending up)
- **Confirmation**: Close above resistance
- **Target**: Resistance + (Resistance - Support at breakout)
- **Invalidation**: Below rising support line

### Descending Triangle
- Flat support (pivot lows horizontal)
- Falling resistance (pivot highs trending down)
- **Confirmation**: Close below support
- **Target**: Support - (Resistance at breakout - Support)
- **Invalidation**: Above falling resistance

### Symmetrical Triangle
- Falling resistance, rising support (converging)
- **Confirmation**: Close above resistance (bullish) or below support (bearish)
- **Target**: Breakout level + pattern height at widest point
- **Invalidation**: Opposite trendline

### Rising Wedge
- Both trendlines sloping up, resistance steeper than support
- Bearish reversal pattern
- **Confirmation**: Close below support
- **Target**: Support - pattern height
- **Invalidation**: Above resistance

### Falling Wedge
- Both trendlines sloping down, support steeper than resistance
- Bullish reversal pattern
- **Confirmation**: Close above resistance
- **Target**: Resistance + pattern height
- **Invalidation**: Below support

### Rectangle
- Horizontal resistance and support (both within tolerance)
- Multiple touches on both levels
- **Confirmation**: Breakout above resistance or below support
- **Target**: Breakout level + rectangle height
- **Invalidation**: Back inside rectangle

### Bull Flag
- Sharp pole (strong move up in few bars)
- Flag: downward sloping parallel channel
- **Confirmation**: Close above flag resistance
- **Target**: Breakout + pole height
- **Invalidation**: Below flag support

### Bear Flag
- Sharp pole down
- Flag: upward sloping channel
- **Confirmation**: Close below flag support
- **Target**: Breakdown - pole height
- **Invalidation**: Above flag resistance

### Pennant
- Similar to flag but converging trendlines (small triangle)
- Short duration
- Same target calculation as flag

### Cup and Handle
- U-shape cup (rounded bottom)
- Left and right rims at similar price
- Cup depth 10-50% of rim price
- Handle: shallow pullback (< 50% cup depth)
- **Confirmation**: Close above rim
- **Target**: Rim + cup depth
- **Invalidation**: Below handle low

### Inverse Cup and Handle
- Inverted U-shape
- Bearish continuation

### Rounding Bottom
- 5+ pivot lows forming gradual curve: High → Higher → Low → Higher → High
- Gradual curvature, no sharp V
- **Confirmation**: Close above left lip
- **Target**: Left lip + (Left lip - Bottom)
- **Invalidation**: Below bottom

### Rounding Top
- Inverse of rounding bottom
- Bearish reversal

### Broadening Formation
- Diverging trendlines: rising resistance, falling support
- Increasing volatility
- No clear directional bias
- **Status**: FORMING only (no confirmation rule)

## Trendline Fitting

For sloping lines (triangles, wedges, flags):
- Linear regression on pivot points
- Slope = price_change / bar_change
- Projected line at current bar = last_pivot_price + slope * bars_since

## Volume Confirmation
- Breakouts: volume > 1.5x recent average
- Increases pattern quality score
- Not required for detection

## Time Symmetry
- Left and right sides of pattern should have similar duration
- Tolerance: 30% difference allowed
- Affects quality score, not detection

## Quality Scoring
- Number of clean touches on trendlines
- Volume profile (decreasing during formation, increasing on breakout)
- Time symmetry
- Pattern completeness
- Trend context alignment

## Limitations
- Requires confirmed pivots (lookback delay)
- Subjective pattern boundaries handled by tolerance
- Complex patterns (cup & handle) need more bars
- False breakouts possible - wait for close confirmation