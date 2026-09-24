from dataclasses import dataclass
from typing import List, Optional, Dict, Any
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
)
from app.patterns.indicators.technical import obv


@dataclass
class VolumeConfig:
    volume_sma_period: int = 20
    volume_spike_mult: float = 2.0
    volume_expansion_mult: float = 1.5
    volume_contraction_mult: float = 0.7
    climax_mult: float = 3.0
    breakout_volume_mult: float = 1.5
    low_volume_mult: float = 0.5
    obv_period: int = 20


class VolumePatternDetector(PatternDetector):
    def __init__(self, config: Optional[VolumeConfig] = None):
        self.config = config or VolumeConfig()

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="VOLUME_PATTERNS",
            category=PatternCategory.VOLUME,
            description="Volume and spread patterns: spikes, climax, breakouts, OBV, accumulation/distribution",
            required_candles=30,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "volume_sma_period": self.config.volume_sma_period,
                "volume_spike_mult": self.config.volume_spike_mult,
                "volume_expansion_mult": self.config.volume_expansion_mult,
                "volume_contraction_mult": self.config.volume_contraction_mult,
                "climax_mult": self.config.climax_mult,
                "breakout_volume_mult": self.config.breakout_volume_mult,
                "low_volume_mult": self.config.low_volume_mult,
            },
            confirmation_rules=[
                "Volume signals confirmed by price action",
                "Breakouts require volume expansion",
                "Climax requires extreme volume",
            ],
            invalidation_rules=[
                "Volume pattern fails if price reverses immediately",
            ],
            quality_factors=[
                "Volume magnitude",
                "Price-volume alignment",
                "Trend context",
                "Persistence of volume pattern",
            ],
        )

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        if len(data.candles) < self.definition.required_candles:
            return []

        volumes = np.array([c.volume for c in data.candles])
        closes = np.array([c.close for c in data.candles])
        highs = np.array([c.high for c in data.candles])
        lows = np.array([c.low for c in data.candles])

        vol_sma = pd.Series(volumes).rolling(self.config.volume_sma_period).mean().values
        obv_vals = obv(pd.Series(closes), pd.Series(volumes)).values

        detections = []
        idx = len(data.candles) - 1

        if idx >= self.config.volume_sma_period:
            detections.extend(self._check_volume_spike(data, volumes, vol_sma, idx))
            detections.extend(self._check_volume_expansion(data, volumes, vol_sma, idx))
            detections.extend(self._check_volume_contraction(data, volumes, vol_sma, idx))
            detections.extend(self._check_volume_climax(data, volumes, vol_sma, idx))
            detections.extend(self._check_high_volume_breakout(data, volumes, vol_sma, closes, idx))
            detections.extend(self._check_low_volume_breakout(data, volumes, vol_sma, closes, idx))
            detections.extend(self._check_volume_confirmation(data, volumes, vol_sma, closes, idx))
            detections.extend(self._check_obv_patterns(data, obv_vals, closes, idx))
            detections.extend(self._check_accumulation_distribution(data, volumes, closes, highs, lows, idx))

        return detections

    def _check_volume_spike(self, data: OHLCVData, volumes: np.ndarray, vol_sma: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if np.isnan(vol_sma[idx]) or vol_sma[idx] == 0:
            return detections

        ratio = volumes[idx] / vol_sma[idx]
        if ratio >= self.config.volume_spike_mult:
            detections.append(self._create_detection(
                data, idx - 5, idx, "VOLUME_SPIKE", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"volume": float(volumes[idx]), "avg_volume": float(vol_sma[idx]), "ratio": float(ratio)},
                explanation=[f"Volume spike: {ratio:.1f}x {self.config.volume_sma_period}-period average"]
            ))
        return detections

    def _check_volume_expansion(self, data: OHLCVData, volumes: np.ndarray, vol_sma: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if idx < 5 or np.isnan(vol_sma[idx]):
            return detections

        recent_vol = volumes[idx-4:idx+1].mean()
        if recent_vol > vol_sma[idx] * self.config.volume_expansion_mult:
            detections.append(self._create_detection(
                data, idx - 10, idx, "VOLUME_EXPANSION", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"recent_avg_volume": float(recent_vol), "sma_volume": float(vol_sma[idx]), "ratio": float(recent_vol / vol_sma[idx])},
                explanation=[f"Volume expanding: recent 5-bar avg {recent_vol/vol_sma[idx]:.1f}x SMA"]
            ))
        return detections

    def _check_volume_contraction(self, data: OHLCVData, volumes: np.ndarray, vol_sma: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if idx < 5 or np.isnan(vol_sma[idx]):
            return detections

        recent_vol = volumes[idx-4:idx+1].mean()
        if recent_vol < vol_sma[idx] * self.config.volume_contraction_mult:
            detections.append(self._create_detection(
                data, idx - 10, idx, "VOLUME_CONTRACTION", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"recent_avg_volume": float(recent_vol), "sma_volume": float(vol_sma[idx]), "ratio": float(recent_vol / vol_sma[idx])},
                explanation=[f"Volume contracting: recent 5-bar avg {recent_vol/vol_sma[idx]:.1f}x SMA"]
            ))
        return detections

    def _check_volume_climax(self, data: OHLCVData, volumes: np.ndarray, vol_sma: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if np.isnan(vol_sma[idx]) or vol_sma[idx] == 0:
            return detections

        ratio = volumes[idx] / vol_sma[idx]
        if ratio >= self.config.climax_mult:
            price_change = (data.candles[idx].close - data.candles[idx].open) / data.candles[idx].open
            direction = PatternDirection.BULLISH if price_change > 0 else PatternDirection.BEARISH
            detections.append(self._create_detection(
                data, idx - 3, idx, "VOLUME_CLIMAX", direction, PatternStatus.CONFIRMED,
                {"volume": float(volumes[idx]), "avg_volume": float(vol_sma[idx]), "ratio": float(ratio), "price_change_pct": float(price_change * 100)},
                explanation=[f"Volume climax: {ratio:.1f}x average on {'up' if price_change > 0 else 'down'} candle", "Potential exhaustion signal"]
            ))
        return detections

    def _check_high_volume_breakout(self, data: OHLCVData, volumes: np.ndarray, vol_sma: np.ndarray, closes: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if idx < 1 or np.isnan(vol_sma[idx]):
            return detections

        price_change = (closes[idx] - closes[idx-1]) / closes[idx-1]
        vol_ratio = volumes[idx] / vol_sma[idx]

        if abs(price_change) > 0.02 and vol_ratio >= self.config.breakout_volume_mult:
            direction = PatternDirection.BULLISH if price_change > 0 else PatternDirection.BEARISH
            detections.append(self._create_detection(
                data, idx - 5, idx, "HIGH_VOLUME_BREAKOUT", direction, PatternStatus.CONFIRMED,
                {"volume": float(volumes[idx]), "avg_volume": float(vol_sma[idx]), "price_change_pct": float(price_change * 100), "vol_ratio": float(vol_ratio)},
                explanation=[f"Breakout with volume: {price_change*100:.1f}% price move, {vol_ratio:.1f}x volume"]
            ))
        return detections

    def _check_low_volume_breakout(self, data: OHLCVData, volumes: np.ndarray, vol_sma: np.ndarray, closes: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if idx < 1 or np.isnan(vol_sma[idx]):
            return detections

        price_change = (closes[idx] - closes[idx-1]) / closes[idx-1]
        vol_ratio = volumes[idx] / vol_sma[idx]

        if abs(price_change) > 0.02 and vol_ratio <= self.config.low_volume_mult:
            direction = PatternDirection.BULLISH if price_change > 0 else PatternDirection.BEARISH
            detections.append(self._create_detection(
                data, idx - 5, idx, "LOW_VOLUME_BREAKOUT", direction, PatternStatus.FORMING,
                {"volume": float(volumes[idx]), "avg_volume": float(vol_sma[idx]), "price_change_pct": float(price_change * 100), "vol_ratio": float(vol_ratio)},
                explanation=[f"Breakout on low volume: {price_change*100:.1f}% move, {vol_ratio:.1f}x volume", "Suspect breakout - possible false move"]
            ))
        return detections

    def _check_volume_confirmation(self, data: OHLCVData, volumes: np.ndarray, vol_sma: np.ndarray, closes: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if idx < 3:
            return detections

        price_trend = closes[idx] - closes[idx-3]
        vol_trend = volumes[idx] - np.mean(volumes[idx-3:idx])

        if price_trend > 0 and vol_trend > 0:
            detections.append(self._create_detection(
                data, idx - 3, idx, "VOLUME_CONFIRMATION_BULLISH", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                {"price_change": float(price_trend), "volume_trend": float(vol_trend)},
                explanation=["Price rising with increasing volume", "Bullish volume confirmation"]
            ))
        elif price_trend < 0 and vol_trend > 0:
            detections.append(self._create_detection(
                data, idx - 3, idx, "VOLUME_CONFIRMATION_BEARISH", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                {"price_change": float(price_trend), "volume_trend": float(vol_trend)},
                explanation=["Price falling with increasing volume", "Bearish volume confirmation"]
            ))
        elif price_trend > 0 and vol_trend < 0:
            detections.append(self._create_detection(
                data, idx - 3, idx, "VOLUME_DIVERGENCE_BULLISH", PatternDirection.BEARISH, PatternStatus.FORMING,
                {"price_change": float(price_trend), "volume_trend": float(vol_trend)},
                explanation=["Price rising but volume decreasing", "Bearish volume divergence - warning"]
            ))
        elif price_trend < 0 and vol_trend < 0:
            detections.append(self._create_detection(
                data, idx - 3, idx, "VOLUME_DIVERGENCE_BEARISH", PatternDirection.BULLISH, PatternStatus.FORMING,
                {"price_change": float(price_trend), "volume_trend": float(vol_trend)},
                explanation=["Price falling but volume decreasing", "Bullish volume divergence - potential reversal"]
            ))
        return detections

    def _check_obv_patterns(self, data: OHLCVData, obv_vals: np.ndarray, closes: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if idx < 5 or np.isnan(obv_vals[idx]):
            return detections

        obv_slope = obv_vals[idx] - obv_vals[idx-5]
        price_slope = closes[idx] - closes[idx-5]

        if obv_slope > 0 and price_slope <= 0:
            detections.append(self._create_detection(
                data, idx - 5, idx, "OBV_BULLISH_DIVERGENCE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                {"obv_change": float(obv_slope), "price_change": float(price_slope)},
                explanation=["OBV rising while price flat/declining", "Accumulation signal"]
            ))
        elif obv_slope < 0 and price_slope >= 0:
            detections.append(self._create_detection(
                data, idx - 5, idx, "OBV_BEARISH_DIVERGENCE", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                {"obv_change": float(obv_slope), "price_change": float(price_slope)},
                explanation=["OBV falling while price flat/rising", "Distribution signal"]
            ))

        if idx >= 20:
            obv_high = max(obv_vals[idx-20:idx+1])
            obv_low = min(obv_vals[idx-20:idx+1])
            if obv_vals[idx] >= obv_high * 0.99:
                detections.append(self._create_detection(
                    data, idx - 20, idx, "OBV_BREAKOUT", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"obv": float(obv_vals[idx]), "20_bar_high": float(obv_high)},
                    explanation=["OBV at 20-bar high", "Strong buying pressure"]
                ))
            elif obv_vals[idx] <= obv_low * 1.01:
                detections.append(self._create_detection(
                    data, idx - 20, idx, "OBV_BREAKDOWN", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"obv": float(obv_vals[idx]), "20_bar_low": float(obv_low)},
                    explanation=["OBV at 20-bar low", "Strong selling pressure"]
                ))

        return detections

    def _check_accumulation_distribution(self, data: OHLCVData, volumes: np.ndarray, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray, idx: int) -> List[PatternDetection]:
        detections = []
        if idx < 10:
            return detections

        mfm = ((closes - lows) - (highs - closes)) / (highs - lows)
        mfm = np.nan_to_num(mfm, nan=0.0)
        mfv = mfm * volumes
        ad_line = np.cumsum(mfv)

        ad_slope = ad_line[idx] - ad_line[idx-10]
        price_slope = closes[idx] - closes[idx-10]

        if ad_slope > 0 and price_slope <= 0:
            detections.append(self._create_detection(
                data, idx - 10, idx, "ACCUMULATION", PatternDirection.BULLISH, PatternStatus.FORMING,
                {"ad_change": float(ad_slope), "price_change": float(price_slope)},
                explanation=["Accumulation/Distribution line rising while price flat/declining", "Smart money accumulating"]
            ))
        elif ad_slope < 0 and price_slope >= 0:
            detections.append(self._create_detection(
                data, idx - 10, idx, "DISTRIBUTION", PatternDirection.BEARISH, PatternStatus.FORMING,
                {"ad_change": float(ad_slope), "price_change": float(price_slope)},
                explanation=["Accumulation/Distribution line falling while price flat/rising", "Smart money distributing"]
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


def register_volume_patterns(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(VolumePatternDetector())