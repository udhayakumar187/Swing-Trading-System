# Harmonic Patterns Documentation

## Overview
Harmonic patterns are geometric price structures based on Fibonacci ratios between sequential pivot points (X-A-B-C-D). Detection uses strict ratio validation with configurable tolerance.

## Pattern Structure
All patterns use 5 confirmed pivots: X → A → B → C → D
- Alternating high/low sequence required
- X-A: Initial impulse leg
- A-B: Retracement of X-A
- B-C: Counter-trend move
- C-D: Final leg completing pattern at D
- D is the Potential Reversal Zone (PRZ)

## Ratio Validation
Each pattern defines expected ranges for four key ratios:
- `AB/XA`: Retracement of XA leg
- `BC/AB`: Retracement of AB leg
- `CD/BC`: Extension of BC leg
- `AD/XA`: Overall retracement from X to D

All ratios must fall within `expected_range * (1 ± tolerance)`
Default tolerance: 5% (configurable)

## Pattern Definitions

### Gartley
| Ratio | Min | Max | Description |
|-------|-----|-----|-------------|
| AB/XA | 0.618 | 0.618 | Exact 61.8% retrace |
| BC/AB | 0.382 | 0.886 | 38.2%-88.6% retrace |
| CD/BC | 1.13 | 1.618 | 113%-161.8% extension |
| AD/XA | 0.786 | 0.786 | Exact 78.6% retrace |

**Direction**: Bullish if D is pivot low, Bearish if D is pivot high
**PRZ**: At D completion
**Targets**: 38.2% and 61.8% of XA from D
**Invalidation**: Beyond X

### Bat
| Ratio | Min | Max |
|-------|-----|-----|
| AB/XA | 0.382 | 0.50 |
| BC/AB | 0.382 | 0.886 |
| CD/BC | 1.618 | 2.618 |
| AD/XA | 0.886 | 0.886 |

**Key**: Deeper AB retrace, extended CD, precise 88.6% AD/XA

### Butterfly
| Ratio | Min | Max |
|-------|-----|-----|
| AB/XA | 0.786 | 0.786 |
| BC/AB | 0.382 | 0.886 |
| CD/BC | 1.618 | 2.618 |
| AD/XA | 1.27 | 1.27 |

**Key**: 78.6% AB retrace, AD extends beyond X (127%)

### Crab
| Ratio | Min | Max |
|-------|-----|-----|
| AB/XA | 0.382 | 0.618 |
| BC/AB | 0.382 | 0.886 |
| CD/BC | 2.24 | 3.618 |
| AD/XA | 1.618 | 1.618 |

**Key**: Extreme CD extension (224%-361.8%), 161.8% AD/XA

### Deep Crab
| Ratio | Min | Max |
|-------|-----|-----|
| AB/XA | 0.886 | 0.886 |
| BC/AB | 0.382 | 0.886 |
| CD/BC | 2.0 | 3.618 |
| AD/XA | 1.618 | 1.618 |

**Key**: Very deep AB retrace (88.6%), extreme CD

### Cypher
| Ratio | Min | Max |
|-------|-----|-----|
| AB/XA | 0.382 | 0.618 |
| BC/AB | 1.13 | 1.414 |
| CD/BC | 1.27 | 2.0 |
| AD/XA | 0.786 | 0.786 |

**Key**: BC extends beyond A (113%-141.4%), distinct structure

### Shark
| Ratio | Min | Max |
|-------|-----|-----|
| AB/XA | 0.382 | 0.618 |
| BC/AB | 1.13 | 1.618 |
| CD/BC | 1.618 | 2.24 |
| AD/XA | 0.886 | 1.13 |

**Key**: 5-0 pattern variant, D can exceed X

## Detection Process

1. Detect all confirmed pivots using `PivotDetector`
2. Extract all 5-pivot alternating sequences
3. Calculate actual ratios for each sequence
4. Match against all pattern definitions
5. Return matches with measured ratios

## Output Metadata
Each detection includes:
- Exact pivot prices (X, A, B, C, D)
- Measured ratios: `AB_XA_ratio`, `BC_AB_ratio`, `CD_BC_ratio`, `AD_XA_ratio`
- PRZ zone (price range at D)
- Invalidation level (beyond X)
- Target zones (38.2%, 61.8% of XA from D)
- FibonacciRatio objects with expected/actual/within_tolerance

## Confirmation Rules
- All 4 ratios within tolerance
- D pivot confirmed (right bars elapsed)
- PRZ tested (price reaches D zone)

## Invalidation
- Price moves beyond X pivot
- Ratios exceed max tolerance after formation

## Quality Factors
- Ratio precision (closeness to ideal values)
- Pattern symmetry (time/price proportions)
- Volume at D completion
- Confluence with S/R, trendlines, other patterns

## Limitations
- Requires 5 confirmed pivots (significant lookback)
- Tolerance setting critical - too loose = false positives, too strict = misses
- Patterns can overlap/conflict
- PRZ is zone, not exact price
- Timeframe dependent
- Not all harmonic structures in literature implemented