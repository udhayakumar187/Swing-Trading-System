from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta

from app.patterns.models import (
    PatternDetection,
    PatternCategory,
    PatternDirection,
    PatternStatus,
    OHLCVData,
    Timeframe,
    MarketRegime,
)
from app.patterns.registry import PatternRegistry
from app.patterns.regime.detector import MarketRegimeDetector, RegimeConfig
from app.patterns.confluence.engine import calculate_confluence, ConfluenceConfig


@dataclass
class ScannerConfig:
    min_quality_score: int = 50
    max_symbols_per_scan: int = 100
    include_forming: bool = True
    include_confirmed: bool = True
    categories: Optional[List[PatternCategory]] = None
    directions: Optional[List[PatternDirection]] = None
    regimes: Optional[List[MarketRegime]] = None


@dataclass
class ScanResult:
    symbol: str
    timeframe: Timeframe
    pattern: str
    category: PatternCategory
    direction: PatternDirection
    status: PatternStatus
    quality_score: int
    confirmation: bool
    entry_level: Optional[float]
    invalidation: Optional[float]
    target: Optional[float]
    volume_status: str
    market_regime: Optional[MarketRegime]
    confluence_score: Optional[int] = None
    detection_time: datetime = None


class PatternScanner:
    def __init__(
        self,
        registry: PatternRegistry,
        config: Optional[ScannerConfig] = None,
    ):
        self.registry = registry
        self.config = config or ScannerConfig()
        self.regime_detector = MarketRegimeDetector(RegimeConfig())
        self.confluence_config = ConfluenceConfig()

    def scan_symbol(
        self,
        data: OHLCVData,
        timeframe: Timeframe,
    ) -> List[ScanResult]:
        if len(data.candles) < 50:
            return []

        regime_data = self.regime_detector.detect_with_details(data)
        market_regime = regime_data["regime"]

        if self.config.regimes and market_regime not in self.config.regimes:
            return []

        detections = self.registry.detect_all(
            data,
            categories=self.config.categories,
        )

        confluence = calculate_confluence(detections, self.confluence_config, market_regime)

        results = []
        for det in detections:
            if self.config.directions and det.direction not in self.config.directions:
                continue

            if det.status == PatternStatus.FORMING and not self.config.include_forming:
                continue
            if det.status == PatternStatus.CONFIRMED and not self.config.include_confirmed:
                continue

            quality = det.quality_score or 50
            if quality < self.config.min_quality_score:
                continue

            entry = self._calculate_entry_level(det)
            target = self._get_primary_target(det)
            volume_status = "HIGH" if det.volume_confirmation else "NORMAL"

            results.append(ScanResult(
                symbol=data.symbol,
                timeframe=timeframe,
                pattern=det.pattern_name,
                category=det.pattern_category,
                direction=det.direction,
                status=det.status,
                quality_score=quality,
                confirmation=det.status == PatternStatus.CONFIRMED,
                entry_level=entry,
                invalidation=det.invalidation_level,
                target=target,
                volume_status=volume_status,
                market_regime=market_regime,
                confluence_score=confluence.technical_confluence_score,
                detection_time=det.detection_timestamp,
            ))

        results.sort(key=lambda x: (x.quality_score, x.confluence_score or 0), reverse=True)
        return results

    def scan_multiple(
        self,
        data_dict: Dict[str, OHLCVData],
        timeframe: Timeframe,
    ) -> List[ScanResult]:
        all_results = []
        symbols = list(data_dict.keys())[:self.config.max_symbols_per_scan]

        for symbol in symbols:
            data = data_dict[symbol]
            data.symbol = symbol
            try:
                results = self.scan_symbol(data, timeframe)
                all_results.extend(results)
            except Exception as e:
                pass

        all_results.sort(key=lambda x: (x.quality_score, x.confluence_score or 0), reverse=True)
        return all_results

    def _calculate_entry_level(self, detection: PatternDetection) -> Optional[float]:
        if detection.direction == PatternDirection.BULLISH:
            levels = detection.price_levels
            if "pattern_low" in levels:
                return levels["pattern_low"]
            elif "trough1" in levels:
                return levels["trough1"]
            elif "support" in levels:
                return levels["support"]
        elif detection.direction == PatternDirection.BEARISH:
            levels = detection.price_levels
            if "pattern_high" in levels:
                return levels["pattern_high"]
            elif "peak1" in levels:
                return levels["peak1"]
            elif "resistance" in levels:
                return levels["resistance"]
        return None

    def _get_primary_target(self, detection: PatternDetection) -> Optional[float]:
        targets = detection.target_levels
        if "target_1" in targets:
            return targets["target_1"]
        elif "target" in targets:
            return targets["target"]
        return None


def create_scanner(
    registry: Optional[PatternRegistry] = None,
    config: Optional[ScannerConfig] = None,
) -> PatternScanner:
    if registry is None:
        from app.patterns import get_initialized_registry
        registry = get_initialized_registry()
    return PatternScanner(registry, config)