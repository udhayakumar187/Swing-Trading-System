from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd

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
    DivergenceType,
)
from app.patterns.detectors.pivot import PivotDetector, PivotConfig
from app.patterns.indicators.technical import rsi, macd, stochastic


@dataclass
class DivergenceConfig:
    pivot_left: int = 5
    pivot_right: int = 5
    min_divergence_bars: int = 5
    max_divergence_bars: int = 50
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    stoch_k: int = 14
    stoch_d: int = 3
    min_price_diff_pct: float = 0.005
    min_indicator_diff: float = 1.0


class DivergenceDetector(PatternDetector):
    def __init__(self, config: Optional[DivergenceConfig] = None):
        self.config = config or DivergenceConfig()
        self.pivot_detector = PivotDetector(PivotConfig(
            left_bars=self.config.pivot_left,
            right_bars=self.config.pivot_right,
        ))

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="DIVERGENCE_PATTERNS",
            category=PatternCategory.INDICATOR_PATTERN,
            description="Regular and hidden divergence detection across multiple indicators",
            required_candles=60,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "pivot_left": self.config.pivot_left,
                "pivot_right": self.config.pivot_right,
                "min_divergence_bars": self.config.min_divergence_bars,
                "max_divergence_bars": self.config.max_divergence_bars,
                "rsi_period": self.config.rsi_period,
                "macd_fast": self.config.macd_fast,
                "macd_slow": self.config.macd_slow,
                "macd_signal": self.config.macd_signal,
                "stoch_k": self.config.stoch_k,
                "stoch_d": self.config.stoch_d,
                "min_price_diff_pct": self.config.min_price_diff_pct,
                "min_indicator_diff": self.config.min_indicator_diff,
            },
            confirmation_rules=[
                "Divergence confirmed on pivot points only",
                "Price and indicator must move in opposite directions",
                "Minimum price and indicator difference thresholds",
            ],
            invalidation_rules=[
                "Price makes new extreme in divergence direction",
                "Indicator confirms trend continuation",
            ],
            quality_factors=[
                "Number of confirming pivots",
                "Magnitude of divergence",
                "Volume confirmation",
                "Trend context",
            ],
        )

    def _calculate_indicators(self, data: OHLCVData) -> Dict[str, np.ndarray]:
        close = np.array([c.close for c in data.candles])
        high = np.array([c.high for c in data.candles])
        low = np.array([c.low for c in data.candles])

        df = pd.DataFrame({"close": close, "high": high, "low": low})

        rsi_vals = rsi(df["close"], self.config.rsi_period).values
        macd_line, signal_line, histogram = macd(
            df["close"], self.config.macd_fast, self.config.macd_slow, self.config.macd_signal
        )
        stoch_k, stoch_d = stochastic(
            df["high"], df["low"], df["close"],
            self.config.stoch_k, self.config.stoch_d, 3
        )

        return {
            "rsi": rsi_vals,
            "macd": macd_line.values,
            "macd_hist": histogram.values,
            "stoch_k": stoch_k.values,
            "stoch_d": stoch_d.values,
            "close": close,
            "high": high,
            "low": low,
        }

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        if len(data.candles) < self.definition.required_candles:
            return []

        indicators = self._calculate_indicators(data)
        pivots = self.pivot_detector.detect_pivots(data)
        pivot_highs = self.pivot_detector.get_pivot_highs(pivots)
        pivot_lows = self.pivot_detector.get_pivot_lows(pivots)

        detections = []

        for indicator_name in ["rsi", "macd", "macd_hist", "stoch_k"]:
            detections.extend(self._detect_divergences(
                data, indicators, indicator_name, pivot_highs, pivot_lows
            ))

        return detections

    def _detect_divergences(
        self,
        data: OHLCVData,
        indicators: Dict[str, np.ndarray],
        indicator_name: str,
        pivot_highs: List[PivotPoint],
        pivot_lows: List[PivotPoint],
    ) -> List[PatternDetection]:
        detections = []
        indicator_vals = indicators[indicator_name]
        price_highs = indicators["high"]
        price_lows = indicators["low"]

        for i in range(1, len(pivot_highs)):
            curr_pivot = pivot_highs[i]
            prev_pivot = pivot_highs[i - 1]

            bars_between = curr_pivot.index - prev_pivot.index
            if bars_between < self.config.min_divergence_bars or bars_between > self.config.max_divergence_bars:
                continue

            curr_price = price_highs[curr_pivot.index]
            prev_price = price_highs[prev_pivot.index]
            curr_ind = indicator_vals[curr_pivot.index]
            prev_ind = indicator_vals[prev_pivot.index]

            if np.isnan(curr_ind) or np.isnan(prev_ind):
                continue

            price_diff_pct = (curr_price - prev_price) / prev_price
            ind_diff = curr_ind - prev_ind

            if price_diff_pct > self.config.min_price_diff_pct and ind_diff < -self.config.min_indicator_diff:
                detections.append(self._create_divergence_detection(
                    data, prev_pivot, curr_pivot, indicator_name,
                    DivergenceType.REGULAR_BEARISH, PatternDirection.BEARISH,
                    prev_price, curr_price, prev_ind, curr_ind,
                    "Price higher high, indicator lower high"
                ))

            elif price_diff_pct < -self.config.min_price_diff_pct and ind_diff > self.config.min_indicator_diff:
                detections.append(self._create_divergence_detection(
                    data, prev_pivot, curr_pivot, indicator_name,
                    DivergenceType.HIDDEN_BEARISH, PatternDirection.BEARISH,
                    prev_price, curr_price, prev_ind, curr_ind,
                    "Price lower high, indicator higher high (hidden)"
                ))

        for i in range(1, len(pivot_lows)):
            curr_pivot = pivot_lows[i]
            prev_pivot = pivot_lows[i - 1]

            bars_between = curr_pivot.index - prev_pivot.index
            if bars_between < self.config.min_divergence_bars or bars_between > self.config.max_divergence_bars:
                continue

            curr_price = price_lows[curr_pivot.index]
            prev_price = price_lows[prev_pivot.index]
            curr_ind = indicator_vals[curr_pivot.index]
            prev_ind = indicator_vals[prev_pivot.index]

            if np.isnan(curr_ind) or np.isnan(prev_ind):
                continue

            price_diff_pct = (curr_price - prev_price) / prev_price
            ind_diff = curr_ind - prev_ind

            if price_diff_pct < -self.config.min_price_diff_pct and ind_diff > self.config.min_indicator_diff:
                detections.append(self._create_divergence_detection(
                    data, prev_pivot, curr_pivot, indicator_name,
                    DivergenceType.REGULAR_BULLISH, PatternDirection.BULLISH,
                    prev_price, curr_price, prev_ind, curr_ind,
                    "Price lower low, indicator higher low"
                ))

            elif price_diff_pct > self.config.min_price_diff_pct and ind_diff < -self.config.min_indicator_diff:
                detections.append(self._create_divergence_detection(
                    data, prev_pivot, curr_pivot, indicator_name,
                    DivergenceType.HIDDEN_BULLISH, PatternDirection.BULLISH,
                    prev_price, curr_price, prev_ind, curr_ind,
                    "Price higher low, indicator lower low (hidden)"
                ))

        return detections

    def _create_divergence_detection(
        self,
        data: OHLCVData,
        pivot1: PivotPoint,
        pivot2: PivotPoint,
        indicator_name: str,
        div_type: DivergenceType,
        direction: PatternDirection,
        price1: float,
        price2: float,
        ind1: float,
        ind2: float,
        description: str,
    ) -> PatternDetection:
        from datetime import datetime

        price_change = abs(price2 - price1) / price1 * 100
        ind_change = abs(ind2 - ind1)

        quality = min(100, int(50 + price_change * 10 + ind_change * 2))

        return PatternDetection(
            symbol=data.symbol,
            timeframe=data.timeframe,
            pattern_name=f"{indicator_name.upper()}_{div_type.value}",
            pattern_category=self.get_category(),
            direction=direction,
            status=PatternStatus.CONFIRMED,
            start_timestamp=pivot1.timestamp,
            confirmation_timestamp=pivot2.timestamp,
            completion_timestamp=pivot2.timestamp,
            detection_timestamp=datetime.utcnow(),
            price_levels={
                "pivot1_price": price1,
                "pivot2_price": price2,
                "pivot1_indicator": ind1,
                "pivot2_indicator": ind2,
            },
            invalidation_level=price2 if direction == PatternDirection.BULLISH else price2,
            quality_score=quality,
            metadata={
                "indicator": indicator_name,
                "divergence_type": div_type.value,
                "pivot1_index": pivot1.index,
                "pivot2_index": pivot2.index,
                "price_change_pct": price_change,
                "indicator_change": ind_change,
            },
            explanation=[
                f"{indicator_name.upper()} {div_type.value.replace('_', ' ').title()}",
                description,
                f"Price change: {price_change:.2f}%, Indicator change: {ind_change:.2f}",
            ],
            pivots=[pivot1, pivot2],
        )


def register_divergence_patterns(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(DivergenceDetector())