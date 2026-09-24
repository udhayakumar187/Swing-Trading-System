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
    WaveType,
)
from app.patterns.detectors.pivot import PivotDetector, PivotConfig


@dataclass
class WaveConfig:
    pivot_left: int = 5
    pivot_right: int = 5
    min_wave_bars: int = 5
    max_wave_bars: int = 100
    impulse_ratio_min: float = 1.0
    impulse_ratio_max: float = 2.618
    corrective_ratio_min: float = 0.382
    corrective_ratio_max: float = 0.786


class WavePatternDetector(PatternDetector):
    def __init__(self, config: Optional[WaveConfig] = None):
        self.config = config or WaveConfig()
        self.pivot_detector = PivotDetector(PivotConfig(
            left_bars=self.config.pivot_left,
            right_bars=self.config.pivot_right,
        ))

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="WAVE_PATTERNS",
            category=PatternCategory.WAVE,
            description="Wave analysis candidates: impulse, corrective, ABC, Elliott-style",
            required_candles=50,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "pivot_left": self.config.pivot_left,
                "pivot_right": self.config.pivot_right,
                "min_wave_bars": self.config.min_wave_bars,
                "max_wave_bars": self.config.max_wave_bars,
                "impulse_ratio_min": self.config.impulse_ratio_min,
                "impulse_ratio_max": self.config.impulse_ratio_max,
                "corrective_ratio_min": self.config.corrective_ratio_min,
                "corrective_ratio_max": self.config.corrective_ratio_max,
            },
            confirmation_rules=[
                "Wave candidates labeled as WAVE_CANDIDATE only",
                "Rules satisfied/violated explicitly listed",
                "No certainty claims made",
            ],
            invalidation_rules=[
                "Price exceeds wave X origin",
                "Wave structure rules violated",
            ],
            quality_factors=[
                "Number of rules satisfied",
                "Fibonacci ratio adherence",
                "Wave proportion symmetry",
                "Volume profile alignment",
            ],
        )

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        if len(data.candles) < self.definition.required_candles:
            return []

        pivots = self.pivot_detector.detect_pivots(data)
        if len(pivots) < 6:
            return []

        detections = []
        detections.extend(self._detect_impulse_candidates(data, pivots))
        detections.extend(self._detect_corrective_candidates(data, pivots))
        detections.extend(self._detect_abc_corrections(data, pivots))
        detections.extend(self._detect_elliott_impulse(data, pivots))
        return detections

    def _detect_impulse_candidates(self, data: OHLCVData, pivots: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        for i in range(len(pivots) - 5):
            seq = pivots[i:i+6]
            if not self._valid_impulse_structure(seq):
                continue

            rules_sat, rules_viol = self._validate_impulse_rules(seq, data)
            if rules_sat >= 3:
                direction = PatternDirection.BULLISH if seq[0].pivot_type == PivotType.LOW else PatternDirection.BEARISH
                detections.append(self._create_wave_detection(
                    data, seq, WaveType.IMPULSE, direction, rules_sat, rules_viol
                ))
        return detections

    def _detect_corrective_candidates(self, data: OHLCVData, pivots: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        for i in range(len(pivots) - 3):
            seq = pivots[i:i+4]
            if not self._valid_corrective_structure(seq):
                continue

            rules_sat, rules_viol = self._validate_corrective_rules(seq, data)
            if rules_sat >= 2:
                direction = PatternDirection.BULLISH if seq[0].pivot_type == PivotType.HIGH else PatternDirection.BEARISH
                detections.append(self._create_wave_detection(
                    data, seq, WaveType.CORRECTIVE, direction, rules_sat, rules_viol
                ))
        return detections

    def _detect_abc_corrections(self, data: OHLCVData, pivots: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        for i in range(len(pivots) - 3):
            seq = pivots[i:i+4]
            if seq[0].pivot_type == seq[2].pivot_type and seq[1].pivot_type == seq[3].pivot_type:
                if seq[0].pivot_type != seq[1].pivot_type:
                    rules_sat, rules_viol = self._validate_abc_rules(seq, data)
                    if rules_sat >= 2:
                        direction = PatternDirection.BULLISH if seq[0].pivot_type == PivotType.HIGH else PatternDirection.BEARISH
                        detections.append(self._create_wave_detection(
                            data, seq, WaveType.ABC_CORRECTION, direction, rules_sat, rules_viol
                        ))
        return detections

    def _detect_elliott_impulse(self, data: OHLCVData, pivots: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        for i in range(len(pivots) - 8):
            seq = pivots[i:i+9]
            if not self._valid_elliott_structure(seq):
                continue

            rules_sat, rules_viol = self._validate_elliott_rules(seq, data)
            if rules_sat >= 5:
                direction = PatternDirection.BULLISH if seq[0].pivot_type == PivotType.LOW else PatternDirection.BEARISH
                detections.append(self._create_wave_detection(
                    data, seq, WaveType.ELLIOTT_IMPULSE, direction, rules_sat, rules_viol
                ))
        return detections

    def _valid_impulse_structure(self, seq: List[PivotPoint]) -> bool:
        types = [p.pivot_type for p in seq]
        return types == [PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH] or \
               types == [PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW]

    def _valid_corrective_structure(self, seq: List[PivotPoint]) -> bool:
        types = [p.pivot_type for p in seq]
        return types == [PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW] or \
               types == [PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH]

    def _valid_elliott_structure(self, seq: List[PivotPoint]) -> bool:
        types = [p.pivot_type for p in seq]
        return types == [PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW] or \
               types == [PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH, PivotType.LOW, PivotType.HIGH]

    def _validate_impulse_rules(self, seq: List[PivotPoint], data: OHLCVData) -> Tuple[int, List[str]]:
        rules_sat = 0
        rules_viol = []

        w1 = abs(seq[1].price - seq[0].price)
        w2 = abs(seq[2].price - seq[1].price)
        w3 = abs(seq[3].price - seq[2].price)
        w4 = abs(seq[4].price - seq[3].price)
        w5 = abs(seq[5].price - seq[4].price)

        if w2 < w1 * 0.9:
            rules_sat += 1
        else:
            rules_viol.append("Wave 2 retraces >= 90% of Wave 1")

        if w3 > w1 and w3 > w5:
            rules_sat += 1
        else:
            rules_viol.append("Wave 3 not the longest")

        if w4 < w1 * 0.5:
            rules_sat += 1
        else:
            rules_viol.append("Wave 4 overlaps Wave 1 territory")

        if w5 > 0:
            rules_sat += 1
        else:
            rules_viol.append("Wave 5 not extending")

        return rules_sat, rules_viol

    def _validate_corrective_rules(self, seq: List[PivotPoint], data: OHLCVData) -> Tuple[int, List[str]]:
        rules_sat = 0
        rules_viol = []

        a = abs(seq[1].price - seq[0].price)
        b = abs(seq[2].price - seq[1].price)
        c = abs(seq[3].price - seq[2].price)

        if b / a <= self.config.corrective_ratio_max and b / a >= self.config.corrective_ratio_min:
            rules_sat += 1
        else:
            rules_viol.append(f"Wave B retrace {b/a:.2f} outside [{self.config.corrective_ratio_min}, {self.config.corrective_ratio_max}]")

        if c > a * 0.382:
            rules_sat += 1
        else:
            rules_viol.append("Wave C too short")

        return rules_sat, rules_viol

    def _validate_abc_rules(self, seq: List[PivotPoint], data: OHLCVData) -> Tuple[int, List[str]]:
        rules_sat = 0
        rules_viol = []

        a = abs(seq[1].price - seq[0].price)
        b = abs(seq[2].price - seq[1].price)
        c = abs(seq[3].price - seq[2].price)

        if 0.382 <= b / a <= 0.786:
            rules_sat += 1
        else:
            rules_viol.append(f"Wave B retrace {b/a:.2f} not in [0.382, 0.786]")

        if 1.0 <= c / a <= 1.618:
            rules_sat += 1
        else:
            rules_viol.append(f"Wave C length {c/a:.2f} not in [1.0, 1.618] of Wave A")

        return rules_sat, rules_viol

    def _validate_elliott_rules(self, seq: List[PivotPoint], data: OHLCVData) -> Tuple[int, List[str]]:
        rules_sat = 0
        rules_viol = []

        w1 = abs(seq[1].price - seq[0].price)
        w2 = abs(seq[2].price - seq[1].price)
        w3 = abs(seq[3].price - seq[2].price)
        w4 = abs(seq[4].price - seq[3].price)
        w5 = abs(seq[5].price - seq[4].price)

        if w2 < w1:
            rules_sat += 1
        else:
            rules_viol.append("Wave 2 retraces 100%+ of Wave 1")

        if w3 > w1 and w3 > w5:
            rules_sat += 1
        else:
            rules_viol.append("Wave 3 not longest")

        if w4 < w1 * 0.382:
            rules_sat += 1
        else:
            rules_viol.append("Wave 4 overlaps Wave 1")

        if w5 > 0 and w5 < w3 * 1.618:
            rules_sat += 1
        else:
            rules_viol.append("Wave 5 extension invalid")

        a_wave = abs(seq[6].price - seq[5].price)
        b_wave = abs(seq[7].price - seq[6].price)
        c_wave = abs(seq[8].price - seq[7].price)

        if 0.382 <= b_wave / a_wave <= 0.786:
            rules_sat += 1
        else:
            rules_viol.append("Corrective B wave retrace invalid")

        if 1.0 <= c_wave / a_wave <= 1.618:
            rules_sat += 1
        else:
            rules_viol.append("Corrective C wave length invalid")

        return rules_sat, rules_viol

    def _create_wave_detection(
        self,
        data: OHLCVData,
        seq: List[PivotPoint],
        wave_type: WaveType,
        direction: PatternDirection,
        rules_sat: int,
        rules_viol: List[str],
    ) -> PatternDetection:
        from datetime import datetime

        total_rules = rules_sat + len(rules_viol)
        quality = int((rules_sat / total_rules) * 100) if total_rules > 0 else 50

        start_pivot = seq[0]
        end_pivot = seq[-1]

        if direction == PatternDirection.BULLISH:
            invalidation = start_pivot.price * 0.99
        else:
            invalidation = start_pivot.price * 1.01

        return PatternDetection(
            symbol=data.symbol,
            timeframe=data.timeframe,
            pattern_name=f"WAVE_CANDIDATE_{wave_type.value}",
            pattern_category=self.get_category(),
            direction=direction,
            status=PatternStatus.FORMING,
            start_timestamp=start_pivot.timestamp,
            confirmation_timestamp=None,
            completion_timestamp=end_pivot.timestamp,
            detection_timestamp=datetime.utcnow(),
            price_levels={f"pivot_{i}": p.price for i, p in enumerate(seq)},
            invalidation_level=invalidation,
            quality_score=quality,
            metadata={
                "wave_type": wave_type.value,
                "rules_satisfied": rules_sat,
                "rules_violated": rules_viol,
                "pivot_count": len(seq),
                "pivot_indices": [p.index for p in seq],
            },
            explanation=[
                f"Wave candidate: {wave_type.value}",
                f"Rules satisfied: {rules_sat}/{total_rules}",
                f"Violations: {'; '.join(rules_viol) if rules_viol else 'None'}",
                "NOTE: This is a wave candidate, not a guaranteed wave count",
            ],
            pivots=seq,
        )


def register_wave_patterns(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(WavePatternDetector())