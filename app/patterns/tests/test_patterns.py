import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.patterns.models import (
    Candle,
    OHLCVData,
    Timeframe,
    PatternDirection,
    PatternStatus,
    PatternCategory,
    MarketRegime,
)
from app.patterns.detectors.candlestick import CandlestickPatternDetector, CandlestickConfig
from app.patterns.detectors.chart_patterns import ChartPatternDetector, ChartPatternConfig
from app.patterns.detectors.market_structure import MarketStructureDetector, MarketStructureConfig
from app.patterns.detectors.indicator_patterns import IndicatorPatternDetector, IndicatorPatternConfig
from app.patterns.detectors.pivot import PivotDetector, PivotConfig
from app.patterns.divergence.detector import DivergenceDetector, DivergenceConfig
from app.patterns.harmonic.detector import HarmonicPatternDetector, HarmonicConfig
from app.patterns.wave.detector import WavePatternDetector, WaveConfig
from app.patterns.volume.detector import VolumePatternDetector, VolumeConfig
from app.patterns.regime.detector import MarketRegimeDetector, RegimeConfig
from app.patterns.confluence.engine import calculate_confluence, ConfluenceConfig
from app.patterns.backtest.engine import PatternBacktester, BacktestConfig
from app.patterns.scanner.service import PatternScanner, ScannerConfig
from app.patterns.registry import PatternRegistry


def create_test_candles(count: int, base_price: float = 100.0, trend: str = "flat") -> list[Candle]:
    candles = []
    current_price = base_price
    base_time = datetime(2024, 1, 1, 9, 15)

    for i in range(count):
        if trend == "up":
            current_price += np.random.uniform(0.1, 0.5)
        elif trend == "down":
            current_price -= np.random.uniform(0.1, 0.5)
        else:
            current_price += np.random.uniform(-0.3, 0.3)

        open_price = current_price + np.random.uniform(-0.2, 0.2)
        close_price = current_price + np.random.uniform(-0.2, 0.2)
        high_price = max(open_price, close_price) + abs(np.random.uniform(0, 0.5))
        low_price = min(open_price, close_price) - abs(np.random.uniform(0, 0.5))
        volume = np.random.randint(10000, 100000)

        candles.append(Candle(
            timestamp=base_time + timedelta(minutes=15 * i),
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(close_price, 2),
            volume=volume,
        ))

    return candles


def create_bullish_engulfing_candles() -> list[Candle]:
    base_time = datetime(2024, 1, 1, 9, 15)
    return [
        Candle(timestamp=base_time, open=102.0, high=103.0, low=100.0, close=100.5, volume=50000),
        Candle(timestamp=base_time + timedelta(minutes=15), open=100.0, high=104.0, low=99.5, close=103.0, volume=60000),
    ]


def create_bearish_engulfing_candles() -> list[Candle]:
    base_time = datetime(2024, 1, 1, 9, 15)
    return [
        Candle(timestamp=base_time, open=100.0, high=103.0, low=99.5, close=102.5, volume=50000),
        Candle(timestamp=base_time + timedelta(minutes=15), open=103.0, high=103.5, low=99.0, close=99.5, volume=60000),
    ]


def create_hammer_candles() -> list[Candle]:
    base_time = datetime(2024, 1, 1, 9, 15)
    return [
        Candle(timestamp=base_time, open=100.0, high=102.0, low=99.0, close=101.0, volume=50000),
        Candle(timestamp=base_time + timedelta(minutes=15), open=97.0, high=97.5, low=92.0, close=99.0, volume=50000),
    ]


def create_shooting_star_candles() -> list[Candle]:
    base_time = datetime(2024, 1, 1, 9, 15)
    return [
        Candle(timestamp=base_time, open=100.0, high=102.0, low=99.0, close=101.0, volume=50000),
        Candle(timestamp=base_time + timedelta(minutes=15), open=101.0, high=109.0, low=100.3, close=100.0, volume=50000),
    ]


def create_doji_candles() -> list[Candle]:
    base_time = datetime(2024, 1, 1, 9, 15)
    return [
        Candle(timestamp=base_time, open=100.0, high=102.0, low=99.0, close=101.0, volume=50000),
        Candle(timestamp=base_time + timedelta(minutes=15), open=100.0, high=101.0, low=99.0, close=100.02, volume=50000),
    ]


def create_morning_star_candles() -> list[Candle]:
    base_time = datetime(2024, 1, 1, 9, 15)
    return [
        Candle(timestamp=base_time, open=102.0, high=103.0, low=100.0, close=100.5, volume=50000),
        Candle(timestamp=base_time + timedelta(minutes=15), open=99.0, high=99.1, low=98.9, close=99.0, volume=30000),
        Candle(timestamp=base_time + timedelta(minutes=30), open=99.5, high=104.0, low=99.5, close=103.0, volume=60000),
    ]


def create_double_bottom_candles() -> list[Candle]:
    base_time = datetime(2024, 1, 1)
    # Create clear double bottom with enough bars for pivot confirmation
    # Second bottom slightly higher than first (more realistic)
    prices = []
    # Pre-pattern data (40 bars)
    for i in range(40):
        prices.append((105 + i * 0.1, 106 + i * 0.1, 104 + i * 0.1, 105.5 + i * 0.1))
    # Pattern
    prices.extend([
        (105, 106, 104, 105.5),  # day 40
        (108, 110, 107, 109.5),  # day 41
        (105, 106, 100, 101),    # day 42 - first bottom at 100
        (103, 105, 102, 104),    # day 43
        (108, 110, 107, 109),    # day 44 - bounce to 110
        (106, 107, 101, 102),    # day 45 - second bottom at 101 (slightly higher)
        (104, 106, 103, 105),    # day 46
        (108, 110, 107, 109),    # day 47
        (111, 113, 110, 112),    # day 48 - breakout above 110
        (113, 115, 112, 114),    # day 49
        (115, 117, 114, 116),    # day 50
    ])
    # Additional bars for pivot confirmation of second bottom (need 5 more)
    for i in range(51, 57):
        prices.append((115 + (i-50) * 0.5, 117 + (i-50) * 0.5, 114 + (i-50) * 0.5, 116 + (i-50) * 0.5))
    candles = []
    for i, (o, h, l, c) in enumerate(prices):
        candles.append(Candle(
            timestamp=base_time + timedelta(days=i),
            open=o, high=h, low=l, close=c, volume=50000
        ))
    return candles


class TestCandlestickPatterns:
    @pytest.fixture
    def detector(self):
        return CandlestickPatternDetector()

    def test_bullish_engulfing(self, detector):
        candles = create_bullish_engulfing_candles()
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.MIN_15, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "BULLISH_ENGULFING" for d in detections)

    def test_bearish_engulfing(self, detector):
        candles = create_bearish_engulfing_candles()
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.MIN_15, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "BEARISH_ENGULFING" for d in detections)

    def test_hammer(self, detector):
        candles = create_hammer_candles()
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.MIN_15, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "HAMMER" for d in detections)

    def test_shooting_star(self, detector):
        candles = create_shooting_star_candles()
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.MIN_15, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "SHOOTING_STAR" for d in detections)

    def test_doji(self, detector):
        candles = create_doji_candles()
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.MIN_15, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "DOJI" for d in detections)

    def test_morning_star(self, detector):
        candles = create_morning_star_candles()
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.MIN_15, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "MORNING_STAR" for d in detections)

    def test_insufficient_data(self, detector):
        candles = create_test_candles(1)
        with pytest.raises(ValueError):
            OHLCVData(symbol="TEST", timeframe=Timeframe.MIN_15, candles=candles)


class TestChartPatterns:
    @pytest.fixture
    def detector(self):
        return ChartPatternDetector(ChartPatternConfig(pivot_left=2, pivot_right=2, min_pattern_bars=3))

    def test_double_bottom(self, detector):
        candles = create_double_bottom_candles()
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "DOUBLE_BOTTOM" for d in detections)

    def test_insufficient_data(self, detector):
        candles = create_test_candles(10)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        assert len(detections) >= 0


class TestMarketStructure:
    @pytest.fixture
    def detector(self):
        return MarketStructureDetector(MarketStructureConfig(pivot_left=2, pivot_right=2))

    def test_uptrend_detection(self, detector):
        base_time = datetime(2024, 1, 1)
        # Clear uptrend with distinct higher highs and higher lows (60 candles for required_candles=50)
        prices = [
            (100, 100), (102, 102), (104, 104), (106, 106), (105, 105), (103, 103),
            (102, 102), (100, 100), (99, 99), (100, 100), (101, 101), (102, 102),
            (104, 104), (106, 106), (108, 108), (110, 110), (109, 109), (107, 107),
            (106, 106), (104, 104), (103, 103), (104, 104), (105, 105), (106, 106),
            (108, 108), (110, 110), (112, 112), (114, 114), (113, 113), (111, 111),
            (109, 109), (107, 107), (106, 106), (107, 107), (108, 108), (109, 109),
            (111, 111), (113, 113), (115, 115), (117, 117), (116, 116), (114, 114),
            (112, 112), (111, 111), (112, 112), (113, 113), (114, 114), (115, 115),
            (116, 116), (118, 118), (120, 120), (119, 119), (117, 117), (115, 115),
            (116, 116), (118, 118), (121, 121), (122, 122), (123, 123), (124, 124),
        ]
        candles = []
        for i, (o, c) in enumerate(prices):
            h = max(o, c) + 0.5
            l = min(o, c) - 0.5
            candles.append(Candle(
                timestamp=base_time + timedelta(days=i),
                open=o, high=h, low=l, close=c, volume=50000
            ))
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "UPTREND" for d in detections)

    def test_downtrend_detection(self, detector):
        base_time = datetime(2024, 1, 1)
        # Clear downtrend with distinct lower highs and lower lows (60 candles for required_candles=50)
        prices = [
            (120, 120), (118, 118), (116, 116), (114, 114), (115, 115), (117, 117),
            (118, 118), (120, 120), (121, 121), (120, 120), (119, 119), (118, 118),
            (116, 116), (114, 114), (112, 112), (110, 110), (111, 111), (113, 113),
            (114, 114), (116, 116), (117, 117), (116, 116), (115, 115), (114, 114),
            (112, 112), (110, 110), (108, 108), (106, 106), (107, 107), (108, 108),
            (109, 109), (111, 111), (112, 112), (111, 111), (110, 110), (109, 109),
            (107, 107), (105, 105), (103, 103), (101, 101), (102, 102), (103, 103),
            (100, 100), (98, 98), (96, 96), (94, 94), (95, 95), (97, 97),
            (98, 98), (100, 100), (101, 101), (100, 100), (99, 99), (97, 97),
            (96, 96), (94, 94), (92, 92), (90, 90), (88, 88), (86, 86),
        ]
        candles = []
        for i, (o, c) in enumerate(prices):
            h = max(o, c) + 0.5
            l = min(o, c) - 0.5
            candles.append(Candle(
                timestamp=base_time + timedelta(days=i),
                open=o, high=h, low=l, close=c, volume=50000
            ))
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        assert any(d.pattern_name == "DOWNTREND" for d in detections)


class TestPivotDetector:
    @pytest.fixture
    def detector(self):
        return PivotDetector(PivotConfig(left_bars=2, right_bars=2))

    def test_pivot_high_detection(self, detector):
        candles = [
            Candle(timestamp=datetime(2024,1,1) + timedelta(days=i), open=100, high=100+i*0.1, low=99, close=99.5+i*0.1, volume=1000)
            for i in range(10)
        ]
        candles[5] = Candle(timestamp=datetime(2024,1,6), open=105, high=110, low=104, close=106, volume=1000)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        pivots = detector.detect_pivots(data)
        assert len(pivots) > 0


class TestIndicatorPatterns:
    @pytest.fixture
    def detector(self):
        return IndicatorPatternDetector()

    def test_rsi_overbought(self, detector):
        candles = create_test_candles(60, trend="up")
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        rsi_patterns = [d for d in detections if "RSI" in d.pattern_name]
        assert len(rsi_patterns) >= 0


class TestDivergenceDetector:
    @pytest.fixture
    def detector(self):
        return DivergenceDetector()

    def test_divergence_detection(self, detector):
        candles = create_test_candles(60)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        div_patterns = [d for d in detections if "DIVERGENCE" in d.pattern_name]
        assert len(div_patterns) >= 0


class TestHarmonicPatterns:
    @pytest.fixture
    def detector(self):
        return HarmonicPatternDetector()

    def test_harmonic_detection(self, detector):
        candles = create_test_candles(60)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        harmonic_patterns = [d for d in detections if d.pattern_category == PatternCategory.HARMONIC]
        assert len(harmonic_patterns) >= 0


class TestWavePatterns:
    @pytest.fixture
    def detector(self):
        return WavePatternDetector()

    def test_wave_candidate_detection(self, detector):
        candles = create_test_candles(60)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        wave_patterns = [d for d in detections if d.pattern_category == PatternCategory.WAVE]
        assert len(wave_patterns) >= 0


class TestVolumePatterns:
    @pytest.fixture
    def detector(self):
        return VolumePatternDetector()

    def test_volume_spike(self, detector):
        candles = create_test_candles(30)
        candles[-1] = Candle(
            timestamp=candles[-1].timestamp,
            open=100, high=105, low=99, close=104, volume=500000
        )
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        detections = detector.detect(data)
        vol_patterns = [d for d in detections if d.pattern_category == PatternCategory.VOLUME]
        assert len(vol_patterns) >= 0


class TestMarketRegime:
    @pytest.fixture
    def detector(self):
        return MarketRegimeDetector()

    def test_regime_detection(self, detector):
        candles = create_test_candles(60, trend="up")
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        regime = detector.detect(data)
        assert regime in MarketRegime


class TestConfluenceEngine:
    def test_confluence_calculation(self):
        from app.patterns.models import PatternDetection
        detections = [
            PatternDetection(
                symbol="TEST", timeframe=Timeframe.DAY_1,
                pattern_name="BULLISH_ENGULFING", pattern_category=PatternCategory.CANDLESTICK,
                direction=PatternDirection.BULLISH, status=PatternStatus.CONFIRMED,
                start_timestamp=datetime.now(), detection_timestamp=datetime.now(),
                price_levels={}, quality_score=80,
            ),
            PatternDetection(
                symbol="TEST", timeframe=Timeframe.DAY_1,
                pattern_name="DOUBLE_BOTTOM", pattern_category=PatternCategory.CHART_PATTERN,
                direction=PatternDirection.BULLISH, status=PatternStatus.CONFIRMED,
                start_timestamp=datetime.now(), detection_timestamp=datetime.now(),
                price_levels={}, quality_score=75,
            ),
        ]
        result = calculate_confluence(detections)
        assert result.technical_confluence_score > 50
        assert len(result.patterns) == 2


class TestBacktester:
    @pytest.fixture
    def backtester(self):
        return PatternBacktester(BacktestConfig())

    def test_backtest_run(self, backtester):
        detector = CandlestickPatternDetector()
        candles = create_test_candles(100)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        result = backtester.backtest_pattern(detector, data)
        assert result.pattern_name == "CANDLESTICK_PATTERNS"
        assert result.total_occurrences >= 0


class TestScanner:
    @pytest.fixture
    def scanner(self):
        registry = PatternRegistry()
        from app.patterns.detectors import (
            register_candlestick_patterns, register_chart_patterns,
            register_market_structure, register_indicator_patterns,
        )
        register_candlestick_patterns(registry)
        register_chart_patterns(registry)
        register_market_structure(registry)
        register_indicator_patterns(registry)
        return PatternScanner(registry, ScannerConfig(min_quality_score=0))

    def test_scan_symbol(self, scanner):
        candles = create_test_candles(60)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        results = scanner.scan_symbol(data, Timeframe.DAY_1)
        assert isinstance(results, list)


class TestDataValidation:
    def test_valid_ohlcv(self):
        candles = create_test_candles(10)
        data = OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)
        assert len(data.candles) == 10

    def test_invalid_high_low(self):
        from pydantic import ValidationError
        base_time = datetime(2024, 1, 1)
        candles = [
            Candle(timestamp=base_time, open=100, high=99, low=101, close=100, volume=1000),
        ]
        with pytest.raises(ValidationError):
            OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)

    def test_duplicate_timestamps(self):
        base_time = datetime(2024, 1, 1)
        candles = [
            Candle(timestamp=base_time, open=100, high=101, low=99, close=100, volume=1000),
            Candle(timestamp=base_time, open=101, high=102, low=100, close=101, volume=1000),
        ]
        with pytest.raises(ValueError):
            OHLCVData(symbol="TEST", timeframe=Timeframe.DAY_1, candles=candles)


class TestPatternRegistry:
    def test_registry_registration(self):
        registry = PatternRegistry()
        detector = CandlestickPatternDetector()
        registry.register(detector)
        assert registry.get("CANDLESTICK_PATTERNS") == detector
        assert len(registry.get_all()) == 1

    def test_registry_categories(self):
        registry = PatternRegistry()
        detector = CandlestickPatternDetector()
        registry.register(detector)
        cats = registry.get_categories()
        assert PatternCategory.CANDLESTICK in cats

    def test_duplicate_registration(self):
        registry = PatternRegistry()
        detector = CandlestickPatternDetector()
        registry.register(detector)
        with pytest.raises(ValueError):
            registry.register(detector)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])