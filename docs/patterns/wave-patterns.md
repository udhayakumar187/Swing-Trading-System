# Wave Patterns Documentation

## Overview
Wave analysis framework providing **candidates only** - never guaranteed wave counts. Every detection labeled `WAVE_CANDIDATE` with explicit rules satisfied/violated.

## Philosophy
Wave analysis (especially Elliott Wave) is inherently subjective. This engine:
- Does NOT claim certainty
- Generates candidates from pivot sequences
- Validates against objective rules
- Reports rules satisfied AND violated
- Provides quality metric based on rule adherence

## Pivot Sequence Foundation
All wave analysis uses confirmed pivots from `PivotDetector`:
- `left_bars=5`, `right_bars=5` (configurable)
- Only confirmed pivots for live detection
- Sequence: alternating high/low pivots

## Wave Candidate Types

### Impulse Wave Candidate (5-wave)
**Structure**: 5 pivots = 3 impulse + 2 corrective
- Pivots: Low-High-Low-High-Low (bullish) or High-Low-High-Low-High (bearish)
- Waves: 1, 2, 3, 4, 5

**Rules (Elliott-based)**:
1. Wave 2 retraces < 100% of Wave 1
2. Wave 3 not shortest (typically longest)
3. Wave 4 does not overlap Wave 1 territory
4. Wave 5 extends (typically)
5. Alternation: Wave 2 & 4 different character

**Validation**:
- Measures each rule pass/fail
- Quality = rules_satisfied / total_rules * 100
- Status: FORMING (never CONFIRMED)

### Corrective Wave Candidate (3-wave)
**Structure**: 3 pivots = A-B-C
- Zigzag, flat, or triangle variants
- Simpler validation

**Rules**:
1. Wave B retrace 38.2%-78.6% of Wave A
2. Wave C extends beyond Wave A end
3. Wave C typically 100%-161.8% of Wave A

### ABC Correction Candidate
- Specific 3-wave corrective structure
- Same rules as corrective above
- Labeled separately for clarity

### Elliott Impulse Candidate (9-pivot / 5+4)
**Structure**: 5-wave impulse + 3-wave correction = 8 waves, 9 pivots
- Complete cycle candidate
- Validates both impulse and corrective phases

**Additional Rules**:
- Corrective phase: A-B-C structure
- Wave B retrace 38.2%-78.6% of A
- Wave C length 100%-161.8% of A

## Output Format
Every wave candidate includes:
```json
{
  "pattern_name": "WAVE_CANDIDATE_IMPULSE",
  "direction": "BULLISH|BEARISH",
  "status": "FORMING",
  "pivots": [...],
  "metadata": {
    "wave_type": "IMPULSE|CORRECTIVE|ABC_CORRECTION|ELLIOTT_IMPULSE",
    "rules_satisfied": 4,
    "rules_violated": ["Wave 4 overlaps Wave 1"],
    "pivot_count": 6,
    "pivot_indices": [10, 15, 22, 28, 35, 42]
  },
  "explanation": [
    "Wave candidate: IMPULSE",
    "Rules satisfied: 4/5",
    "Violations: Wave 4 overlaps Wave 1",
    "NOTE: This is a wave candidate, not a guaranteed wave count"
  ]
}
```

## Invalidation Levels
- Impulse: Beyond Wave 1 origin (X point)
- Corrective: Beyond Wave A origin
- Explicitly provided per candidate

## Quality Metric
```
quality = (rules_satisfied / total_rules) * 100
```
- 100 = all rules satisfied
- < 50 = more violations than satisfied
- Not a probability

## Confirmation Rules
- Wave candidates never "confirmed" automatically
- Require subsequent price action validation
- Used as framework for analysis, not signals

## Limitations
- **HIGHLY SUBJECTIVE** - Multiple valid wave counts often exist
- Pivot selection affects entire count
- No probabilistic interpretation
- Best used with other confirmation
- Timeframe dependent
- Real-time lag (pivot confirmation delay)
- Not suitable for automated trading alone