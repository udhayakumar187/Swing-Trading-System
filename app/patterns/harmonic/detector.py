from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
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
    FibonacciRatio,
)
from app.patterns.detectors.pivot import PivotDetector, PivotConfig


@dataclass
class HarmonicConfig:
    pivot_left: int = 5
    pivot_right: int = 5
    ratio_tolerance: float = 0.05
    min_pattern_bars: int = 10
    max_pattern_bars: int = 100


HARMONIC_RATIOS = {
    "GARTLEY": {
        "AB_XA": (0.618, 0.618),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (1.13, 1.618),
        "AD_XA": (0.786, 0.786),
    },
    "BAT": {
        "AB_XA": (0.382, 0.5),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (1.618, 2.618),
        "AD_XA": (0.886, 0.886),
    },
    "BUTTERFLY": {
        "AB_XA": (0.786, 0.786),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (1.618, 2.618),
        "AD_XA": (1.27, 1.27),
    },
    "CRAB": {
        "AB_XA": (0.382, 0.618),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (2.24, 3.618),
        "AD_XA": (1.618, 1.618),
    },
    "DEEP_CRAB": {
        "AB_XA": (0.886, 0.886),
        "BC_AB": (0.382, 0.886),
        "CD_BC": (2.0, 3.618),
        "AD_XA": (1.618, 1.618),
    },
    "CYPHER": {
        "AB_XA": (0.382, 0.618),
        "BC_AB": (1.13, 1.414),
        "CD_BC": (1.27, 2.0),
        "AD_XA": (0.786, 0.786),
    },
    "SHARK": {
        "AB_XA": (0.382, 0.618),
        "BC_AB": (1.13, 1.618),
        "CD_BC": (1.618, 2.24),
        "AD_XA": (0.886, 1.13),
    },
}


class HarmonicPatternDetector(PatternDetector):
    def __init__(self, config: Optional[HarmonicConfig] = None):
        self.config = config or HarmonicConfig()
        self.pivot_detector = PivotDetector(PivotConfig(
            left_bars=self.config.pivot_left,
            right_bars=self.config.pivot_right,
        ))

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="HARMONIC_PATTERNS",
            category=PatternCategory.HARMONIC,
            description="Harmonic patterns: Gartley, Bat, Butterfly, Crab, Deep Crab, Cypher, Shark",
            required_candles=50,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "pivot_left": self.config.pivot_left,
                "pivot_right": self.config.pivot_right,
                "ratio_tolerance": self.config.ratio_tolerance,
                "patterns": {k: {"ratios": v} for k, v in HARMONIC_RATIOS.items()},
            },
            confirmation_rules=[
                "All Fibonacci ratios must be within tolerance",
                "Pattern must complete at point D",
                "PRZ (Potential Reversal Zone) must be tested",
            ],
            invalidation_rules=[
                "Price moves beyond point X",
                "Ratios exceed maximum tolerance",
            ],
            quality_factors=[
                "Ratio precision",
                "Pattern symmetry",
                "Volume at completion",
                "Confluence with other levels",
            ],
        )

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        if len(data.candles) < self.definition.required_candles:
            return []

        pivots = self.pivot_detector.detect_pivots(data)
        if len(pivots) < 5:
            return []

        detections = []
        self._find_harmonic_patterns(data, pivots, detections)
        return detections

    def _find_harmonic_patterns(self, data: OHLCVData, pivots: List[PivotPoint], detections: List[PatternDetection]):
        for i in range(len(pivots) - 4):
            sequence = pivots[i:i+5]
            if not self._valid_alternating_sequence(sequence):
                continue

            X, A, B, C, D = sequence
            if D.index >= len(data.candles) - 1:
                continue

            ratios = self._calculate_ratios(X, A, B, C, D)
            if ratios is None:
                continue

            for pattern_name, expected in HARMONIC_RATIOS.items():
                if self._matches_pattern(ratios, expected):
                    direction = PatternDirection.BULLISH if D.pivot_type == PivotType.LOW else PatternDirection.BEARISH
                    detections.append(self._create_harmonic_detection(
                        data, pattern_name, X, A, B, C, D, ratios, direction, expected
                    ))

    def _valid_alternating_sequence(self, pivots: List[PivotPoint]) -> bool:
        for i in range(1, len(pivots)):
            if pivots[i].pivot_type == pivots[i-1].pivot_type:
                return False
        return True

    def _calculate_ratios(self, X: PivotPoint, A: PivotPoint, B: PivotPoint, C: PivotPoint, D: PivotPoint) -> Optional[Dict[str, float]]:
        XA = abs(A.price - X.price)
        if XA == 0:
            return None

        AB = abs(B.price - A.price)
        BC = abs(C.price - B.price)
        CD = abs(D.price - C.price)
        AD = abs(D.price - X.price)

        return {
            "AB_XA": AB / XA,
            "BC_AB": BC / AB if AB > 0 else 0,
            "CD_BC": CD / BC if BC > 0 else 0,
            "AD_XA": AD / XA,
            "XA_price": XA,
            "X_price": X.price,
            "A_price": A.price,
            "B_price": B.price,
            "C_price": C.price,
            "D_price": D.price,
        }

    def _matches_pattern(self, actual: Dict[str, float], expected: Dict[str, Tuple[float, float]]) -> bool:
        for ratio_name, (exp_min, exp_max) in expected.items():
            if ratio_name not in actual:
                return False
            act_val = actual[ratio_name]
            tol = self.config.ratio_tolerance
            if not (exp_min * (1 - tol) <= act_val <= exp_max * (1 + tol)):
                return False
        return True

    def _create_harmonic_detection(
        self,
        data: OHLCVData,
        pattern_name: str,
        X: PivotPoint,
        A: PivotPoint,
        B: PivotPoint,
        C: PivotPoint,
        D: PivotPoint,
        ratios: Dict[str, float],
        direction: PatternDirection,
        expected: Dict[str, Tuple[float, float]],
    ) -> PatternDetection:
        from datetime import datetime

        XA = ratios["XA_price"]
        D_price = ratios["D_price"]
        A_price = ratios["A_price"]
        C_price = ratios["C_price"]

        if direction == PatternDirection.BULLISH:
            prz_low = D_price
            prz_high = D_price + XA * 0.1
            invalidation = X.price * 0.99
            target_1 = D_price + XA * 0.382
            target_2 = D_price + XA * 0.618
        else:
            prz_low = D_price - XA * 0.1
            prz_high = D_price
            invalidation = X.price * 1.01
            target_1 = D_price - XA * 0.382
            target_2 = D_price - XA * 0.618

        fib_ratios = [
            FibonacciRatio(name="AB/XA", expected_min=expected["AB_XA"][0], expected_max=expected["AB_XA"][1], actual=ratios["AB_XA"], within_tolerance=True),
            FibonacciRatio(name="BC/AB", expected_min=expected["BC_AB"][0], expected_max=expected["BC_AB"][1], actual=ratios["BC_AB"], within_tolerance=True),
            FibonacciRatio(name="CD/BC", expected_min=expected["CD_BC"][0], expected_max=expected["CD_BC"][1], actual=ratios["CD_BC"], within_tolerance=True),
            FibonacciRatio(name="AD/XA", expected_min=expected["AD_XA"][0], expected_max=expected["AD_XA"][1], actual=ratios["AD_XA"], within_tolerance=True),
        ]

        quality = self._calculate_quality(ratios, expected)

        return PatternDetection(
            symbol=data.symbol,
            timeframe=data.timeframe,
            pattern_name=pattern_name,
            pattern_category=self.get_category(),
            direction=direction,
            status=PatternStatus.CONFIRMED,
            start_timestamp=X.timestamp,
            confirmation_timestamp=D.timestamp,
            completion_timestamp=D.timestamp,
            detection_timestamp=datetime.utcnow(),
            price_levels={
                "X": X.price, "A": A.price, "B": B.price, "C": C.price, "D": D.price,
                "PRZ_low": prz_low, "PRZ_high": prz_high,
            },
            invalidation_level=invalidation,
            target_levels={"target_1": target_1, "target_2": target_2},
            quality_score=quality,
            metadata={
                "ratios": ratios,
                "pivot_indices": {"X": X.index, "A": A.index, "B": B.index, "C": C.index, "D": D.index},
            },
            explanation=[
                f"{pattern_name} harmonic pattern detected",
                f"X={X.price:.2f}, A={A.price:.2f}, B={B.price:.2f}, C={C.price:.2f}, D={D.price:.2f}",
                f"Ratios: AB/XA={ratios['AB_XA']:.3f}, BC/AB={ratios['BC_AB']:.3f}, CD/BC={ratios['CD_BC']:.3f}, AD/XA={ratios['AD_XA']:.3f}",
            ],
            pivots=[X, A, B, C, D],
            fibonacci_ratios=fib_ratios,
        )

    def _calculate_quality(self, actual: Dict[str, float], expected: Dict[str, Tuple[float, float]]) -> int:
        score = 100
        for ratio_name, (exp_min, exp_max) in expected.items():
            if ratio_name in actual:
                act = actual[ratio_name]
                exp_mid = (exp_min + exp_max) / 2
                deviation = abs(act - exp_mid) / exp_mid
                score -= min(20, int(deviation * 100))
        return max(0, score)


def register_harmonic_patterns(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(HarmonicPatternDetector())