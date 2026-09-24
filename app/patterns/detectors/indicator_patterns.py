from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from app.patterns.detectors.base import PatternDetector, DetectorContext
from app.patterns.models import (
    PatternDefinition,
    PatternDetection,
    PatternCategory,
    PatternDirection,
    PatternStatus,
    OHLCVData,
)
from app.patterns.indicators.technical import (
    add_all_indicators, crossover, crossunder, IndicatorConfig,
    sma, ema, rsi, macd, bollinger_bands, stochastic, atr, obv
)


@dataclass
class IndicatorPatternConfig:
    sma_period: int = 50
    ema_period: int = 20
    ema_short: int = 9
    ema_medium: int = 21
    ema_long: int = 50
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    bb_squeeze_threshold: float = 0.05
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_overbought: float = 80
    stoch_oversold: float = 20
    atr_period: int = 14
    atr_expansion_mult: float = 1.5
    atr_contraction_mult: float = 0.7
    volume_period: int = 20
    volume_spike_mult: float = 2.0


class IndicatorPatternDetector(PatternDetector):
    def __init__(self, config: Optional[IndicatorPatternConfig] = None):
        self.config = config or IndicatorPatternConfig()

    @property
    def definition(self) -> PatternDefinition:
        return PatternDefinition(
            name="INDICATOR_PATTERNS",
            category=PatternCategory.INDICATOR_PATTERN,
            description="Comprehensive indicator-based pattern detection",
            required_candles=60,
            direction=PatternDirection.NEUTRAL,
            parameters={
                "sma_period": self.config.sma_period,
                "ema_period": self.config.ema_period,
                "ema_short": self.config.ema_short,
                "ema_medium": self.config.ema_medium,
                "ema_long": self.config.ema_long,
                "rsi_period": self.config.rsi_period,
                "rsi_overbought": self.config.rsi_overbought,
                "rsi_oversold": self.config.rsi_oversold,
                "macd_fast": self.config.macd_fast,
                "macd_slow": self.config.macd_slow,
                "macd_signal": self.config.macd_signal,
                "bb_period": self.config.bb_period,
                "bb_std": self.config.bb_std,
                "bb_squeeze_threshold": self.config.bb_squeeze_threshold,
                "stoch_k": self.config.stoch_k,
                "stoch_d": self.config.stoch_d,
                "stoch_overbought": self.config.stoch_overbought,
                "stoch_oversold": self.config.stoch_oversold,
                "atr_period": self.config.atr_period,
                "atr_expansion_mult": self.config.atr_expansion_mult,
                "atr_contraction_mult": self.config.atr_contraction_mult,
                "volume_period": self.config.volume_period,
                "volume_spike_mult": self.config.volume_spike_mult,
            },
            confirmation_rules=[
                "Price action confirmation required",
                "Volume confirmation for breakouts",
                "Trend alignment check",
            ],
            invalidation_rules=[
                "Pattern invalidated if price reverses beyond key level",
            ],
            quality_factors=[
                "Multiple indicator alignment",
                "Volume confirmation",
                "Trend strength",
                "Risk/reward ratio",
            ],
        )

    def _prepare_indicators(self, data: OHLCVData) -> pd.DataFrame:
        df = pd.DataFrame([{
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        } for c in data.candles])
        df.set_index("timestamp", inplace=True)

        indicator_config = IndicatorConfig(
            sma_period=self.config.sma_period,
            ema_period=self.config.ema_period,
            wma_period=self.config.ema_period,
            rsi_period=self.config.rsi_period,
            macd_fast=self.config.macd_fast,
            macd_slow=self.config.macd_slow,
            macd_signal=self.config.macd_signal,
            bb_period=self.config.bb_period,
            bb_std=self.config.bb_std,
            stoch_k=self.config.stoch_k,
            stoch_d=self.config.stoch_d,
            stoch_smooth=3,
            atr_period=self.config.atr_period,
        )
        return add_all_indicators(df, indicator_config)

    def detect(self, data: OHLCVData, context: Optional[DetectorContext] = None) -> List[PatternDetection]:
        if len(data.candles) < self.definition.required_candles:
            return []

        df = self._prepare_indicators(data)
        detections = []
        last_idx = len(df) - 1

        detections.extend(self._detect_ma_patterns(data, df, last_idx))
        detections.extend(self._detect_rsi_patterns(data, df, last_idx))
        detections.extend(self._detect_macd_patterns(data, df, last_idx))
        detections.extend(self._detect_bb_patterns(data, df, last_idx))
        detections.extend(self._detect_stochastic_patterns(data, df, last_idx))
        detections.extend(self._detect_atr_patterns(data, df, last_idx))
        detections.extend(self._detect_volume_patterns(data, df, last_idx))

        return detections

    def _detect_ma_patterns(self, data: OHLCVData, df: pd.DataFrame, idx: int) -> List[PatternDetection]:
        detections = []
        close = df["close"]
        sma_50 = df.get(f"SMA_{self.config.sma_period}")
        ema_20 = df.get(f"EMA_{self.config.ema_period}")
        ema_short = ema(close, self.config.ema_short) if self.config.ema_short else None
        ema_medium = ema(close, self.config.ema_medium) if self.config.ema_medium else None
        ema_long = ema(close, self.config.ema_long) if self.config.ema_long else None

        if sma_50 is not None and ema_20 is not None and idx >= 1:
            if crossover(ema_20, sma_50).iloc[idx]:
                detections.append(self._create_detection(
                    data, idx - 5, idx, "GOLDEN_CROSS", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"ema_20": float(ema_20.iloc[idx]), "sma_50": float(sma_50.iloc[idx]), "price": float(close.iloc[idx])},
                    explanation=["EMA 20 crossed above SMA 50", "Bullish trend change signal"]
                ))
            elif crossunder(ema_20, sma_50).iloc[idx]:
                detections.append(self._create_detection(
                    data, idx - 5, idx, "DEATH_CROSS", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"ema_20": float(ema_20.iloc[idx]), "sma_50": float(sma_50.iloc[idx]), "price": float(close.iloc[idx])},
                    explanation=["EMA 20 crossed below SMA 50", "Bearish trend change signal"]
                ))

        if all(v is not None for v in [ema_short, ema_medium, ema_long]) and idx >= 1:
            es, em, el = ema_short.iloc[idx], ema_medium.iloc[idx], ema_long.iloc[idx]
            es_p, em_p, el_p = ema_short.iloc[idx-1], ema_medium.iloc[idx-1], ema_long.iloc[idx-1]

            if es > em > el and es_p <= em_p <= el_p:
                detections.append(self._create_detection(
                    data, idx - 10, idx, "BULLISH_MA_ALIGNMENT", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"ema_short": float(es), "ema_medium": float(em), "ema_long": float(el), "price": float(close.iloc[idx])},
                    explanation=["Short EMA > Medium EMA > Long EMA", "Bullish alignment confirmed"]
                ))
            elif es < em < el and es_p >= em_p >= el_p:
                detections.append(self._create_detection(
                    data, idx - 10, idx, "BEARISH_MA_ALIGNMENT", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"ema_short": float(es), "ema_medium": float(em), "ema_long": float(el), "price": float(close.iloc[idx])},
                    explanation=["Short EMA < Medium EMA < Long EMA", "Bearish alignment confirmed"]
                ))

        if ema_medium is not None and idx >= 2:
            price = close.iloc[idx]
            ema_m = ema_medium.iloc[idx]
            prev_low = min(data.candles[idx-1].low, data.candles[idx-2].low)

            if price > ema_m and prev_low <= ema_medium.iloc[idx-1] <= ema_medium.iloc[idx-2]:
                detections.append(self._create_detection(
                    data, idx - 5, idx, "EMA_PULLBACK", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"ema_medium": float(ema_m), "price": float(price), "pullback_low": float(prev_low)},
                    invalidation_level=float(prev_low),
                    explanation=["Price pulled back to EMA medium and held", "Bullish continuation setup"]
                ))

        if sma_50 is not None and ema_20 is not None and idx >= 20:
            ma_diff = abs(ema_20.iloc[idx] - sma_50.iloc[idx]) / close.iloc[idx]
            if ma_diff < 0.01:
                detections.append(self._create_detection(
                    data, idx - 20, idx, "MA_COMPRESSION", PatternDirection.NEUTRAL, PatternStatus.FORMING,
                    {"ema_20": float(ema_20.iloc[idx]), "sma_50": float(sma_50.iloc[idx]), "price": float(close.iloc[idx])},
                    explanation=["EMA 20 and SMA 50 converging", "Potential breakout imminent"]
                ))

        return detections

    def _detect_rsi_patterns(self, data: OHLCVData, df: pd.DataFrame, idx: int) -> List[PatternDetection]:
        detections = []
        rsi_col = f"RSI_{self.config.rsi_period}"
        rsi_vals = df.get(rsi_col)
        close = df["close"]

        if rsi_vals is None or pd.isna(rsi_vals.iloc[idx]):
            return detections

        rsi_val = rsi_vals.iloc[idx]

        if rsi_val >= self.config.rsi_overbought:
            detections.append(self._create_detection(
                data, idx - 3, idx, "RSI_OVERBOUGHT", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                {"rsi": float(rsi_val), "price": float(close.iloc[idx])},
                explanation=[f"RSI({self.config.rsi_period}) = {rsi_val:.1f} >= {self.config.rsi_overbought}", "Overbought condition"]
            ))
        elif rsi_val <= self.config.rsi_oversold:
            detections.append(self._create_detection(
                data, idx - 3, idx, "RSI_OVERSOLD", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                {"rsi": float(rsi_val), "price": float(close.iloc[idx])},
                explanation=[f"RSI({self.config.rsi_period}) = {rsi_val:.1f} <= {self.config.rsi_oversold}", "Oversold condition"]
            ))

        if idx >= 5:
            for lookback in [5, 10, 14]:
                if idx >= lookback:
                    price_lows = [data.candles[idx - i].low for i in range(lookback + 1)]
                    rsi_lows = [rsi_vals.iloc[idx - i] for i in range(lookback + 1)]
                    if all(not pd.isna(v) for v in rsi_lows):
                        price_ll_idx = np.argmin(price_lows)
                        rsi_ll_idx = np.argmin(rsi_lows)
                        if price_ll_idx == 0 and rsi_ll_idx > 0 and price_lows[0] < price_lows[rsi_ll_idx] and rsi_lows[0] > rsi_lows[rsi_ll_idx]:
                            detections.append(self._create_detection(
                                data, idx - lookback, idx, "BULLISH_RSI_DIVERGENCE", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                                {"rsi": float(rsi_val), "price": float(close.iloc[idx]), "divergence_lookback": lookback},
                                explanation=[f"Bullish RSI divergence over {lookback} bars", "Price lower low, RSI higher low"]
                            ))
                            break

        if idx >= 5:
            for lookback in [5, 10, 14]:
                if idx >= lookback:
                    price_highs = [data.candles[idx - i].high for i in range(lookback + 1)]
                    rsi_highs = [rsi_vals.iloc[idx - i] for i in range(lookback + 1)]
                    if all(not pd.isna(v) for v in rsi_highs):
                        price_hh_idx = np.argmax(price_highs)
                        rsi_hh_idx = np.argmax(rsi_highs)
                        if price_hh_idx == 0 and rsi_hh_idx > 0 and price_highs[0] > price_highs[rsi_hh_idx] and rsi_highs[0] < rsi_highs[rsi_hh_idx]:
                            detections.append(self._create_detection(
                                data, idx - lookback, idx, "BEARISH_RSI_DIVERGENCE", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                                {"rsi": float(rsi_val), "price": float(close.iloc[idx]), "divergence_lookback": lookback},
                                explanation=[f"Bearish RSI divergence over {lookback} bars", "Price higher high, RSI lower high"]
                            ))
                            break

        return detections

    def _detect_macd_patterns(self, data: OHLCVData, df: pd.DataFrame, idx: int) -> List[PatternDetection]:
        detections = []
        macd_col = f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"
        signal_col = f"MACD_SIGNAL_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"
        hist_col = f"MACD_HIST_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"

        macd_line = df.get(macd_col)
        signal_line = df.get(signal_col)
        histogram = df.get(hist_col)
        close = df["close"]

        if macd_line is None or signal_line is None or pd.isna(macd_line.iloc[idx]):
            return detections

        if idx >= 1:
            if crossover(macd_line, signal_line).iloc[idx]:
                detections.append(self._create_detection(
                    data, idx - 5, idx, "BULLISH_MACD_CROSSOVER", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"macd": float(macd_line.iloc[idx]), "signal": float(signal_line.iloc[idx]), "price": float(close.iloc[idx])},
                    explanation=["MACD line crossed above signal line", "Bullish momentum signal"]
                ))
            elif crossunder(macd_line, signal_line).iloc[idx]:
                detections.append(self._create_detection(
                    data, idx - 5, idx, "BEARISH_MACD_CROSSOVER", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"macd": float(macd_line.iloc[idx]), "signal": float(signal_line.iloc[idx]), "price": float(close.iloc[idx])},
                    explanation=["MACD line crossed below signal line", "Bearish momentum signal"]
                ))

        if histogram is not None and idx >= 1:
            if histogram.iloc[idx-1] < 0 and histogram.iloc[idx] > 0:
                detections.append(self._create_detection(
                    data, idx - 3, idx, "MACD_ZERO_LINE_CROSS_UP", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"macd": float(macd_line.iloc[idx]), "histogram": float(histogram.iloc[idx]), "price": float(close.iloc[idx])},
                    explanation=["MACD histogram crossed above zero", "Bullish momentum accelerating"]
                ))
            elif histogram.iloc[idx-1] > 0 and histogram.iloc[idx] < 0:
                detections.append(self._create_detection(
                    data, idx - 3, idx, "MACD_ZERO_LINE_CROSS_DOWN", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"macd": float(macd_line.iloc[idx]), "histogram": float(histogram.iloc[idx]), "price": float(close.iloc[idx])},
                    explanation=["MACD histogram crossed below zero", "Bearish momentum accelerating"]
                ))

        return detections

    def _detect_bb_patterns(self, data: OHLCVData, df: pd.DataFrame, idx: int) -> List[PatternDetection]:
        detections = []
        upper = df.get(f"BB_UPPER_{self.config.bb_period}_{self.config.bb_std}")
        middle = df.get(f"BB_MIDDLE_{self.config.bb_period}_{self.config.bb_std}")
        lower = df.get(f"BB_LOWER_{self.config.bb_period}_{self.config.bb_std}")
        width = df.get(f"BB_WIDTH_{self.config.bb_period}_{self.config.bb_std}")
        close = df["close"]
        high = df["high"]
        low = df["low"]

        if any(v is None for v in [upper, middle, lower, width]) or pd.isna(upper.iloc[idx]):
            return detections

        if high.iloc[idx] > upper.iloc[idx] and close.iloc[idx] > upper.iloc[idx]:
            detections.append(self._create_detection(
                data, idx - 3, idx, "BB_UPPER_BREAKOUT", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                {"upper_band": float(upper.iloc[idx]), "price": float(close.iloc[idx]), "middle_band": float(middle.iloc[idx])},
                invalidation_level=float(middle.iloc[idx]),
                explanation=[f"Price closed above upper Bollinger Band ({upper.iloc[idx]:.2f})", "Bullish breakout signal"]
            ))

        if low.iloc[idx] < lower.iloc[idx] and close.iloc[idx] < lower.iloc[idx]:
            detections.append(self._create_detection(
                data, idx - 3, idx, "BB_LOWER_BREAKDOWN", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                {"lower_band": float(lower.iloc[idx]), "price": float(close.iloc[idx]), "middle_band": float(middle.iloc[idx])},
                invalidation_level=float(middle.iloc[idx]),
                explanation=[f"Price closed below lower Bollinger Band ({lower.iloc[idx]:.2f})", "Bearish breakdown signal"]
            ))

        if width.iloc[idx] < self.config.bb_squeeze_threshold:
            detections.append(self._create_detection(
                data, idx - 10, idx, "BOLLINGER_SQUEEZE", PatternDirection.NEUTRAL, PatternStatus.FORMING,
                {"bandwidth": float(width.iloc[idx]), "upper": float(upper.iloc[idx]), "lower": float(lower.iloc[idx])},
                explanation=[f"Bollinger Band width = {width.iloc[idx]:.4f} < {self.config.bb_squeeze_threshold}", "Low volatility, breakout expected"]
            ))

        if idx >= 5 and width.iloc[idx] > width.iloc[idx-5] * 1.5:
            detections.append(self._create_detection(
                data, idx - 5, idx, "BOLLINGER_EXPANSION", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"bandwidth": float(width.iloc[idx]), "prev_bandwidth": float(width.iloc[idx-5])},
                explanation=["Bollinger Bands expanding rapidly", "Volatility increasing"]
            ))

        return detections

    def _detect_stochastic_patterns(self, data: OHLCVData, df: pd.DataFrame, idx: int) -> List[PatternDetection]:
        detections = []
        stoch_k = df.get(f"STOCH_K_{self.config.stoch_k}_{self.config.stoch_d}_{3}")
        stoch_d = df.get(f"STOCH_D_{self.config.stoch_k}_{self.config.stoch_d}_{3}")

        if stoch_k is None or stoch_d is None or pd.isna(stoch_k.iloc[idx]):
            return detections

        k_val = stoch_k.iloc[idx]
        d_val = stoch_d.iloc[idx]

        if idx >= 1:
            if crossover(stoch_k, stoch_d).iloc[idx] and k_val < self.config.stoch_oversold:
                detections.append(self._create_detection(
                    data, idx - 3, idx, "STOCH_BULLISH_CROSSOVER", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                    {"stoch_k": float(k_val), "stoch_d": float(d_val)},
                    explanation=[f"Stochastic %K crossed above %D in oversold zone ({k_val:.1f})", "Bullish reversal signal"]
                ))
            elif crossunder(stoch_k, stoch_d).iloc[idx] and k_val > self.config.stoch_overbought:
                detections.append(self._create_detection(
                    data, idx - 3, idx, "STOCH_BEARISH_CROSSOVER", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                    {"stoch_k": float(k_val), "stoch_d": float(d_val)},
                    explanation=[f"Stochastic %K crossed below %D in overbought zone ({k_val:.1f})", "Bearish reversal signal"]
                ))

        if k_val >= self.config.stoch_overbought and d_val >= self.config.stoch_overbought:
            detections.append(self._create_detection(
                data, idx - 2, idx, "STOCH_OVERBOUGHT", PatternDirection.BEARISH, PatternStatus.CONFIRMED,
                {"stoch_k": float(k_val), "stoch_d": float(d_val)},
                explanation=[f"Stochastic overbought: %K={k_val:.1f}, %D={d_val:.1f}"]
            ))
        elif k_val <= self.config.stoch_oversold and d_val <= self.config.stoch_oversold:
            detections.append(self._create_detection(
                data, idx - 2, idx, "STOCH_OVERSOLD", PatternDirection.BULLISH, PatternStatus.CONFIRMED,
                {"stoch_k": float(k_val), "stoch_d": float(d_val)},
                explanation=[f"Stochastic oversold: %K={k_val:.1f}, %D={d_val:.1f}"]
            ))

        return detections

    def _detect_atr_patterns(self, data: OHLCVData, df: pd.DataFrame, idx: int) -> List[PatternDetection]:
        detections = []
        atr_col = f"ATR_{self.config.atr_period}"
        atr_vals = df.get(atr_col)

        if atr_vals is None or pd.isna(atr_vals.iloc[idx]) or idx < 10:
            return detections

        atr_val = atr_vals.iloc[idx]
        atr_avg = atr_vals.iloc[idx-10:idx].mean()

        if atr_val > atr_avg * self.config.atr_expansion_mult:
            detections.append(self._create_detection(
                data, idx - 10, idx, "ATR_EXPANSION", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"atr": float(atr_val), "atr_avg": float(atr_avg), "ratio": float(atr_val / atr_avg)},
                explanation=[f"ATR expanded to {atr_val:.2f} (avg: {atr_avg:.2f})", "Volatility increasing significantly"]
            ))
        elif atr_val < atr_avg * self.config.atr_contraction_mult:
            detections.append(self._create_detection(
                data, idx - 10, idx, "ATR_CONTRACTION", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"atr": float(atr_val), "atr_avg": float(atr_avg), "ratio": float(atr_val / atr_avg)},
                explanation=[f"ATR contracted to {atr_val:.2f} (avg: {atr_avg:.2f})", "Volatility decreasing"]
            ))

        return detections

    def _detect_volume_patterns(self, data: OHLCVData, df: pd.DataFrame, idx: int) -> List[PatternDetection]:
        detections = []
        volume = df["volume"]
        avg_vol = volume.rolling(self.config.volume_period).mean()

        if idx < self.config.volume_period or pd.isna(avg_vol.iloc[idx]):
            return detections

        vol_ratio = volume.iloc[idx] / avg_vol.iloc[idx]

        if vol_ratio > self.config.volume_spike_mult:
            detections.append(self._create_detection(
                data, idx - 3, idx, "VOLUME_SPIKE", PatternDirection.NEUTRAL, PatternStatus.CONFIRMED,
                {"volume": float(volume.iloc[idx]), "avg_volume": float(avg_vol.iloc[idx]), "ratio": float(vol_ratio)},
                explanation=[f"Volume spike: {vol_ratio:.1f}x average", "Unusual activity detected"]
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


def register_indicator_patterns(registry=None):
    if registry is None:
        from app.patterns.registry import get_registry
        registry = get_registry()
    registry.register(IndicatorPatternDetector())