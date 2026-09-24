from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel

from app.patterns.scanner.pattern_scanner import PatternScannerService
from app.patterns.repositories.supabase_repository import get_supabase_repository
from app.patterns.models.pattern_tracking import PatternType, PatternOutcome, PatternStatistics
from app.core.config import get_settings

router = APIRouter(prefix="/api/patterns", tags=["patterns"])

_scanner_service: Optional[PatternScannerService] = None


def get_scanner_service() -> PatternScannerService:
    global _scanner_service
    if _scanner_service is None:
        _scanner_service = PatternScannerService()
    return _scanner_service


class ScanRequest(BaseModel):
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = None


class ScanResponse(BaseModel):
    success: bool
    message: str
    results: Dict[str, List[Dict[str, Any]]] = {}


class PatternResponse(BaseModel):
    id: str
    symbol: str
    timeframe: str
    pattern_type: str
    pattern_name: str
    direction: str
    detection_timestamp: str
    detection_price: float
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    quality_score: Optional[int] = None
    volume_confirmation: bool = False
    outcome: str
    max_favorable_move: Optional[float] = None
    max_adverse_move: Optional[float] = None


class StatisticsResponse(BaseModel):
    statistics: List[Dict[str, Any]]


@router.post("/scan", response_model=ScanResponse)
async def scan_patterns(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
):
    try:
        scanner = get_scanner_service()
        results = scanner.scan_all_symbols(request.symbols, request.timeframe)
        
        response_data = {}
        for symbol, patterns in results.items():
            response_data[symbol] = [
                {
                    "id": p.id,
                    "pattern_type": p.pattern_type.value,
                    "pattern_name": p.pattern_name,
                    "direction": p.direction,
                    "detection_price": p.detection_price,
                    "detection_timestamp": p.detection_timestamp.isoformat(),
                    "stop_loss": p.stop_loss,
                    "target_price": p.target_price,
                    "quality_score": p.quality_score,
                    "volume_confirmation": p.volume_confirmation,
                }
                for p in patterns
            ]
        
        return ScanResponse(
            success=True,
            message=f"Scanned {len(results)} symbols, found patterns in {sum(len(v) for v in results.values())} symbols",
            results=response_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/background", response_model=ScanResponse)
async def scan_patterns_background(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
):
    try:
        scanner = get_scanner_service()
        
        def run_scan():
            scanner.scan_all_symbols(request.symbols, request.timeframe)
        
        background_tasks.add_task(run_scan)
        
        return ScanResponse(
            success=True,
            message="Background scan started",
            results={}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-outcomes")
async def update_outcomes(background_tasks: BackgroundTasks):
    try:
        scanner = get_scanner_service()
        
        def run_update():
            scanner.update_pending_outcomes()
        
        background_tasks.add_task(run_update)
        
        return {"success": True, "message": "Outcome update started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[PatternResponse])
async def list_patterns(
    symbol: Optional[str] = Query(None),
    pattern_type: Optional[PatternType] = Query(None),
    outcome: Optional[PatternOutcome] = Query(None),
    limit: int = Query(100, le=500),
):
    try:
        repo = get_supabase_repository()
        patterns = repo.get_patterns_by_symbol(
            symbol=symbol or get_settings().pattern_symbols[0],
            pattern_type=pattern_type,
            outcome=outcome,
            limit=limit
        )
        
        return [
            PatternResponse(
                id=p.id,
                symbol=p.symbol,
                timeframe=p.timeframe,
                pattern_type=p.pattern_type.value,
                pattern_name=p.pattern_name,
                direction=p.direction,
                detection_timestamp=p.detection_timestamp.isoformat(),
                detection_price=p.detection_price,
                stop_loss=p.stop_loss,
                target_price=p.target_price,
                quality_score=p.quality_score,
                volume_confirmation=p.volume_confirmation,
                outcome=p.outcome.value,
                max_favorable_move=p.max_favorable_move,
                max_adverse_move=p.max_adverse_move,
            )
            for p in patterns
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=List[PatternResponse])
async def get_pending_patterns(symbols: Optional[str] = Query(None)):
    try:
        repo = get_supabase_repository()
        symbol_list = symbols.split(",") if symbols else get_settings().pattern_symbols
        patterns = repo.get_pending_patterns(symbol_list)
        
        return [
            PatternResponse(
                id=p.id,
                symbol=p.symbol,
                timeframe=p.timeframe,
                pattern_type=p.pattern_type.value,
                pattern_name=p.pattern_name,
                direction=p.direction,
                detection_timestamp=p.detection_timestamp.isoformat(),
                detection_price=p.detection_price,
                stop_loss=p.stop_loss,
                target_price=p.target_price,
                quality_score=p.quality_score,
                volume_confirmation=p.volume_confirmation,
                outcome=p.outcome.value,
                max_favorable_move=p.max_favorable_move,
                max_adverse_move=p.max_adverse_move,
            )
            for p in patterns
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    pattern_type: Optional[PatternType] = Query(None),
    symbol: Optional[str] = Query(None),
):
    try:
        repo = get_supabase_repository()
        stats = repo.get_pattern_statistics(pattern_type, symbol)
        return StatisticsResponse(statistics=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forward-tracking/{pattern_id}")
async def get_forward_tracking(pattern_id: str):
    try:
        repo = get_supabase_repository()
        tracking = repo.get_forward_tracking(pattern_id)
        
        if not tracking:
            raise HTTPException(status_code=404, detail="Forward tracking not found")
        
        return tracking.model_dump(mode="json")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_scanner_config():
    settings = get_settings()
    return {
        "symbols": settings.pattern_symbols,
        "timeframe": settings.PATTERN_SCAN_TIMEFRAME,
        "lookback_days": settings.PATTERN_SCAN_LOOKBACK_DAYS,
        "forward_days": settings.PATTERN_FORWARD_DAYS,
        "supabase_configured": settings.has_supabase,
    }