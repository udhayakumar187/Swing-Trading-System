from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np

from app.patterns.detectors.base import PatternDetector, DetectorContext
from app.patterns.models import (
    PatternDefinition,
    PatternDetection,
    PatternCategory,
    PatternDirection,
    PatternStatus,
    OHLCVData,
    PivotPoint,
    PivotType,
    MarketRegime,
)
from app.patterns.detectors.pivot import PivotDetector, PivotConfig


@dataclass
class MarketStructureConfig:
    pivot_left: int = 5
    pivot_right: int = 5
    min_swing_bars: int = 3
    breakout_threshold: float = 0.005
    retest_tolerance: float = 0.003
    trend_min_swings: int = 3
    range_threshold: float = 0.05
    volume_confirmation: bool = True


class MarketStructureDetector(PatternDetector):
    def __init__(self, config: Optional[MarketStructureConfig] = None):
        self.config = config or MarketStructureConfig()
        self.pivot_detector = PivotDetector(PivotConfig(
            left_bars=self.config.pivot_left,
            right_bars=self.config.pivot_right,
        ))

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="MARKET_STRUCTURE",
            category=PatternCategory.MARKET_STRUCTURE,
            description="Market structure analysis: trends, swings, BOS, CHOCH, support/resistance",
            required_candles=50,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "pivot_left": self.config.pivot_left,
                "pivot_right": self.config.pivot_right,
                "min_swing_bars": self.config.min_swing_bars,
                "breakout_threshold": self.config.breakout_threshold,
                "retest_tolerance": self.config.retest_tolerance,
                "trend_min_swings": self.config.trend_min_swings,
                "range_threshold": self.config.range_threshold,
            },
            confirmation_rules=[
                "Swing points must be confirmed pivots",
                "Breakouts require close beyond level",
                "Retests must hold within tolerance",
            ],
            invalidation_rules=[
                "Price closes back beyond broken level",
                "Structure fails to make new swing",
            ],
            quality_factors=[
                "Number of confirming swings",
                "Volume on breakout",
                "Time at level",
                "Multiple timeframe alignment",
            ],
        )

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        if len(data.candles) < self.definition.required_candles:
            return []

        pivots = self.pivot_detector.detect_pivots(data)
        pivot_highs = self.pivot_detector.get_pivot_highs(pivots)
        pivot_lows = self.pivot_detector.get_pivot_lows(pivots)

        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return []

        detections = []

        detections.extend(self._detect_swings(data, pivot_highs, pivot_lows))
        detections.extend(self._detect_trends(data, pivot_highs, pivot_lows))
        detections.extend(self._detect_bos_choch(data, pivot_highs, pivot_lows))
        detections.extend(self._detect_support_resistance(data, pivot_highs, pivot_lows))
        detections.extend(self._detect_breakouts(data, pivot_highs, pivot_lows))
        detections.extend(self._detect_liquidity_sweeps(data, pivot_highs, pivot_lows))
        detections.extend(self._detect_swing_failure(data, pivot_highs, pivot_lows))

        return detections

    def _detect_swings(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) >= 2 and len(lows) >= 2:
            last_high = highs[-1]
            prev_high = highs[-2]
            last_low = lows[-1]
            prev_low = lows[-2]

            if last_high.price > prev_high.price:
                detections.append(self._create_detection(
                    data, prev_high.index, last_high.index,
                    "HIGHER_HIGH", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"swing_high": last_high.price, "prev_swing_high": prev_high.price},
                    explanation=[f"Higher high formed: {last_high.price:.2f} > {prev_high.price:.2f}"]
                ))

            if last_low.price > prev_low.price:
                detections.append(self._create_detection(
                    data, prev_low.index, last_low.index,
                    "HIGHER_LOW", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"swing_low": last_low.price, "prev_swing_low": prev_low.price},
                    explanation=[f"Higher low formed: {last_low.price:.2f} > {prev_low.price:.2f}"]
                ))

            if last_high.price < prev_high.price:
                detections.append(self._create_detection(
                    data, prev_high.index, last_high.index,
                    "LOWER_HIGH", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"swing_high": last_high.price, "prev_swing_high": prev_high.price},
                    explanation=[f"Lower high formed: {last_high.price:.2f} < {prev_high.price:.2f}"]
                ))

            if last_low.price < prev_low.price:
                detections.append(self._create_detection(
                    data, prev_low.index, last_low.index,
                    "LOWER_LOW", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"swing_low": last_low.price, "prev_swing_low": prev_low.price},
                    explanation=[f"Lower low formed: {last_low.price:.2f} < {prev_low.price:.2f}"]
                ))

        return detections

    def _detect_trends(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        min_swings = self.config.trend_min_swings

        if len(highs) >= min_swings and len(lows) >= min_swings:
            recent_highs = [h.price for h in highs[-min_swings:]]
            recent_lows = [l.price for l in lows[-min_swings:]]

            hh = all(recent_highs[i] > recent_highs[i-1] for i in range(1, len(recent_highs)))
            hl = all(recent_lows[i] > recent_lows[i-1] for i in range(1, len(recent_lows)))

            if hh and hl:
                detections.append(self._create_detection(
                    data, lows[-min_swings].index, len(data.candles) - 1,
                    "UPTREND", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"trend_start": lows[-min_swings].price, "current_high": highs[-1].price, "swing_count": min_swings},
                    explanation=[f"Uptrend confirmed: {min_swings} consecutive higher highs and higher lows"]
                ))

            lh = all(recent_highs[i] < recent_highs[i-1] for i in range(1, len(recent_highs)))
            ll = all(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows)))

            if lh and ll:
                detections.append(self._create_detection(
                    data, highs[-min_swings].index, len(data.candles) - 1,
                    "DOWNTREND", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"trend_start": highs[-min_swings].price, "current_low": lows[-1].price, "swing_count": min_swings},
                    explanation=[f"Downtrend confirmed: {min_swings} consecutive lower highs and lower lows"]
                ))

        if len(highs) >= 3 and len(lows) >= 3:
            high_range = max(h.price for h in highs[-3:]) - min(h.price for h in highs[-3:])
            low_range = max(l.price for l in lows[-3:]) - min(l.price for l in lows[-3:])
            avg_price = (highs[-1].price + lows[-1].price) / 2

            if high_range / avg_price < self.config.range_threshold and low_range / avg_price < self.config.range_threshold:
                detections.append(self._create_detection(
                    data, min(highs[-3].index, lows[-3].index), len(data.candles) - 1,
                    "RANGING", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                    {"range_high": max(h.price for h in highs[-3:]), "range_low": min(l.price for l in lows[-3:])},
                    explanation=[f"Price ranging: highs within {high_range/avg_price:.1%}, lows within {low_range/avg_price:.1%}"]
                ))

        return detections

    def _detect_bos_choch(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 2 or len(lows) < 2:
            return detections

        last_close = data.candles[-1].close

        if len(highs) >= 2:
            prev_high = highs[-2]
            last_high = highs[-1]
            if last_close > prev_high.price * (1 + self.config.breakout_threshold):
                if len(lows) >= 2 and lows[-1].price > lows[-2].price:
                    detections.append(self._create_detection(
                        data, prev_high.index, len(data.candles) - 1,
                        "BREAK_OF_STRUCTURE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                        {"broken_level": prev_high.price, "close": last_close},
                        invalidation_level=prev_high.price,
                        metadata={"type": "BOS"},
                        explanation=[f"BOS Bullish: Close {last_close:.2f} broke above prior swing high {prev_high.price:.2f}", "Higher low intact"]
                    ))
                else:
                    detections.append(self._create_detection(
                        data, prev_high.index, len(data.candles) - 1,
                        "CHANGE_OF_CHARACTER", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                        {"broken_level": prev_high.price, "close": last_close},
                        invalidation_level=prev_high.price,
                        metadata={"type": "CHOCH"},
                        explanation=[f"CHoCH Bullish: Close {last_close:.2f} broke above prior swing high {prev_high.price:.2f}", "Lower low was in place - trend change signal"]
                    ))

        if len(lows) >= 2:
            prev_low = lows[-2]
            last_low = lows[-1]
            if last_close < prev_low.price * (1 - self.config.breakout_threshold):
                if len(highs) >= 2 and highs[-1].price < highs[-2].price:
                    detections.append(self._create_detection(
                        data, prev_low.index, len(data.candles) - 1,
                        "BREAK_OF_STRUCTURE", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                        {"broken_level": prev_low.price, "close": last_close},
                        invalidation_level=prev_low.price,
                        metadata={"type": "BOS"},
                        explanation=[f"BOS Bearish: Close {last_close:.2f} broke below prior swing low {prev_low.price:.2f}", "Lower high intact"]
                    ))
                else:
                    detections.append(self._create_detection(
                        data, prev_low.index, len(data.candles) - 1,
                        "CHANGE_OF_CHARACTER", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                        {"broken_level": prev_low.price, "close": last_close},
                        invalidation_level=prev_low.price,
                        metadata={"type": "CHOCH"},
                        explanation=[f"CHoCH Bearish: Close {last_close:.2f} broke below prior swing low {prev_low.price:.2f}", "Higher high was in place - trend change signal"]
                    ))

        return detections

    def _detect_support_resistance(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        current_price = data.candles[-1].close

        for pivot in highs[-5:]:
            if pivot.confirmed:
                touches = sum(1 for h in highs if abs(h.price - pivot.price) / pivot.price < 0.01)
                if touches >= 2:
                    dist = (pivot.price - current_price) / current_price
                    if 0 < dist < 0.05:
                        detections.append(self._create_detection(
                            data, pivot.index, len(data.candles) - 1,
                            "RESISTANCE", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                            {"level": pivot.price, "touches": touches, "distance_pct": dist * 100},
                            explanation=[f"Resistance at {pivot.price:.2f} tested {touches} times", f"Current price {dist*100:.1f}% below"]
                        ))

        for pivot in lows[-5:]:
            if pivot.confirmed:
                touches = sum(1 for l in lows if abs(l.price - pivot.price) / pivot.price < 0.01)
                if touches >= 2:
                    dist = (current_price - pivot.price) / current_price
                    if 0 < dist < 0.05:
                        detections.append(self._create_detection(
                            data, pivot.index, len(data.candles) - 1,
                            "SUPPORT", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                            {"level": pivot.price, "touches": touches, "distance_pct": dist * 100},
                            explanation=[f"Support at {pivot.price:.2f} tested {touches} times", f"Current price {dist*100:.1f}% above"]
                        ))

        return detections

    def _detect_breakouts(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(data.candles) < 2:
            return detections

        current = data.candles[-1]
        prev = data.candles[-2]

        for pivot in highs[-3:]:
            if pivot.confirmed and prev.close <= pivot.price and current.close > pivot.price * (1 + self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, pivot.index, len(data.candles) - 1,
                    "RESISTANCE_BREAK", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"broken_level": pivot.price, "breakout_close": current.close, "volume": current.volume},
                    invalidation_level=pivot.price,
                    target_levels={"target": pivot.price + (pivot.price - min(l.price for l in lows[-3:])) if lows else None},
                    volume_confirmation=current.volume > prev.volume * 1.2,
                    explanation=[f"Resistance breakout: Close {current.close:.2f} > {pivot.price:.2f}"]
                ))

        for pivot in lows[-3:]:
            if pivot.confirmed and prev.close >= pivot.price and current.close < pivot.price * (1 - self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, pivot.index, len(data.candles) - 1,
                    "SUPPORT_BREAK", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"broken_level": pivot.price, "breakout_close": current.close, "volume": current.volume},
                    invalidation_level=pivot.price,
                    target_levels={"target": pivot.price - (max(h.price for h in highs[-3:]) - pivot.price) if highs else None},
                    volume_confirmation=current.volume > prev.volume * 1.2,
                    explanation=[f"Support breakdown: Close {current.close:.2f} < {pivot.price:.2f}"]
                ))

        return detections

    def _detect_liquidity_sweeps(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(data.candles) < 2:
            return detections

        current = data.candles[-1]

        for pivot in highs[-3:]:
            if pivot.confirmed and current.high > pivot.price and current.close < pivot.price:
                detections.append(self._create_detection(
                    data, pivot.index, len(data.candles) - 1,
                    "LIQUIDITY_SWEEP_HIGH", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"swept_level": pivot.price, "high": current.high, "close": current.close},
                    explanation=[f"Liquidity sweep above {pivot.price:.2f}: High {current.high:.2f}, Close {current.close:.2f}", "Stop hunt / liquidity grab"]
                ))

        for pivot in lows[-3:]:
            if pivot.confirmed and current.low < pivot.price and current.close > pivot.price:
                detections.append(self._create_detection(
                    data, pivot.index, len(data.candles) - 1,
                    "LIQUIDITY_SWEEP_LOW", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"swept_level": pivot.price, "low": current.low, "close": current.close},
                    explanation=[f"Liquidity sweep below {pivot.price:.2f}: Low {current.low:.2f}, Close {current.close:.2f}", "Stop hunt / liquidity grab"]
                ))

        return detections

    def _detect_swing_failure(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 2 or len(lows) < 2:
            return detections

        last_high = highs[-1]
        prev_high = highs[-2]
        last_low = lows[-1]
        prev_low = lows[-2]

        if last_high.price > prev_high.price:
            if last_low.price < prev_low.price:
                detections.append(self._create_detection(
                    data, prev_high.index, len(data.candles) - 1,
                    "SWING_FAILURE_BEARISH", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"failed_high": last_high.price, "prev_high": prev_high.price, "break_low": last_low.price},
                    explanation=[f"Swing failure: Higher high {last_high.price:.2f} followed by lower low {last_low.price:.2f}", "Bearish reversal pattern"]
                ))

        if last_low.price < prev_low.price:
            if last_high.price > prev_high.price:
                detections.append(self._create_detection(
                    data, prev_low.index, len(data.candles) - 1,
                    "SWING_FAILURE_BULLISH", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"failed_low": last_low.price, "prev_low": prev_low.price, "break_high": last_high.price},
                    explanation=[f"Swing failure: Lower low {last_low.price:.2f} followed by higher high {last_high.price:.2f}", "Bullish reversal pattern"]
                ))

        return detections

    def _create_detection(
        self,
        data: OHLCVData,
        start_idx: int,
        end_idx: int,
        pattern_name: str,
        direction: PatternDirection,
        status: PatternStatus,
        price_levels: Dict[str, float],
        invalidation_level: Optional[float] = None,
        target_levels: Optional[Dict[str, float]] = None,
        quality_score: Optional[int] = None,
        volume_confirmation: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        explanation: Optional[List[str]] = None,
    ) -> PatternDetection:
        from datetime import datetime

        start_ts = data.candles[max(0, start_idx)].timestamp
        detection_ts = datetime.utcnow()
        completion_ts = data.candles[end_idx].timestamp if end_idx < len(data.candles) else None

        return PatternDetection(
            symbol=data.symbol,
            timeframe=data.timeframe,
            pattern_name=pattern_name,
            pattern_category=self.get_category(),
            direction=direction,
            status=status,
            start_timestamp=start_ts,
            confirmation_timestamp=start_ts if status == PatternStatus.CONFIRMED else None,
            completion_timestamp=completion_ts,
            detection_timestamp=detection_ts,
            price_levels=price_levels,
            invalidation_level=invalidation_level,
            target_levels=target_levels or {},
            quality_score=quality_score,
            volume_confirmation=volume_confirmation,
            metadata=metadata or {},
            explanation=explanation or [],
        )


def register_market_structure(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(MarketStructureDetector())