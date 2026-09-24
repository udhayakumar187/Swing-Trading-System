from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.patterns.models import (
    PatternDetection,
    PatternCategory,
    PatternDirection,
    PatternStatus,
    Timeframe,
    MarketRegime,
    OHLCVData,
    Candle,
)
from app.patterns.registry import get_registry
from app.patterns.scanner.service import create_scanner, ScannerConfig, ScanResult
from app.patterns.regime.detector import MarketRegimeDetector, RegimeConfig
from app.patterns.confluence.engine import calculate_confluence, ConfluenceConfig
from app.patterns.backtest.engine import PatternBacktester, BacktestConfig
from app.patterns.detectors.pivot import PivotDetector, PivotConfig


router = APIRouter(prefix="/api/patterns", tags=["patterns"])


class DetectRequest(BaseModel):
    symbol: str
    timeframe: Timeframe
    candles: List[Candle]
    categories: Optional[List[PatternCategory]] = None
    detector_names: Optional[List[str]] = None


class ScanRequest(BaseModel):
    symbols: List[str]
    timeframe: Timeframe
    candles_by_symbol: Dict[str, List[Candle]]
    min_quality: int = 50
    categories: Optional[List[PatternCategory]] = None
    directions: Optional[List[PatternDirection]] = None
    regimes: Optional[List[MarketRegime]] = None


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: Timeframe
    candles: List[Candle]
    pattern_names: Optional[List[str]] = None
    categories: Optional[List[PatternCategory]] = None
    transaction_cost: float = 0.001
    slippage: float = 0.0005
    max_holding: int = 60


class ConfluenceRequest(BaseModel):
    symbol: str
    timeframe: Timeframe
    candles: List[Candle]


class MarketRegimeRequest(BaseModel):
    symbol: str
    timeframe: Timeframe
    candles: List[Candle]


@router.get("")
async def list_patterns():
    registry = get_registry()
    patterns = []
    for detector in registry.get_all():
        patterns.append({
            "name": detector.get_name(),
            "category": detector.get_category().value,
            "description": detector.definition.description,
            "required_candles": detector.get_required_candles(),
            "parameters": detector.definition.parameters,
        })
    return {"patterns": patterns}


@router.get("/categories")
async def list_categories():
    registry = get_registry()
    categories = []
    for cat in registry.get_categories():
        detectors = registry.get_by_category(cat)
        categories.append({
            "category": cat.value,
            "count": len(detectors),
            "patterns": [d.get_name() for d in detectors],
        })
    return {"categories": categories}


@router.get("/{pattern_name}")
async def get_pattern(pattern_name: str):
    registry = get_registry()
    detector = registry.get(pattern_name)
    if not detector:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {
        "name": detector.get_name(),
        "category": detector.get_category().value,
        "definition": detector.definition.model_dump(),
    }


@router.post("/detect")
async def detect_patterns(request: DetectRequest):
    registry = get_registry()

    try:
        data = OHLCVData(
            symbol=request.symbol,
            timeframe=request.timeframe,
            candles=request.candles,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")

    detections = registry.detect_all(
        data,
        categories=request.categories,
        detector_names=request.detector_names,
    )

    return {
        "symbol": request.symbol,
        "timeframe": request.timeframe.value,
        "detections": [d.to_dict() for d in detections],
        "count": len(detections),
    }


@router.post("/scan")
async def scan_patterns(request: ScanRequest):
    registry = get_registry()

    data_dict = {}
    for symbol, candles in request.candles_by_symbol.items():
        try:
            data_dict[symbol] = OHLCVData(
                symbol=symbol,
                timeframe=request.timeframe,
                candles=candles,
            )
        except Exception:
            continue

    scanner_config = ScannerConfig(
        min_quality_score=request.min_quality,
        categories=request.categories,
        directions=request.directions,
        regimes=request.regimes,
    )

    scanner = create_scanner(registry, scanner_config)
    results = scanner.scan_multiple(data_dict, request.timeframe)

    return {
        "timeframe": request.timeframe.value,
        "scanned_symbols": len(data_dict),
        "results": [
            {
                "symbol": r.symbol,
                "pattern": r.pattern,
                "category": r.category.value,
                "direction": r.direction.value,
                "status": r.status.value,
                "quality_score": r.quality_score,
                "confirmed": r.confirmation,
                "entry_level": r.entry_level,
                "invalidation": r.invalidation,
                "target": r.target,
                "volume_status": r.volume_status,
                "market_regime": r.market_regime.value if r.market_regime else None,
                "confluence_score": r.confluence_score,
            }
            for r in results
        ],
    }


@router.post("/confluence")
async def get_confluence(request: ConfluenceRequest):
    registry = get_registry()

    try:
        data = OHLCVData(
            symbol=request.symbol,
            timeframe=request.timeframe,
            candles=request.candles,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")

    detections = registry.detect_all(data)
    confluence = calculate_confluence(detections)

    return {
        "symbol": request.symbol,
        "timeframe": request.timeframe.value,
        "confluence": {
            "technical_confluence_score": confluence.technical_confluence_score,
            "explanation": confluence.explanation,
            "market_regime": confluence.market_regime.value if confluence.market_regime else None,
            "patterns": [
                {
                    "pattern_name": p.pattern_name,
                    "category": p.category.value,
                    "direction": p.direction.value,
                    "quality_score": p.quality_score,
                    "weight": p.weight,
                }
                for p in confluence.patterns
            ],
        },
    }


@router.post("/market-regime")
async def get_market_regime(request: MarketRegimeRequest):
    try:
        data = OHLCVData(
            symbol=request.symbol,
            timeframe=request.timeframe,
            candles=request.candles,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")

    detector = MarketRegimeDetector(RegimeConfig())
    result = detector.detect_with_details(data)

    return {
        "symbol": request.symbol,
        "timeframe": request.timeframe.value,
        "regime": result["regime"].value,
        "details": {k: v for k, v in result.items() if k != "regime"},
    }


@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    registry = get_registry()

    try:
        data = OHLCVData(
            symbol=request.symbol,
            timeframe=request.timeframe,
            candles=request.candles,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")

    config = BacktestConfig(
        transaction_cost_pct=request.transaction_cost,
        slippage_pct=request.slippage,
        max_holding_period=request.max_holding,
    )

    backtester = PatternBacktester(config)

    if request.pattern_names:
        results = {}
        for name in request.pattern_names:
            detector = registry.get(name)
            if detector:
                results[name] = backtester.backtest_pattern(detector, data)
    else:
        results = backtester.backtest_all_patterns(
            registry,
            data,
            categories=request.categories,
        )

    return {
        "symbol": request.symbol,
        "timeframe": request.timeframe.value,
        "config": config.__dict__,
        "results": {
            name: {
                "pattern_name": r.pattern_name,
                "total_occurrences": r.total_occurrences,
                "confirmed_count": r.confirmed_count,
                "invalidated_count": r.invalidated_count,
                "target_reached": r.target_reached,
                "stop_reached": r.stop_reached,
                "avg_return": r.avg_return,
                "median_return": r.median_return,
                "avg_mfe": r.avg_mfe,
                "avg_mae": r.avg_mae,
                "avg_holding_period": r.avg_holding_period,
                "win_count": r.win_count,
                "loss_count": r.loss_count,
                "profit_factor": r.profit_factor,
                "max_drawdown": r.max_drawdown,
            }
            for name, r in results.items()
        },
    }


@router.get("/pivots/{symbol}")
async def get_pivots(
    symbol: str,
    timeframe: Timeframe,
    candles: List[Candle] = Body(...),
    left_bars: int = Query(5, ge=1, le=20),
    right_bars: int = Query(5, ge=1, le=20),
):
    try:
        data = OHLCVData(symbol=symbol, timeframe=timeframe, candles=candles)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")

    pivot_detector = PivotDetector(PivotConfig(left_bars=left_bars, right_bars=right_bars))
    pivots = pivot_detector.detect_pivots(data)

    return {
        "symbol": symbol,
        "timeframe": timeframe.value,
        "config": {"left_bars": left_bars, "right_bars": right_bars},
        "pivots": [
            {
                "index": p.index,
                "timestamp": p.timestamp.isoformat(),
                "price": p.price,
                "type": p.pivot_type.value,
                "confirmed": p.confirmed,
            }
            for p in pivots
        ],
    }