from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np

from app.patterns.models import PivotPoint, PivotType, OHLCVData


@dataclass
class PivotConfig:
    left_bars: int = 5
    right_bars: int = 5
    min_pivot_distance: float = 0.0


class PivotDetector:
    def __init__(self, config: Optional[PivotConfig] = None):
        self.config = config or PivotConfig()

    def detect_pivots(self, data: OHLCVData) -> List[PivotPoint]:
        if len(data.candles) < self.config.left_bars + self.config.right_bars + 1:
            return []

        highs = np.array([c.high for c in data.candles])
        lows = np.array([c.low for c in data.candles])
        timestamps = [c.timestamp for c in data.candles]

        pivots = []

        for i in range(self.config.left_bars, len(data.candles) - self.config.right_bars):
            is_pivot_high = True
            is_pivot_low = True

            current_high = highs[i]
            current_low = lows[i]

            for j in range(1, self.config.left_bars + 1):
                if highs[i - j] >= current_high:
                    is_pivot_high = False
                if lows[i - j] <= current_low:
                    is_pivot_low = False

            for j in range(1, self.config.right_bars + 1):
                if highs[i + j] > current_high:
                    is_pivot_high = False
                if lows[i + j] < current_low:
                    is_pivot_low = False

            if is_pivot_high:
                pivots.append(PivotPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=current_high,
                    pivot_type=PivotType.HIGH,
                    left_bars=self.config.left_bars,
                    right_bars=self.config.right_bars,
                    confirmed=True,
                ))

            if is_pivot_low:
                pivots.append(PivotPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=current_low,
                    pivot_type=PivotType.LOW,
                    left_bars=self.config.left_bars,
                    right_bars=self.config.right_bars,
                    confirmed=True,
                ))

        return sorted(pivots, key=lambda p: p.index)

    def detect_pivots_live(self, data: OHLCVData) -> List[PivotPoint]:
        if len(data.candles) < self.config.left_bars + 1:
            return []

        highs = np.array([c.high for c in data.candles])
        lows = np.array([c.low for c in data.candles])
        timestamps = [c.timestamp for c in data.candles]

        pivots = []

        max_check = len(data.candles) - self.config.right_bars

        for i in range(self.config.left_bars, max_check):
            is_pivot_high = True
            is_pivot_low = True

            current_high = highs[i]
            current_low = lows[i]

            for j in range(1, self.config.left_bars + 1):
                if highs[i - j] >= current_high:
                    is_pivot_high = False
                if lows[i - j] <= current_low:
                    is_pivot_low = False

            for j in range(1, self.config.right_bars + 1):
                if i + j < len(data.candles):
                    if highs[i + j] > current_high:
                        is_pivot_high = False
                    if lows[i + j] < current_low:
                        is_pivot_low = False

            if is_pivot_high:
                confirmed = (i + self.config.right_bars) < len(data.candles)
                pivots.append(PivotPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=current_high,
                    pivot_type=PivotType.HIGH,
                    left_bars=self.config.left_bars,
                    right_bars=self.config.right_bars,
                    confirmed=confirmed,
                ))

            if is_pivot_low:
                confirmed = (i + self.config.right_bars) < len(data.candles)
                pivots.append(PivotPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=current_low,
                    pivot_type=PivotType.LOW,
                    left_bars=self.config.left_bars,
                    right_bars=self.config.right_bars,
                    confirmed=confirmed,
                ))

        return sorted(pivots, key=lambda p: p.index)

    def get_pivot_highs(self, pivots: List[PivotPoint]) -> List[PivotPoint]:
        return [p for p in pivots if p.pivot_type == PivotType.HIGH]

    def get_pivot_lows(self, pivots: List[PivotPoint]) -> List[PivotPoint]:
        return [p for p in pivots if p.pivot_type == PivotType.LOW]

    def get_last_confirmed_pivot(self, pivots: List[PivotPoint], pivot_type: PivotType) -> Optional[PivotPoint]:
        filtered = [p for p in pivots if p.pivot_type == pivot_type and p.confirmed]
        return filtered[-1] if filtered else None


def create_pivot_detector(left_bars: int = 5, right_bars: int = 5) -> PivotDetector:
    return PivotDetector(PivotConfig(left_bars=left_bars, right_bars=right_bars))