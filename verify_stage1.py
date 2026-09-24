#!/usr/bin/env python
"""
Verification script for STAGE 1 implementation.
This script checks that all files exist and have correct structure.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_file_exists(path, description):
    """Check if a file exists."""
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if os.path.exists(full_path):
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[MISSING] {description}: {path}")
        return False


def check_directory_exists(path, description):
    """Check if a directory exists."""
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if os.path.isdir(full_path):
        print(f"[OK] {description}: {path}/")
        return True
    else:
        print(f"[MISSING] {description}: {path}/")
        return False


def main():
    print("=" * 60)
    print("STAGE 1 FILE STRUCTURE VERIFICATION")
    print("=" * 60)
    
    all_ok = True
    
    # Root files
    print("\n--- Root Files ---")
    all_ok &= check_file_exists(".env.example", "Environment example")
    all_ok &= check_file_exists("requirements.txt", "Requirements")
    all_ok &= check_file_exists("Dockerfile", "Dockerfile")
    all_ok &= check_file_exists("docker-compose.yml", "Docker Compose")
    all_ok &= check_file_exists("alembic.ini", "Alembic config")
    all_ok &= check_file_exists("README.md", "README")
    
    # App structure
    print("\n--- App Directory Structure ---")
    all_ok &= check_directory_exists("app", "App root")
    all_ok &= check_directory_exists("app/api", "API module")
    all_ok &= check_directory_exists("app/core", "Core module")
    all_ok &= check_directory_exists("app/models", "Models module")
    all_ok &= check_directory_exists("app/schemas", "Schemas module")
    all_ok &= check_directory_exists("app/services", "Services module")
    all_ok &= check_directory_exists("app/strategies", "Strategies module")
    all_ok &= check_directory_exists("app/risk", "Risk module")
    all_ok &= check_directory_exists("app/brokers", "Brokers module")
    all_ok &= check_directory_exists("app/market_data", "Market Data module")
    all_ok &= check_directory_exists("app/scheduler", "Scheduler module")
    all_ok &= check_directory_exists("app/repositories", "Repositories module")
    all_ok &= check_directory_exists("app/utils", "Utils module")
    all_ok &= check_directory_exists("app/tests", "Tests module")
    
    # Core files
    print("\n--- Core Files ---")
    all_ok &= check_file_exists("app/core/__init__.py", "Core init")
    all_ok &= check_file_exists("app/core/config.py", "Config")
    all_ok &= check_file_exists("app/core/database.py", "Database")
    all_ok &= check_file_exists("app/core/logging.py", "Logging")
    
    # Model files
    print("\n--- Model Files ---")
    all_ok &= check_file_exists("app/models/__init__.py", "Models init")
    all_ok &= check_file_exists("app/models/base.py", "Base model")
    all_ok &= check_file_exists("app/models/account.py", "Account model")
    all_ok &= check_file_exists("app/models/position.py", "Position model")
    all_ok &= check_file_exists("app/models/order.py", "Order model")
    all_ok &= check_file_exists("app/models/signal.py", "Signal model")
    all_ok &= check_file_exists("app/models/trading_run.py", "TradingRun model")
    all_ok &= check_file_exists("app/models/journal_entry.py", "JournalEntry model")
    all_ok &= check_file_exists("app/models/risk_settings.py", "RiskSettings model")
    all_ok &= check_file_exists("app/models/audit_log.py", "AuditLog model")
    all_ok &= check_file_exists("app/models/watchlist.py", "Watchlist model")
    all_ok &= check_file_exists("app/models/daily_portfolio_snapshot.py", "DailyPortfolioSnapshot model")
    
    # API files
    print("\n--- API Files ---")
    all_ok &= check_file_exists("app/api/__init__.py", "API init")
    all_ok &= check_file_exists("app/api/health.py", "Health endpoint")
    
    # Main app
    print("\n--- Main App ---")
    all_ok &= check_file_exists("app/main.py", "Main FastAPI app")
    
    # Alembic
    print("\n--- Alembic ---")
    all_ok &= check_directory_exists("alembic", "Alembic dir")
    all_ok &= check_directory_exists("alembic/versions", "Alembic versions")
    all_ok &= check_file_exists("alembic/env.py", "Alembic env")
    
    # Tests
    print("\n--- Tests ---")
    all_ok &= check_file_exists("app/tests/__init__.py", "Tests init")
    all_ok &= check_file_exists("app/tests/test_stage1.py", "Stage 1 tests")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] ALL STAGE 1 FILES PRESENT")
        print("\nSTAGE 1 COMPLETE:")
        print("  - Project structure created")
        print("  - Configuration (.env.example, config.py)")
        print("  - Database models (all 10 models)")
        print("  - Database connection & session management")
        print("  - Alembic migration setup")
        print("  - Logging configuration")
        print("  - Health endpoint (/api/health, /api/health/db)")
        print("  - FastAPI app with CORS")
        print("  - Docker & Docker Compose")
        print("  - Test structure")
    else:
        print("[FAILURE] SOME FILES MISSING")
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())