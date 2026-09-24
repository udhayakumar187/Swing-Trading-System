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
)
from app.patterns.detectors.pivot import PivotDetector, PivotConfig


@dataclass
class ChartPatternConfig:
    pivot_left: int = 5
    pivot_right: int = 5
    tolerance: float = 0.02
    min_pattern_bars: int = 10
    max_pattern_bars: int = 100
    volume_confirmation: bool = True
    breakout_threshold: float = 0.01
    time_symmetry_tolerance: float = 0.3


class ChartPatternDetector(PatternDetector):
    def __init__(self, config: Optional[ChartPatternConfig] = None):
        self.config = config or ChartPatternConfig()
        self.pivot_detector = PivotDetector(PivotConfig(
            left_bars=self.config.pivot_left,
            right_bars=self.config.pivot_right,
        ))

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="CHART_PATTERNS",
            category=PatternCategory.CHART_PATTERN,
            description="Classic chart patterns: double top/bottom, head & shoulders, triangles, flags, wedges, cup & handle",
            required_candles=50,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "pivot_left": self.config.pivot_left,
                "pivot_right": self.config.pivot_right,
                "tolerance": self.config.tolerance,
                "min_pattern_bars": self.config.min_pattern_bars,
                "max_pattern_bars": self.config.max_pattern_bars,
                "breakout_threshold": self.config.breakout_threshold,
                "time_symmetry_tolerance": self.config.time_symmetry_tolerance,
            },
            confirmation_rules=[
                "Pattern must have confirmed pivot points",
                "Breakout requires close beyond pattern boundary",
                "Volume should increase on breakout",
                "Measured move target calculated",
            ],
            invalidation_rules=[
                "Price closes back inside pattern after breakout",
                "Pattern exceeds maximum time/price limits",
            ],
            quality_factors=[
                "Pattern symmetry",
                "Volume profile",
                "Time symmetry",
                "Trend context",
                "Multiple touch points",
            ],
        )

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        if len(data.candles) < self.definition.required_candles:
            return []

        pivots = self.pivot_detector.detect_pivots(data)
        highs = self.pivot_detector.get_pivot_highs(pivots)
        lows = self.pivot_detector.get_pivot_lows(pivots)

        if len(highs) < 2 or len(lows) < 2:
            return []

        detections = []

        detections.extend(self._detect_double_top_bottom(data, highs, lows))
        detections.extend(self._detect_triple_top_bottom(data, highs, lows))
        detections.extend(self._detect_head_shoulders(data, highs, lows))
        detections.extend(self._detect_triangles(data, highs, lows))
        detections.extend(self._detect_wedges(data, highs, lows))
        detections.extend(self._detect_rectangle(data, highs, lows))
        detections.extend(self._detect_flags_pennants(data, highs, lows))
        detections.extend(self._detect_cup_handle(data, highs, lows))
        detections.extend(self._detect_rounding(data, highs, lows))
        detections.extend(self._detect_broadening(data, highs, lows))

        return detections

    def _prices_equal(self, p1: float, p2: float) -> bool:
        return abs(p1 - p2) / max(p1, p2) <= self.config.tolerance

    def _detect_double_top_bottom(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []

        for i in range(1, len(highs)):
            h1, h2 = highs[i-1], highs[i]
            bars_between = h2.index - h1.index
            if self.config.min_pattern_bars <= bars_between <= self.config.max_pattern_bars:
                if self._prices_equal(h1.price, h2.price):
                    neckline = min(l.price for l in lows if h1.index < l.index < h2.index) if any(h1.index < l.index < h2.index for l in lows) else min(h1.price, h2.price) * 0.97
                    if data.candles[-1].close < neckline * (1 - self.config.breakout_threshold):
                        detections.append(self._create_detection(
                            data, h1.index, h2.index,
                            "DOUBLE_TOP", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                            {"peak1": h1.price, "peak2": h2.price, "neckline": neckline},
                            invalidation_level=max(h1.price, h2.price),
                            target_levels={"target": neckline - (max(h1.price, h2.price) - neckline)},
                            explanation=[
                                f"Double top: two peaks at ~{h1.price:.2f}/{h2.price:.2f}",
                                f"Neckline at {neckline:.2f} broken",
                                f"Time between peaks: {bars_between} bars"
                            ]
                        ))

        for i in range(1, len(lows)):
            l1, l2 = lows[i-1], lows[i]
            bars_between = l2.index - l1.index
            if self.config.min_pattern_bars <= bars_between <= self.config.max_pattern_bars:
                if self._prices_equal(l1.price, l2.price):
                    neckline = max(h.price for h in highs if l1.index < h.index < l2.index) if any(l1.index < h.index < l2.index for h in highs) else max(l1.price, l2.price) * 1.03
                    if data.candles[-1].close > neckline * (1 + self.config.breakout_threshold):
                        detections.append(self._create_detection(
                            data, l1.index, l2.index,
                            "DOUBLE_BOTTOM", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                            {"trough1": l1.price, "trough2": l2.price, "neckline": neckline},
                            invalidation_level=min(l1.price, l2.price),
                            target_levels={"target": neckline + (neckline - min(l1.price, l2.price))},
                            explanation=[
                                f"Double bottom: two troughs at ~{l1.price:.2f}/{l2.price:.2f}",
                                f"Neckline at {neckline:.2f} broken",
                                f"Time between troughs: {bars_between} bars"
                            ]
                        ))

        return detections

    def _detect_triple_top_bottom(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []

        for i in range(2, len(highs)):
            h1, h2, h3 = highs[i-2], highs[i-1], highs[i]
            if all(self._prices_equal(h1.price, h.price) for h in [h2, h3]):
                bars_span = h3.index - h1.index
                if bars_span <= self.config.max_pattern_bars:
                    neckline = min(l.price for l in lows if h1.index < l.index < h3.index) if any(h1.index < l.index < h3.index for l in lows) else min(h1.price, h2.price, h3.price) * 0.97
                    if data.candles[-1].close < neckline * (1 - self.config.breakout_threshold):
                        detections.append(self._create_detection(
                            data, h1.index, h3.index,
                            "TRIPLE_TOP", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                            {"peak1": h1.price, "peak2": h2.price, "peak3": h3.price, "neckline": neckline},
                            invalidation_level=max(h1.price, h2.price, h3.price),
                            target_levels={"target": neckline - (max(h1.price, h2.price, h3.price) - neckline)},
                            explanation=[
                                f"Triple top: three peaks at ~{h1.price:.2f}/{h2.price:.2f}/{h3.price:.2f}",
                                f"Neckline at {neckline:.2f} broken"
                            ]
                        ))

        for i in range(2, len(lows)):
            l1, l2, l3 = lows[i-2], lows[i-1], lows[i]
            if all(self._prices_equal(l1.price, l.price) for l in [l2, l3]):
                bars_span = l3.index - l1.index
                if bars_span <= self.config.max_pattern_bars:
                    neckline = max(h.price for h in highs if l1.index < h.index < l3.index) if any(l1.index < h.index < l3.index for h in highs) else max(l1.price, l2.price, l3.price) * 1.03
                    if data.candles[-1].close > neckline * (1 + self.config.breakout_threshold):
                        detections.append(self._create_detection(
                            data, l1.index, l3.index,
                            "TRIPLE_BOTTOM", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                            {"trough1": l1.price, "trough2": l2.price, "trough3": l3.price, "neckline": neckline},
                            invalidation_level=min(l1.price, l2.price, l3.price),
                            target_levels={"target": neckline + (neckline - min(l1.price, l2.price, l3.price))},
                            explanation=[
                                f"Triple bottom: three troughs at ~{l1.price:.2f}/{l2.price:.2f}/{l3.price:.2f}",
                                f"Neckline at {neckline:.2f} broken"
                            ]
                        ))

        return detections

    def _detect_head_shoulders(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []

        for i in range(2, len(highs)):
            ls, h, rs = highs[i-2], highs[i-1], highs[i]
            if h.price > ls.price and h.price > rs.price and self._prices_equal(ls.price, rs.price):
                neckline_l = max(l for l in lows if ls.index < l.index < h.index) if any(ls.index < l.index < h.index for l in lows) else None
                neckline_r = max(l for l in lows if h.index < l.index < rs.index) if any(h.index < l.index < rs.index for l in lows) else None
                if neckline_l and neckline_r and self._prices_equal(neckline_l.price, neckline_r.price):
                    neckline = (neckline_l.price + neckline_r.price) / 2
                    if data.candles[-1].close < neckline * (1 - self.config.breakout_threshold):
                        detections.append(self._create_detection(
                            data, ls.index, rs.index,
                            "HEAD_AND_SHOULDERS", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                            {"left_shoulder": ls.price, "head": h.price, "right_shoulder": rs.price, "neckline": neckline},
                            invalidation_level=h.price,
                            target_levels={"target": neckline - (h.price - neckline)},
                            explanation=[
                                f"Head & Shoulders: LS={ls.price:.2f}, H={h.price:.2f}, RS={rs.price:.2f}",
                                f"Neckline at {neckline:.2f} broken"
                            ]
                        ))

        for i in range(2, len(lows)):
            ls, h, rs = lows[i-2], lows[i-1], lows[i]
            if h.price < ls.price and h.price < rs.price and self._prices_equal(ls.price, rs.price):
                neckline_l = min(hgh for hgh in highs if ls.index < hgh.index < h.index) if any(ls.index < hgh.index < h.index for hgh in highs) else None
                neckline_r = min(hgh for hgh in highs if h.index < hgh.index < rs.index) if any(h.index < hgh.index < rs.index for hgh in highs) else None
                if neckline_l and neckline_r and self._prices_equal(neckline_l.price, neckline_r.price):
                    neckline = (neckline_l.price + neckline_r.price) / 2
                    if data.candles[-1].close > neckline * (1 + self.config.breakout_threshold):
                        detections.append(self._create_detection(
                            data, ls.index, rs.index,
                            "INVERSE_HEAD_AND_SHOULDERS", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                            {"left_shoulder": ls.price, "head": h.price, "right_shoulder": rs.price, "neckline": neckline},
                            invalidation_level=h.price,
                            target_levels={"target": neckline + (neckline - h.price)},
                            explanation=[
                                f"Inverse H&S: LS={ls.price:.2f}, H={h.price:.2f}, RS={rs.price:.2f}",
                                f"Neckline at {neckline:.2f} broken"
                            ]
                        ))

        return detections

    def _detect_triangles(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 3 or len(lows) < 3:
            return detections

        recent_highs = highs[-4:]
        recent_lows = lows[-4:]

        high_slopes = [(recent_highs[i].price - recent_highs[i-1].price) / (recent_highs[i].index - recent_highs[i-1].index) for i in range(1, len(recent_highs))]
        low_slopes = [(recent_lows[i].price - recent_lows[i-1].price) / (recent_lows[i].index - recent_lows[i-1].index) for i in range(1, len(recent_lows))]

        avg_high_slope = np.mean(high_slopes) if high_slopes else 0
        avg_low_slope = np.mean(low_slopes) if low_slopes else 0

        last_close = data.candles[-1].close
        high_line = recent_highs[-1].price + avg_high_slope * (len(data.candles) - 1 - recent_highs[-1].index)
        low_line = recent_lows[-1].price + avg_low_slope * (len(data.candles) - 1 - recent_lows[-1].index)

        if abs(avg_high_slope) < 0.001 and avg_low_slope > 0.001:
            if last_close > high_line * (1 + self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_highs[0].index, len(data.candles) - 1,
                    "ASCENDING_TRIANGLE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"resistance": high_line, "support_slope": avg_low_slope, "apex_index": recent_highs[-1].index},
                    invalidation_level=low_line,
                    target_levels={"target": high_line + (high_line - low_line)},
                    explanation=["Ascending triangle: flat resistance, rising support", f"Breakout above resistance at {high_line:.2f}"]
                ))

        elif abs(avg_low_slope) < 0.001 and avg_high_slope < -0.001:
            if last_close < low_line * (1 - self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_lows[0].index, len(data.candles) - 1,
                    "DESCENDING_TRIANGLE", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"support": low_line, "resistance_slope": avg_high_slope, "apex_index": recent_lows[-1].index},
                    invalidation_level=high_line,
                    target_levels={"target": low_line - (high_line - low_line)},
                    explanation=["Descending triangle: flat support, falling resistance", f"Breakdown below support at {low_line:.2f}"]
                ))

        elif avg_high_slope < -0.001 and avg_low_slope > 0.001:
            if last_close > high_line * (1 + self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_highs[0].index, len(data.candles) - 1,
                    "SYMMETRICAL_TRIANGLE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"resistance_slope": avg_high_slope, "support_slope": avg_low_slope},
                    invalidation_level=low_line,
                    target_levels={"target": high_line + (high_line - low_line)},
                    explanation=["Symmetrical triangle: converging trendlines", f"Bullish breakout above {high_line:.2f}"]
                ))
            elif last_close < low_line * (1 - self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_lows[0].index, len(data.candles) - 1,
                    "SYMMETRICAL_TRIANGLE", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"resistance_slope": avg_high_slope, "support_slope": avg_low_slope},
                    invalidation_level=high_line,
                    target_levels={"target": low_line - (high_line - low_line)},
                    explanation=["Symmetrical triangle: converging trendlines", f"Bearish breakdown below {low_line:.2f}"]
                ))

        return detections

    def _detect_wedges(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 3 or len(lows) < 3:
            return detections

        recent_highs = highs[-4:]
        recent_lows = lows[-4:]

        high_slopes = [(recent_highs[i].price - recent_highs[i-1].price) / (recent_highs[i].index - recent_highs[i-1].index) for i in range(1, len(recent_highs))]
        low_slopes = [(recent_lows[i].price - recent_lows[i-1].price) / (recent_lows[i].index - recent_lows[i-1].index) for i in range(1, len(recent_lows))]

        avg_high_slope = np.mean(high_slopes) if high_slopes else 0
        avg_low_slope = np.mean(low_slopes) if low_slopes else 0

        last_close = data.candles[-1].close
        high_line = recent_highs[-1].price + avg_high_slope * (len(data.candles) - 1 - recent_highs[-1].index)
        low_line = recent_lows[-1].price + avg_low_slope * (len(data.candles) - 1 - recent_lows[-1].index)

        if avg_high_slope < -0.001 and avg_low_slope < -0.001 and avg_low_slope > avg_high_slope:
            if last_close < low_line * (1 - self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_highs[0].index, len(data.candles) - 1,
                    "FALLING_WEDGE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"resistance_slope": avg_high_slope, "support_slope": avg_low_slope},
                    invalidation_level=last_low.price,
                    target_levels={"target": high_line + (high_line - low_line)},
                    explanation=["Falling wedge: both lines sloping down, support steeper", f"Bullish breakout below {low_line:.2f}"]
                ))

        elif avg_high_slope > 0.001 and avg_low_slope > 0.001 and avg_high_slope > avg_low_slope:
            if last_close > high_line * (1 + self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_lows[0].index, len(data.candles) - 1,
                    "RISING_WEDGE", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"resistance_slope": avg_high_slope, "support_slope": avg_low_slope},
                    invalidation_level=last_high.price,
                    target_levels={"target": low_line - (high_line - low_line)},
                    explanation=["Rising wedge: both lines sloping up, resistance steeper", f"Bearish breakout above {high_line:.2f}"]
                ))

        return detections

    def _detect_rectangle(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 3 or len(lows) < 3:
            return detections

        recent_highs = highs[-4:]
        recent_lows = lows[-4:]

        high_prices = [h.price for h in recent_highs]
        low_prices = [l.price for l in recent_lows]

        high_range = max(high_prices) - min(high_prices)
        low_range = max(low_prices) - min(low_prices)
        avg_high = np.mean(high_prices)
        avg_low = np.mean(low_prices)

        if high_range / avg_high < self.config.tolerance and low_range / avg_low < self.config.tolerance:
            height = avg_high - avg_low
            last_close = data.candles[-1].close

            if last_close > avg_high * (1 + self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_highs[0].index, len(data.candles) - 1,
                    "RECTANGLE_BREAKOUT_UP", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"resistance": avg_high, "support": avg_low, "height": height},
                    invalidation_level=avg_low,
                    target_levels={"target": avg_high + height},
                    explanation=[f"Rectangle: range {avg_low:.2f}-{avg_high:.2f}", f"Bullish breakout above {avg_high:.2f}"]
                ))
            elif last_close < avg_low * (1 - self.config.breakout_threshold):
                detections.append(self._create_detection(
                    data, recent_lows[0].index, len(data.candles) - 1,
                    "RECTANGLE_BREAKDOWN", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"resistance": avg_high, "support": avg_low, "height": height},
                    invalidation_level=avg_high,
                    target_levels={"target": avg_low - height},
                    explanation=[f"Rectangle: range {avg_low:.2f}-{avg_high:.2f}", f"Bearish breakdown below {avg_low:.2f}"]
                ))

        return detections

    def _detect_flags_pennants(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 2 or len(lows) < 2:
            return detections

        pole_height = 0
        pole_start = 0

        for i in range(len(data.candles) - 10, 5, -1):
            if i + 5 < len(data.candles):
                move = abs(data.candles[i+5].close - data.candles[i].close) / data.candles[i].close
                if move > 0.05:
                    pole_height = move
                    pole_start = i
                    break

        if pole_height > 0:
            flag_highs = [h for h in highs if h.index > pole_start]
            flag_lows = [l for l in lows if l.index > pole_start]

            if len(flag_highs) >= 2 and len(flag_lows) >= 2:
                high_slope = (flag_highs[-1].price - flag_highs[0].price) / (flag_highs[-1].index - flag_highs[0].index)
                low_slope = (flag_lows[-1].price - flag_lows[0].price) / (flag_lows[-1].index - flag_lows[0].index)

                last_close = data.candles[-1].close

                if pole_height > 0 and data.candles[pole_start+5].close > data.candles[pole_start].close:
                    if high_slope < -0.001 and low_slope < -0.001:
                        if last_close > flag_highs[-1].price * (1 + self.config.breakout_threshold):
                            detections.append(self._create_detection(
                                data, pole_start, len(data.candles) - 1,
                                "BULL_FLAG", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                                {"pole_height": pole_height, "flag_high_slope": high_slope, "flag_low_slope": low_slope},
                                invalidation_level=flag_lows[-1].price,
                                target_levels={"target": last_close + pole_height * last_close},
                                explanation=[f"Bull flag: {pole_height:.1%} pole, downward sloping flag", "Bullish continuation"]
                            ))

                elif pole_height > 0 and data.candles[pole_start+5].close < data.candles[pole_start].close:
                    if high_slope > 0.001 and low_slope > 0.001:
                        if last_close < flag_lows[-1].price * (1 - self.config.breakout_threshold):
                            detections.append(self._create_detection(
                                data, pole_start, len(data.candles) - 1,
                                "BEAR_FLAG", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                                {"pole_height": pole_height, "flag_high_slope": high_slope, "flag_low_slope": low_slope},
                                invalidation_level=flag_highs[-1].price,
                                target_levels={"target": last_close - pole_height * last_close},
                                explanation=[f"Bear flag: {pole_height:.1%} pole, upward sloping flag", "Bearish continuation"]
                            ))

        return detections

    def _detect_cup_handle(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 3 or len(lows) < 3:
            return detections

        for i in range(2, len(highs)):
            left_rim = highs[i-2]
            right_rim = highs[i]

            cup_lows = [l for l in lows if left_rim.index < l.index < right_rim.index]
            if not cup_lows:
                continue

            cup_bottom = min(cup_lows, key=lambda x: x.price)

            if self._prices_equal(left_rim.price, right_rim.price):
                cup_depth = (left_rim.price - cup_bottom.price) / left_rim.price
                if 0.1 < cup_depth < 0.5:
                    handle_start = right_rim.index
                    handle_highs = [h for h in highs if h.index > handle_start]
                    handle_lows = [l for l in lows if l.index > handle_start]

                    if len(handle_highs) >= 1 and len(handle_lows) >= 1:
                        handle_high = handle_highs[0].price
                        handle_low = handle_lows[0].price
                        handle_depth = (right_rim.price - handle_low) / right_rim.price

                        if handle_depth < cup_depth * 0.5:
                            last_close = data.candles[-1].close
                            if last_close > right_rim.price * (1 + self.config.breakout_threshold):
                                detections.append(self._create_detection(
                                    data, left_rim.index, len(data.candles) - 1,
                                    "CUP_AND_HANDLE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                                    {"left_rim": left_rim.price, "right_rim": right_rim.price, "cup_bottom": cup_bottom.price, "handle_low": handle_low},
                                    invalidation_level=handle_low,
                                    target_levels={"target": right_rim.price + (right_rim.price - cup_bottom.price)},
                                    explanation=[
                                        f"Cup & Handle: rim at {left_rim.price:.2f}, bottom at {cup_bottom.price:.2f}",
                                        f"Handle low at {handle_low:.2f}, breakout above rim"
                                    ]
                                ))

        return detections

    def _detect_rounding(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(lows) < 5:
            return detections

        recent_lows = lows[-5:]
        prices = [l.price for l in recent_lows]

        if prices[0] > prices[1] > prices[2] < prices[3] < prices[4]:
            last_close = data.candles[-1].close
            if last_close > recent_lows[0].price:
                detections.append(self._create_detection(
                    data, recent_lows[0].index, len(data.candles) - 1,
                    "ROUNDING_BOTTOM", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"left_lip": prices[0], "bottom": prices[2], "right_lip": prices[4]},
                    invalidation_level=prices[2],
                    target_levels={"target": prices[0] + (prices[0] - prices[2])},
                    explanation=["Rounding bottom: gradual curve from left lip to right lip", "Bullish reversal pattern"]
                ))

        if len(highs) >= 5:
            recent_highs = highs[-5:]
            prices = [h.price for h in recent_highs]

            if prices[0] < prices[1] < prices[2] > prices[3] > prices[4]:
                last_close = data.candles[-1].close
                if last_close < recent_highs[0].price:
                    detections.append(self._create_detection(
                        data, recent_highs[0].index, len(data.candles) - 1,
                        "ROUNDING_TOP", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                        {"left_lip": prices[0], "top": prices[2], "right_lip": prices[4]},
                        invalidation_level=prices[2],
                        target_levels={"target": prices[0] - (prices[2] - prices[0])},
                        explanation=["Rounding top: gradual curve from left lip to right lip", "Bearish reversal pattern"]
                    ))

        return detections

    def _detect_broadening(self, data: OHLCVData, highs: List[PivotPoint], lows: List[PivotPoint]) -> List[PatternDetection]:
        detections = []
        if len(highs) < 3 or len(lows) < 3:
            return detections

        recent_highs = highs[-4:]
        recent_lows = lows[-4:]

        high_slopes = [(recent_highs[i].price - recent_highs[i-1].price) / (recent_highs[i].index - recent_highs[i-1].index) for i in range(1, len(recent_highs))]
        low_slopes = [(recent_lows[i].price - recent_lows[i-1].price) / (recent_lows[i].index - recent_lows[i-1].index) for i in range(1, len(recent_lows))]

        avg_high_slope = np.mean(high_slopes) if high_slopes else 0
        avg_low_slope = np.mean(low_slopes) if low_slopes else 0

        if avg_high_slope > 0.001 and avg_low_slope < -0.001:
            detections.append(self._create_detection(
                data, recent_highs[0].index, len(data.candles) - 1,
                "BROADENING_FORMATION", PatternDirection.NEUTRAL, PatternStatus.FORMING,
                {"resistance_slope": avg_high_slope, "support_slope": avg_low_slope},
                explanation=["Broadening formation: diverging trendlines", "Increasing volatility, no clear direction"]
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


def register_chart_patterns(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(ChartPatternDetector())