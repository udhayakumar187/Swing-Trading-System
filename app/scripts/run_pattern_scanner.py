#!/usr/bin/env python
"""
Pattern Scanner Runner
Run this script to scan for patterns and track outcomes.
"""

import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.patterns.scanner.pattern_scanner import PatternScannerService
from app.core.config import get_settings
from app.core.logging import setup_logging


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    
    if not settings.has_supabase:
        logger.warning("Supabase not configured. Please set SUPABASE_URL and SUPABASE_KEY in .env")
        logger.info("Skipping database operations, will only log results")
    
    logger.info("Starting pattern scanner...")
    logger.info(f"Symbols: {settings.pattern_symbols}")
    logger.info(f"Timeframe: {settings.PATTERN_SCAN_TIMEFRAME}")
    logger.info(f"Lookback days: {settings.PATTERN_SCAN_LOOKBACK_DAYS}")
    logger.info(f"Forward tracking days: {settings.PATTERN_FORWARD_DAYS}")
    
    scanner = PatternScannerService()
    
    # Scan all symbols
    results = scanner.scan_all_symbols()
    
    total_patterns = sum(len(p) for p in results.values())
    logger.info(f"Scan complete. Found {total_patterns} patterns across {len(results)} symbols")
    
    for symbol, patterns in results.items():
        logger.info(f"  {symbol}: {len(patterns)} patterns")
        for p in patterns:
            logger.info(f"    - {p.pattern_type.value}: {p.pattern_name} ({p.direction}) @ {p.detection_price:.2f}")
    
    # Update pending outcomes
    logger.info("Updating pending pattern outcomes...")
    scanner.update_pending_outcomes()
    logger.info("Outcome update complete")
    
    # Print statistics
    from app.patterns.repositories.supabase_repository import get_supabase_repository
    if settings.has_supabase:
        repo = get_supabase_repository()
        stats = repo.get_pattern_statistics()
        logger.info("\nPattern Statistics:")
        for s in stats:
            logger.info(
                f"  {s['symbol']} {s['pattern_type']}: "
                f"{s['total_detections']} total, "
                f"{s['successful']} wins, "
                f"{s['failed']} losses, "
                f"{s['pending']} pending, "
                f"Win rate: {s['win_rate']}%, "
                f"Avg return: {s['avg_return_pct']}%, "
                f"Avg R: {s['avg_r_multiple']}"
            )


if __name__ == "__main__":
    main()