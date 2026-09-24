# Candlestick Patterns Documentation

## Overview
Implementation of standard candlestick patterns with configurable mathematical thresholds. All patterns use deterministic rules based on candle anatomy ratios.

## Candle Anatomy Metrics

For each candle:
- `body = |close - open|`
- `range = high - low`
- `upper_wick = high - max(open, close)`
- `lower_wick = min(open, close) - low`
- `body_ratio = body / range`
- `upper_wick_ratio = upper_wick / range`
- `lower_wick_ratio = lower_wick / range`

## Configurable Thresholds

```python
CandlestickConfig:
    doji_threshold: 0.1          # body_ratio <= 10% of range
    body_ratio_threshold: 0.5     # General body size reference
    long_wick_ratio: 2.0          # Wick >= 2x body
    short_wick_ratio: 0.3         # Wick <= 30% of range
    marubozu_threshold: 0.95      # Body >= 95% of range
    spinning_top_body_max: 0.3    # Body <= 30% of range
    engulfing_threshold: 1.0      # Engulfing body >= prior body
    harami_threshold: 0.25        # Harami body <= 25% of prior
    piercing_threshold: 0.5       # Pierce >= 50% of prior body
    dark_cloud_threshold: 0.5     # Cover >= 50% of prior body
    tweezer_tolerance: 0.002      # Price match within 0.2%
    three_soldiers_min_body: 0.6  # Min body ratio for soldiers
    three_crows_max_body: 0.6     # Min body ratio for crows
    star_gap_threshold: 0.003     # Gap >= 0.3%
    morning_star_third_body: 0.5  # Third candle body ratio
    evening_star_third_body: 0.5
```

## Single Candle Patterns

### Doji
- `body_ratio <= doji_threshold`
- Open ≈ Close
- Neutral pattern

### Long-Legged Doji
- Doji + `upper_wick_ratio > long_wick_ratio` AND `lower_wick_ratio > long_wick_ratio`
- High indecision

### Dragonfly Doji
- Doji + `lower_wick_ratio > long_wick_ratio` AND `upper_wick_ratio < short_wick_ratio`
- Bullish reversal at support

### Gravestone Doji
- Doji + `upper_wick_ratio > long_wick_ratio` AND `lower_wick_ratio < short_wick_ratio`
- Bearish reversal at resistance

### Hammer
- `lower_wick_ratio > long_wick_ratio` AND `upper_wick_ratio < short_wick_ratio` AND `body_ratio > doji_threshold`
- Small body at top, long lower wick
- Bullish after downtrend

### Hanging Man
- Same anatomy as Hammer but appears after uptrend
- Bearish reversal signal

### Inverted Hammer
- `upper_wick_ratio > long_wick_ratio` AND `lower_wick_ratio < short_wick_ratio` AND `body_ratio > doji_threshold`
- Bullish reversal potential

### Shooting Star
- Same anatomy as Inverted Hammer but after uptrend
- Bearish reversal signal

### Marubozu (Bullish/Bearish)
- `body_ratio >= marubozu_threshold`
- Minimal wicks
- Strong directional momentum

### Spinning Top
- `body_ratio <= spinning_top_body_max` AND `upper_wick_ratio > 0.3` AND `lower_wick_ratio > 0.3`
- Small body, long wicks both sides
- Indecision

## Two Candle Patterns

### Bullish Engulfing
- Prior: Bearish, Current: Bullish
- `current.open < prior.close` AND `current.close > prior.open`
- `current.body >= prior.body * engulfing_threshold`

### Bearish Engulfing
- Prior: Bullish, Current: Bearish
- `current.open > prior.close` AND `current.close < prior.open`
- `current.body >= prior.body * engulfing_threshold`

### Bullish Harami
- Prior: Bearish, Current: Bullish
- `current.open > prior.close` AND `current.close < prior.open`
- `current.body <= prior.body * harami_threshold`

### Bearish Harami
- Prior: Bullish, Current: Bearish
- `current.open < prior.close` AND `current.close > prior.open`
- `current.body <= prior.body * harami_threshold`

### Piercing Line
- Prior: Bearish, Current: Bullish
- `current.open < prior.close` AND `current.close > (prior.open + prior.close) / 2`
- `current.close < prior.open`

### Dark Cloud Cover
- Prior: Bullish, Current: Bearish
- `current.open > prior.close` AND `current.close < (prior.open + prior.close) / 2`
- `current.close > prior.open`

### Tweezer Bottom
- `|low1 - low2| / min(low1, low2) < tweezer_tolerance`
- Prior bearish, current bullish
- Matching lows = support

### Tweezer Top
- `|high1 - high2| / min(high1, high2) < tweezer_tolerance`
- Prior bullish, current bearish
- Matching highs = resistance

## Three Candle Patterns

### Morning Star
1. Long bearish candle
2. Doji/star (gap down preferred)
3. Long bullish candle (gap up preferred, body_ratio >= morning_star_third_body)
- Bullish reversal

### Evening Star
1. Long bullish candle
2. Doji/star (gap up preferred)
3. Long bearish candle (gap down preferred, body_ratio >= evening_star_third_body)
- Bearish reversal

### Three White Soldiers
- 3 consecutive bullish candles
- Each: `body_ratio >= three_soldiers_min_body`
- Each opens within prior body, closes higher
- Bullish continuation

### Three Black Crows
- 3 consecutive bearish candles
- Each: `body_ratio >= three_crows_max_body`
- Each opens within prior body, closes lower
- Bearish continuation

### Three Inside Up
- Bearish, then Bullish Harami, then higher bullish close
- Bullish reversal

### Three Inside Down
- Bullish, then Bearish Harami, then lower bearish close
- Bearish reversal

### Three Outside Up
- Bearish, then Bullish Engulfing, then higher bullish close
- Bullish reversal

### Three Outside Down
- Bullish, then Bearish Engulfing, then lower bearish close
- Bearish reversal

### Rising Three Methods
- Long bullish, 2 small bearish within range, bullish breaks out
- Bullish continuation

### Falling Three Methods
- Long bearish, 2 small bullish within range, bearish breaks down
- Bearish continuation

## Confirmation Rules
- Patterns at relevant S/R levels preferred
- Volume confirmation increases quality
- Trend context considered

## Invalidation
- Price moves beyond pattern extreme against direction
- Specific invalidation level per pattern

## Quality Factors
- Pattern symmetry (how well ratios match ideal)
- Volume confirmation
- Trend alignment
- S/R confluence

## Limitations
- Thresholds are configurable but fixed per detection
- No probabilistic interpretation
- Context (trend, S/R) not automatically evaluated
- Timeframe dependent