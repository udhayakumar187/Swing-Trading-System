from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import create_tables
from app.core.logging import setup_logging, get_logger
from app.api import health, trading, backtest
from app.core import metrics
from app.scheduler import start_scheduler, stop_scheduler
from app.patterns.api import routes as patterns_routes
from app.patterns import initialize_pattern_engine


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    logger.info(f"Starting application in {settings.TRADING_MODE} mode")
    logger.info(f"Timezone: {settings.TIMEZONE}")
    create_tables()
    logger.info("Database tables created/verified")

    initialize_pattern_engine()
    logger.info("Pattern engine initialized")

    if not settings.is_dry_run:
        logger.warning("LIVE MODE ENABLED - Real orders will be placed!")

    start_scheduler()
    logger.info("Trading scheduler started")

    yield

    stop_scheduler()
    logger.info("Trading scheduler stopped")
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Swing Trading System",
        description="Autonomous swing-trading backend for Indian NSE equities",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS - restrict in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(trading.router)
    app.include_router(backtest.router)
    app.include_router(metrics.router)
    app.include_router(patterns_routes.router)

    return app


app = create_app()