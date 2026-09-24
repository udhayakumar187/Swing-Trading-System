from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core.health_checks import health_checker


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    settings = get_settings()
    
    result = health_checker.run_all_checks(db)
    
    return {
        "status": result["status"],
        "version": "1.0.0",
        "environment": "production" if settings.is_live else "dry_run",
        "trading_mode": settings.TRADING_MODE,
        "timezone": settings.TIMEZONE,
        "timestamp": result["timestamp"],
        "checks": {c["name"]: c["status"] == "healthy" for c in result["checks"]},
        "details": result["checks"]
    }


@router.get("/health/db")
async def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/health/live")
async def liveness_probe():
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(db: Session = Depends(get_db)):
    result = health_checker.run_all_checks(db)
    
    if result["status"] in ["healthy", "degraded"]:
        return {"status": "ready", "details": result}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result)