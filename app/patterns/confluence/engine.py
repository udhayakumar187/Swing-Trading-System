from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.patterns.models import (
    PatternDetection,
    ConfluencePattern,
    ConfluenceResult,
    PatternCategory,
    PatternDirection,
    MarketRegime,
    OHLCVData,
)
from app.patterns.registry import PatternRegistry


@dataclass
class ConfluenceConfig:
    weights: Dict[str, float] = None
    min_patterns: int = 2
    min_score: int = 50

    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                "CANDLESTICK": 1.0,
                "CHART_PATTERN": 1.5,
                "HARMONIC": 1.5,
                "MARKET_STRUCTURE": 1.2,
                "INDICATOR_PATTERN": 1.0,
                "WAVE": 0.8,
                "VOLUME": 1.0,
                "VOLATILITY": 0.8,
            }


class ConfluenceEngine:
    def __init__(self, config: Optional[ConfluenceConfig] = None):
        self.config = config or ConfluenceConfig()

    def analyze(
        self,
        detections: List[PatternDetection],
        market_regime: Optional[MarketRegime] = None,
    ) -> ConfluenceResult:
        if not detections:
            return ConfluenceResult(
                symbol="",
                timeframe=detections[0].timeframe if detections else None,
                patterns=[],
                technical_confluence_score=0,
                explanation=["No patterns detected"],
                market_regime=market_regime,
            )

        symbol = detections[0].symbol
        timeframe = detections[0].timeframe

        bullish_patterns = []
        bearish_patterns = []

        for det in detections:
            weight = self.config.weights.get(det.pattern_category.value, 1.0)
            quality = det.quality_score or 50
            weighted_score = quality * weight

            conf_pattern = ConfluencePattern(
                pattern_name=det.pattern_name,
                category=det.pattern_category,
                direction=det.direction,
                quality_score=quality,
                weight=weight,
            )

            if det.direction == PatternDirection.BULLISH:
                bullish_patterns.append((conf_pattern, weighted_score))
            elif det.direction == PatternDirection.BEARISH:
                bearish_patterns.append((conf_pattern, weighted_score))

        bullish_score = sum(s for _, s in bullish_patterns)
        bearish_score = sum(s for _, s in bearish_patterns)

        total_weight = sum(w for _, w in bullish_patterns) + sum(w for _, w in bearish_patterns)
        if total_weight > 0:
            net_score = (bullish_score - bearish_score) / total_weight * 100 + 50
        else:
            net_score = 50

        net_score = max(0, min(100, int(net_score)))

        dominant = "BULLISH" if bullish_score > bearish_score else "BEARISH" if bearish_score > bullish_score else "NEUTRAL"
        dominant_patterns = bullish_patterns if dominant == "BULLISH" else bearish_patterns

        explanation = [
            f"Confluence analysis: {len(detections)} patterns detected",
            f"Bullish patterns: {len(bullish_patterns)}, Bearish patterns: {len(bearish_patterns)}",
            f"Dominant bias: {dominant} (score: {net_score})",
        ]

        for pat, score in sorted(dominant_patterns, key=lambda x: x[1], reverse=True)[:5]:
            explanation.append(f"  - {pat.pattern_name} ({pat.category.value}): quality={pat.quality_score}, weight={pat.weight:.1f}")

        if market_regime:
            regime_bonus = 0
            if market_regime == MarketRegime.BULL_TREND and dominant == "BULLISH":
                regime_bonus = 5
            elif market_regime == MarketRegime.BEAR_TREND and dominant == "BEARISH":
                regime_bonus = 5
            elif market_regime == MarketRegime.RANGE:
                regime_bonus = -5
            net_score = max(0, min(100, net_score + regime_bonus))
            explanation.append(f"Market regime: {market_regime.value} (adjusted score: {net_score})")

        return ConfluenceResult(
            symbol=symbol,
            timeframe=timeframe,
            patterns=[p for p, _ in bullish_patterns + bearish_patterns],
            technical_confluence_score=net_score,
            explanation=explanation,
            market_regime=market_regime,
            timestamp=datetime.utcnow(),
        )


def calculate_confluence(
    detections: List[PatternDetection],
    config: Optional[ConfluenceConfig] = None,
    market_regime: Optional[MarketRegime] = None,
) -> ConfluenceResult:
    engine = ConfluenceEngine(config)
    return engine.analyze(detections, market_regime)