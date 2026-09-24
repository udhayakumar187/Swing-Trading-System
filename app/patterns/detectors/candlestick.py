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
    Candle,
)


@dataclass
class CandlestickConfig:
    doji_threshold: float = 0.1
    body_ratio_threshold: float = 0.5
    long_wick_ratio: float = 2.0
    short_wick_ratio: float = 0.3
    marubozu_threshold: float = 0.95
    spinning_top_body_max: float = 0.3
    engulfing_threshold: float = 1.0
    harami_threshold: float = 0.25
    piercing_threshold: float = 0.5
    dark_cloud_threshold: float = 0.5
    tweezer_tolerance: float = 0.002
    three_soldiers_min_body: float = 0.6
    three_crows_max_body: float = 0.6
    star_gap_threshold: float = 0.003
    morning_star_third_body: float = 0.5
    evening_star_third_body: float = 0.5


class CandlestickPatternDetector(PatternDetector):
    def __init__(self, config: Optional[CandlestickConfig] = None):
        self.config = config or CandlestickConfig()
        self._candle_cache: Dict[int, Dict[str, float]] = {}

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="CANDLESTICK_PATTERNS",
            category=PatternCategory.CANDLESTICK,
            description="Comprehensive candlestick pattern detection",
            required_candles=3,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "doji_threshold": self.config.doji_threshold,
                "body_ratio_threshold": self.config.body_ratio_threshold,
                "long_wick_ratio": self.config.long_wick_ratio,
                "short_wick_ratio": self.config.short_wick_ratio,
                "marubozu_threshold": self.config.marubozu_threshold,
                "spinning_top_body_max": self.config.spinning_top_body_max,
                "engulfing_threshold": self.config.engulfing_threshold,
                "harami_threshold": self.config.harami_threshold,
                "piercing_threshold": self.config.piercing_threshold,
                "dark_cloud_threshold": self.config.dark_cloud_threshold,
                "tweezer_tolerance": self.config.tweezer_tolerance,
                "three_soldiers_min_body": self.config.three_soldiers_min_body,
                "three_crows_max_body": self.config.three_crows_max_body,
                "star_gap_threshold": self.config.star_gap_threshold,
                "morning_star_third_body": self.config.morning_star_third_body,
                "evening_star_third_body": self.config.evening_star_third_body,
            },
            confirmation_rules=[
                "Pattern must form at relevant support/resistance level",
                "Volume confirmation preferred",
                "Trend context considered",
            ],
            invalidation_rules=[
                "Pattern invalidated if price moves against direction beyond pattern extreme",
            ],
            quality_factors=[
                "Pattern symmetry",
                "Volume confirmation",
                "Trend alignment",
                "Support/resistance confluence",
            ],
        )

    def _analyze_candle(self, candle: Candle) -> Dict[str, float]:
        body = abs(candle.close - candle.open)
        candle_range = candle.high - candle.low
        upper_wick = candle.high - max(candle.open, candle.close)
        lower_wick = min(candle.open, candle.close) - candle.low

        if candle_range == 0:
            body_ratio = 0
            upper_wick_ratio = 0
            lower_wick_ratio = 0
        else:
            body_ratio = body / candle_range
            upper_wick_ratio = upper_wick / candle_range if candle_range > 0 else 0
            lower_wick_ratio = lower_wick / candle_range if candle_range > 0 else 0

        is_bullish = candle.close > candle.open
        is_bearish = candle.close < candle.open
        is_doji = body_ratio <= self.config.doji_threshold

        return {
            "body": body,
            "range": candle_range,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
            "body_ratio": body_ratio,
            "upper_wick_ratio": upper_wick_ratio,
            "lower_wick_ratio": lower_wick_ratio,
            "is_bullish": is_bullish,
            "is_bearish": is_bearish,
            "is_doji": is_doji,
        }

    def _get_candle_analysis(self, idx: int, data: OHLCVData) -> Dict[str, float]:
        if idx not in self._candle_cache:
            self._candle_cache[idx] = self._analyze_candle(data.candles[idx])
        return self._candle_cache[idx]

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        self._candle_cache.clear()
        detections = []

        for i in range(len(data.candles)):
            single = self._detect_single_candle(data, i)
            detections.extend(single)

            if i >= 1:
                two_candle = self._detect_two_candle(data, i - 1, i)
                detections.extend(two_candle)

            if i >= 2:
                three_candle = self._detect_three_candle(data, i - 2, i - 1, i)
                detections.extend(three_candle)

        return detections

    def _detect_single_candle(self, data: OHLCVData, i: int) -> List[PatternDetection]:
        c = data.candles[i]
        a = self._get_candle_analysis(i, data)
        detections = []

        if a["is_doji"]:
            if a["upper_wick_ratio"] > self.config.long_wick_ratio and a["lower_wick_ratio"] > self.config.long_wick_ratio:
                detections.append(self._create_detection(
                    data, i, i, "LONG_LEGGED_DOJI", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low},
                    explanation=["Long upper and lower wicks with small body", "Indecision pattern"]
                ))
            elif a["lower_wick_ratio"] > self.config.long_wick_ratio and a["upper_wick_ratio"] < self.config.short_wick_ratio:
                detections.append(self._create_detection(
                    data, i, i, "DRAGONFLY_DOJI", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low, "open_close": c.open},
                    invalidation_level=c.low,
                    explanation=["Long lower wick, minimal upper wick", "Bullish reversal signal at support"]
                ))
            elif a["upper_wick_ratio"] > self.config.long_wick_ratio and a["lower_wick_ratio"] < self.config.short_wick_ratio:
                detections.append(self._create_detection(
                    data, i, i, "GRAVESTONE_DOJI", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low, "open_close": c.open},
                    invalidation_level=c.high,
                    explanation=["Long upper wick, minimal lower wick", "Bearish reversal signal at resistance"]
                ))
            else:
                detections.append(self._create_detection(
                    data, i, i, "DOJI", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low, "open_close": c.open},
                    explanation=["Open and close nearly equal", "Indecision pattern"]
                ))

        elif a["body_ratio"] >= self.config.marubozu_threshold:
            if a["is_bullish"]:
                detections.append(self._create_detection(
                    data, i, i, "BULLISH_MARUBOZU", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low},
                    explanation=["Long bullish body with minimal wicks", "Strong buying pressure"]
                ))
            else:
                detections.append(self._create_detection(
                    data, i, i, "BEARISH_MARUBOZU", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low},
                    explanation=["Long bearish body with minimal wicks", "Strong selling pressure"]
                ))

        elif a["body_ratio"] <= self.config.spinning_top_body_max and a["upper_wick_ratio"] > 0.3 and a["lower_wick_ratio"] > 0.3:
            detections.append(self._create_detection(
                data, i, i, "SPINNING_TOP", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"candle_high": c.high, "candle_low": c.low},
                explanation=["Small body with long upper and lower wicks", "Indecision pattern"]
            ))

        elif a["lower_wick"] >= a["body"] * self.config.long_wick_ratio and a["upper_wick"] <= a["body"] * self.config.short_wick_ratio and a["body_ratio"] > self.config.doji_threshold:
            if a["is_bullish"]:
                detections.append(self._create_detection(
                    data, i, i, "HAMMER", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low},
                    invalidation_level=c.low,
                    explanation=["Small body at top, long lower wick", "Bullish reversal after downtrend"]
                ))
            else:
                detections.append(self._create_detection(
                    data, i, i, "HANGING_MAN", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low},
                    invalidation_level=c.high,
                    explanation=["Small body at top, long lower wick", "Bearish reversal after uptrend"]
                ))

        elif a["upper_wick"] >= a["body"] * self.config.long_wick_ratio and a["lower_wick"] <= a["body"] * self.config.short_wick_ratio and a["body_ratio"] > self.config.doji_threshold:
            if a["is_bullish"]:
                detections.append(self._create_detection(
                    data, i, i, "INVERTED_HAMMER", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low},
                    invalidation_level=c.low,
                    explanation=["Small body at bottom, long upper wick", "Potential bullish reversal"]
                ))
            else:
                detections.append(self._create_detection(
                    data, i, i, "SHOOTING_STAR", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"candle_high": c.high, "candle_low": c.low},
                    invalidation_level=c.high,
                    explanation=["Small body at bottom, long upper wick", "Bearish reversal after uptrend"]
                ))

        return detections

    def _detect_two_candle(self, data: OHLCVData, i: int, j: int) -> List[PatternDetection]:
        c1 = data.candles[i]
        c2 = data.candles[j]
        a1 = self._get_candle_analysis(i, data)
        a2 = self._get_candle_analysis(j, data)
        detections = []

        if a1["is_bearish"] and a2["is_bullish"]:
            if (c2.open < c1.close and c2.close > c1.open and
                a2["body"] >= a1["body"] * self.config.engulfing_threshold):
                detections.append(self._create_detection(
                    data, i, j, "BULLISH_ENGULFING", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=min(c1.low, c2.low),
                    target_levels={"target_1": c2.high + (c2.high - min(c1.low, c2.low))},
                    explanation=[
                        f"Bullish candle body fully engulfs previous bearish body",
                        f"Engulfing ratio: {a2['body']/a1['body']:.2f}"
                    ]
                ))

            elif (c2.open > c1.close and c2.close < c1.open and
                  c2.open < c1.open and c2.close > (c1.open + c1.close) / 2):
                detections.append(self._create_detection(
                    data, i, j, "PIERCING_LINE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=min(c1.low, c2.low),
                    explanation=[
                        "Bullish candle opens below prior close, closes above midpoint of prior bearish body",
                        f"Penetration: {(c2.close - c1.close) / (c1.open - c1.close):.2%}"
                    ]
                ))

            elif (c2.open > c1.close and c2.close < c1.open and
                  c2.close > c1.close and c2.open < c1.open and
                  a2["body"] <= a1["body"] * self.config.harami_threshold):
                detections.append(self._create_detection(
                    data, i, j, "BULLISH_HARAMI", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=min(c1.low, c2.low),
                    explanation=[
                        "Small bullish body contained within prior bearish body",
                        f"Harami ratio: {a2['body']/a1['body']:.2f}"
                    ]
                ))

        if a1["is_bullish"] and a2["is_bearish"]:
            if (c2.open > c1.close and c2.close < c1.open and
                a2["body"] >= a1["body"] * self.config.engulfing_threshold):
                detections.append(self._create_detection(
                    data, i, j, "BEARISH_ENGULFING", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=max(c1.high, c2.high),
                    target_levels={"target_1": c2.low - (max(c1.high, c2.high) - c2.low)},
                    explanation=[
                        f"Bearish candle body fully engulfs previous bullish body",
                        f"Engulfing ratio: {a2['body']/a1['body']:.2f}"
                    ]
                ))

            elif (c2.open < c1.close and c2.open > c1.open and c2.close < (c1.open + c1.close) / 2):
                detections.append(self._create_detection(
                    data, i, j, "DARK_CLOUD_COVER", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=max(c1.high, c2.high),
                    explanation=[
                        "Bearish candle opens above prior close, closes below midpoint of prior bullish body",
                        f"Penetration: {(c1.close - c2.close) / (c1.close - c1.open):.2%}"
                    ]
                ))

            elif (c2.open < c1.close and c2.close > c1.open and
                  c2.open > c1.open and c2.close < c1.close and
                  a2["body"] <= a1["body"] * self.config.harami_threshold):
                detections.append(self._create_detection(
                    data, i, j, "BEARISH_HARAMI", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=max(c1.high, c2.high),
                    explanation=[
                        "Small bearish body contained within prior bullish body",
                        f"Harami ratio: {a2['body']/a1['body']:.2f}"
                    ]
                ))

        if abs(c1.low - c2.low) / min(c1.low, c2.low) < self.config.tweezer_tolerance:
            if a1["is_bearish"] and a2["is_bullish"]:
                detections.append(self._create_detection(
                    data, i, j, "TWEEZER_BOTTOM", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=min(c1.low, c2.low),
                    explanation=[
                        f"Two consecutive candles with matching lows: {c1.low:.2f}, {c2.low:.2f}",
                        "Strong support level identified"
                    ]
                ))

        if abs(c1.high - c2.high) / min(c1.high, c2.high) < self.config.tweezer_tolerance:
            if a1["is_bullish"] and a2["is_bearish"]:
                detections.append(self._create_detection(
                    data, i, j, "TWEEZER_TOP", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low), "pattern_high": max(c1.high, c2.high)},
                    invalidation_level=max(c1.high, c2.high),
                    explanation=[
                        f"Two consecutive candles with matching highs: {c1.high:.2f}, {c2.high:.2f}",
                        "Strong resistance level identified"
                    ]
                ))

        return detections

    def _detect_three_candle(self, data: OHLCVData, i: int, j: int, k: int) -> List[PatternDetection]:
        c1 = data.candles[i]
        c2 = data.candles[j]
        c3 = data.candles[k]
        a1 = self._get_candle_analysis(i, data)
        a2 = self._get_candle_analysis(j, data)
        a3 = self._get_candle_analysis(k, data)
        detections = []

        if a1["is_bearish"] and a2["is_doji"] and a3["is_bullish"]:
            gap_down = c2.high < c1.low * (1 - self.config.star_gap_threshold)
            gap_up = c3.low > c2.high * (1 + self.config.star_gap_threshold)
            third_body_ok = a3["body_ratio"] >= self.config.morning_star_third_body

            if (gap_down or (c2.high < c1.low)) and (gap_up or (c3.low > c2.high)) and third_body_ok:
                detections.append(self._create_detection(
                    data, i, k, "MORNING_STAR", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low, c3.low), "pattern_high": max(c1.high, c2.high, c3.high)},
                    invalidation_level=min(c1.low, c2.low, c3.low),
                    target_levels={"target_1": c3.high + (c3.high - min(c1.low, c2.low, c3.low))},
                    explanation=[
                        "Three-candle bullish reversal: long bearish, doji/star, long bullish",
                        f"Third candle body ratio: {a3['body_ratio']:.2f}"
                    ]
                ))

        if a1["is_bullish"] and a2["is_doji"] and a3["is_bearish"]:
            gap_up = c2.low > c1.high * (1 + self.config.star_gap_threshold)
            gap_down = c3.high < c2.low * (1 - self.config.star_gap_threshold)
            third_body_ok = a3["body_ratio"] >= self.config.evening_star_third_body

            if (gap_up or (c2.low > c1.high)) and (gap_down or (c3.high < c2.low)) and third_body_ok:
                detections.append(self._create_detection(
                    data, i, k, "EVENING_STAR", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low, c3.low), "pattern_high": max(c1.high, c2.high, c3.high)},
                    invalidation_level=max(c1.high, c2.high, c3.high),
                    target_levels={"target_1": c3.low - (max(c1.high, c2.high, c3.high) - c3.low)},
                    explanation=[
                        "Three-candle bearish reversal: long bullish, doji/star, long bearish",
                        f"Third candle body ratio: {a3['body_ratio']:.2f}"
                    ]
                ))

        if all(a["is_bullish"] for a in [a1, a2, a3]):
            if all(a["body_ratio"] >= self.config.three_soldiers_min_body for a in [a1, a2, a3]):
                if c2.close > c1.close and c3.close > c2.close:
                    if c2.open > c1.open and c2.open < c1.close:
                        if c3.open > c2.open and c3.open < c2.close:
                            detections.append(self._create_detection(
                                data, i, k, "THREE_WHITE_SOLDIERS", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                                {"pattern_low": c1.low, "pattern_high": c3.high},
                                invalidation_level=c1.low,
                                target_levels={"target_1": c3.high + (c3.high - c1.low)},
                                explanation=[
                                    "Three consecutive long bullish candles with higher closes",
                                    "Each opens within previous body"
                                ]
                            ))

        if all(a["is_bearish"] for a in [a1, a2, a3]):
            if all(a["body_ratio"] >= self.config.three_crows_max_body for a in [a1, a2, a3]):
                if c2.close < c1.close and c3.close < c2.close:
                    if c2.open < c1.open and c2.open > c1.close:
                        if c3.open < c2.open and c3.open > c2.close:
                            detections.append(self._create_detection(
                                data, i, k, "THREE_BLACK_CROWS", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                                {"pattern_low": c3.low, "pattern_high": c1.high},
                                invalidation_level=c1.high,
                                target_levels={"target_1": c3.low - (c1.high - c3.low)},
                                explanation=[
                                    "Three consecutive long bearish candles with lower closes",
                                    "Each opens within previous body"
                                ]
                            ))

        if a1["is_bearish"] and a2["is_bullish"] and a3["is_bullish"]:
            if (c2.open > c1.close and c2.close < c1.open and
                c3.open > c2.open and c3.close > c2.close and
                c3.close > c1.open):
                detections.append(self._create_detection(
                    data, i, k, "THREE_OUTSIDE_UP", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low, c3.low), "pattern_high": max(c1.high, c2.high, c3.high)},
                    invalidation_level=min(c1.low, c2.low, c3.low),
                    explanation=[
                        "Bearish candle, bullish engulfing, then higher bullish close",
                        "Confirms bullish reversal"
                    ]
                ))

        if a1["is_bullish"] and a2["is_bearish"] and a3["is_bearish"]:
            if (c2.open < c1.close and c2.close > c1.open and
                c3.open < c2.open and c3.close < c2.close and
                c3.close < c1.open):
                detections.append(self._create_detection(
                    data, i, k, "THREE_OUTSIDE_DOWN", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low, c3.low), "pattern_high": max(c1.high, c2.high, c3.high)},
                    invalidation_level=max(c1.high, c2.high, c3.high),
                    explanation=[
                        "Bullish candle, bearish engulfing, then lower bearish close",
                        "Confirms bearish reversal"
                    ]
                ))

        if a1["is_bearish"] and a2["is_bullish"] and a3["is_bullish"]:
            if (c2.open > c1.open and c2.close < c1.close and
                c3.open > c2.open and c3.close < c2.close and
                c3.close > c1.close):
                detections.append(self._create_detection(
                    data, i, k, "THREE_INSIDE_UP", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low, c3.low), "pattern_high": max(c1.high, c2.high, c3.high)},
                    invalidation_level=min(c1.low, c2.low, c3.low),
                    explanation=[
                        "Bearish candle, bullish harami, then higher bullish close",
                        "Bullish reversal pattern"
                    ]
                ))

        if a1["is_bullish"] and a2["is_bearish"] and a3["is_bearish"]:
            if (c2.open < c1.open and c2.close > c1.close and
                c3.open < c2.open and c3.close > c2.close and
                c3.close < c1.close):
                detections.append(self._create_detection(
                    data, i, k, "THREE_INSIDE_DOWN", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"pattern_low": min(c1.low, c2.low, c3.low), "pattern_high": max(c1.high, c2.high, c3.high)},
                    invalidation_level=max(c1.high, c2.high, c3.high),
                    explanation=[
                        "Bullish candle, bearish harami, then lower bearish close",
                        "Bearish reversal pattern"
                    ]
                ))

        if (a1["is_bullish"] and a1["body_ratio"] > 0.6 and
            a2["is_bearish"] and a2["body_ratio"] < 0.4 and
            a3["is_bearish"] and a3["body_ratio"] < 0.4 and
            c2.low > c1.low and c2.high < c1.high and
            c3.low > c2.low and c3.high < c2.high and
            c3.close > c1.close):
            detections.append(self._create_detection(
                data, i, k, "RISING_THREE_METHODS", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                {"pattern_low": c1.low, "pattern_high": c1.high},
                invalidation_level=c1.low,
                explanation=[
                    "Long bullish, two small bearish within range, then bullish breaks out",
                    "Bullish continuation pattern"
                ]
            ))

        if (a1["is_bearish"] and a1["body_ratio"] > 0.6 and
            a2["is_bullish"] and a2["body_ratio"] < 0.4 and
            a3["is_bullish"] and a3["body_ratio"] < 0.4 and
            c2.high < c1.high and c2.low > c1.low and
            c3.high < c2.high and c3.low > c2.low and
            c3.close < c1.close):
            detections.append(self._create_detection(
                data, i, k, "FALLING_THREE_METHODS", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                {"pattern_low": c1.low, "pattern_high": c1.high},
                invalidation_level=c1.high,
                explanation=[
                    "Long bearish, two small bullish within range, then bearish breaks down",
                    "Bearish continuation pattern"
                ]
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

        start_ts = data.candles[start_idx].timestamp
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
            confirmation_timestamp=start_ts,
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


def register_candlestick_patterns(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(CandlestickPatternDetector())