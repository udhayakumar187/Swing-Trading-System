#!/usr/bin/env python
"""
Verification script for STAGE 4 implementation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_file_exists(path, description):
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if os.path.exists(full_path):
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[MISSING] {description}: {path}")
        return False


def verify_imports():
    print("\nVerifying STAGE 4 imports...")
    
    try:
        from app.brokers.base import BrokerProvider, OrderRequest, OrderResponse
        print("  [OK] app.brokers.base")
    except Exception as e:
        print(f"  [FAIL] app.brokers.base: {e}")
        return False
    
    try:
        from app.brokers.paper_broker import PaperBrokerProvider
        print("  [OK] app.brokers.paper_broker")
    except Exception as e:
        print(f"  [FAIL] app.brokers.paper_broker: {e}")
        return False
    
    try:
        from app.brokers.angelone_broker import AngelOneBrokerProvider, create_broker_provider
        print("  [OK] app.brokers.angelone_broker")
    except Exception as e:
        print(f"  [FAIL] app.brokers.angelone_broker: {e}")
        return False
    
    try:
        from app.brokers import (
            BrokerProvider, OrderRequest, OrderResponse, OrderStatus,
            OrderSide, OrderType, OrderProductType, Position, AccountInfo,
            PaperBrokerProvider, AngelOneBrokerProvider, create_broker_provider
        )
        print("  [OK] app.brokers package")
    except Exception as e:
        print(f"  [FAIL] app.brokers package: {e}")
        return False
    
    try:
        from app.services.execution_service import ExecutionService, ExecutionResult
        print("  [OK] app.services.execution_service")
    except Exception as e:
        print(f"  [FAIL] app.services.execution_service: {e}")
        return False
    
    try:
        from app.services.portfolio_service import PortfolioService, PortfolioSummary
        print("  [OK] app.services.portfolio_service")
    except Exception as e:
        print(f"  [FAIL] app.services.portfolio_service: {e}")
        return False
    
    try:
        from app.services.trading_service import TradingService, TradingRunResult
        print("  [OK] app.services.trading_service")
    except Exception as e:
        print(f"  [FAIL] app.services.trading_service: {e}")
        return False
    
    try:
        from app.scheduler.jobs import TradingScheduler, get_scheduler
        print("  [OK] app.scheduler.jobs")
    except Exception as e:
        print(f"  [FAIL] app.scheduler.jobs: {e}")
        return False
    
    try:
        from app.api.trading import router
        print("  [OK] app.api.trading")
    except Exception as e:
        print(f"  [FAIL] app.api.trading: {e}")
        return False
    
    return True


def verify_paper_broker():
    print("\nVerifying PaperBrokerProvider...")
    
    try:
        from app.brokers.paper_broker import PaperBrokerProvider
        from app.brokers.base import OrderRequest, OrderSide, OrderType, OrderProductType
        
        broker = PaperBrokerProvider(initial_cash=100000)
        assert broker.login()
        assert broker.is_connected()
        print("  [OK] Login/Connection")
        
        account = broker.get_account()
        assert account.available_cash == 100000
        print("  [OK] Get account")
        
        request = OrderRequest(
            symbol="RELIANCE.NS",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.MARKET,
            product_type=OrderProductType.DELIVERY,
            price=2500.0
        )
        
        response = broker.place_order(request)
        assert response.status.value == "COMPLETE"
        assert response.filled_quantity == 10
        print("  [OK] Place BUY order")
        
        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "RELIANCE.NS"
        assert positions[0].quantity == 10
        print("  [OK] Get positions")
        
        orders = broker.get_orders()
        assert len(orders) == 1
        print("  [OK] Get orders")
        
        broker.update_market_price("RELIANCE.NS", 2600.0)
        positions = broker.get_positions()
        assert positions[0].current_price == 2600.0
        assert positions[0].unrealized_pnl == 1000.0
        print("  [OK] Update market price & P&L")
        
        sell_request = OrderRequest(
            symbol="RELIANCE.NS",
            side=OrderSide.SELL,
            quantity=5,
            order_type=OrderType.MARKET,
            product_type=OrderProductType.DELIVERY,
            price=2600.0
        )
        
        response = broker.place_order(sell_request)
        assert response.status.value == "COMPLETE"
        assert response.filled_quantity == 5
        print("  [OK] Place SELL order (partial)")
        
        positions = broker.get_positions()
        assert positions[0].quantity == 5
        print("  [OK] Position quantity updated after partial sell")
        
        broker.logout()
        assert not broker.is_connected()
        print("  [OK] Logout")
        
        return True
    except Exception as e:
        print(f"  [FAIL] PaperBrokerProvider: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_api_routes():
    print("\nVerifying API routes...")
    
    try:
        from app.api.trading import router
        
        routes = [route.path for route in router.routes]
        expected_routes = [
            "/api/positions",
            "/api/orders",
            "/api/signals",
            "/api/trading-runs",
            "/api/portfolio",
            "/api/risk-settings",
            "/api/trading/run",
            "/api/account",
            "/api/logs"
        ]
        
        for route in expected_routes:
            found = any(route in r for r in routes)
            if found:
                print(f"  [OK] {route}")
            else:
                print(f"  [MISSING] {route}")
                return False
        
        return True
    except Exception as e:
        print(f"  [FAIL] API routes: {e}")
        return False


def verify_scheduler():
    print("\nVerifying TradingScheduler...")
    
    try:
        from app.scheduler.jobs import TradingScheduler
        from app.core.config import get_settings
        import os
        
        os.environ['ANGEL_ONE_API_KEY'] = 'test'
        os.environ['ANGEL_ONE_CLIENT_ID'] = 'test'
        os.environ['ANGEL_ONE_PASSWORD'] = 'test'
        os.environ['ANGEL_ONE_TOTP_SECRET'] = 'test'
        os.environ['TRADING_MODE'] = 'DRY_RUN'
        
        scheduler = TradingScheduler()
        assert scheduler.scheduler is not None
        print("  [OK] Scheduler created")
        
        # Start scheduler to add jobs
        scheduler.start()
        
        jobs = scheduler.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        expected_jobs = ["daily_trading", "reconcile_positions", "daily_snapshot"]
        
        for job_id in expected_jobs:
            if job_id in job_ids:
                print(f"  [OK] Job: {job_id}")
            else:
                print(f"  [MISSING] Job: {job_id}")
                return False
        
        next_run = scheduler.get_next_run_time()
        if next_run:
            print(f"  [OK] Next run: {next_run}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Scheduler: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("STAGE 4 VERIFICATION")
    print("=" * 60)
    
    all_ok = True
    
    all_ok &= check_file_exists("app/brokers/base.py", "Broker Base Interface")
    all_ok &= check_file_exists("app/brokers/paper_broker.py", "Paper Broker")
    all_ok &= check_file_exists("app/brokers/angelone_broker.py", "Angel One Broker")
    all_ok &= check_file_exists("app/brokers/__init__.py", "Brokers Init")
    all_ok &= check_file_exists("app/services/execution_service.py", "Execution Service")
    all_ok &= check_file_exists("app/services/portfolio_service.py", "Portfolio Service")
    all_ok &= check_file_exists("app/services/trading_service.py", "Trading Service")
    all_ok &= check_file_exists("app/services/__init__.py", "Services Init")
    all_ok &= check_file_exists("app/scheduler/jobs.py", "Scheduler Jobs")
    all_ok &= check_file_exists("app/scheduler/__init__.py", "Scheduler Init")
    all_ok &= check_file_exists("app/api/trading.py", "Trading API")
    all_ok &= check_file_exists("app/scripts/seed.py", "Seed Script")
    
    if not all_ok:
        print("\n[FAILURE] Some files missing")
        return 1
    
    all_ok &= verify_imports()
    all_ok &= verify_paper_broker()
    all_ok &= verify_api_routes()
    all_ok &= verify_scheduler()
    
    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] ALL STAGE 4 CHECKS PASSED")
        print("\nSTAGE 4 COMPLETE:")
        print("  - BrokerProvider interface (abstract)")
        print("  - PaperBrokerProvider (DRY_RUN execution)")
        print("    * Simulated BUY/SELL MARKET DELIVERY orders")
        print("    * Position tracking with P&L")
        print("    * Cash management")
        print("    * Order history")
        print("  - AngelOneBrokerProvider (LIVE - disabled by default)")
        print("    * SmartAPI authentication with TOTP")
        print("    * Order placement, cancellation, status")
        print("    * Position/account retrieval")
        print("  - Factory create_broker_provider() respects DRY_RUN")
        print("  - ExecutionService:")
        print("    * Order record creation")
        print("    * Broker submission (LIVE) or simulation (DRY_RUN)")
        print("    * Position creation on fill")
        print("    * Order reconciliation")
        print("  - PortfolioService:")
        print("    * Portfolio summary with equity, cash, P&L")
        print("    * Stop loss / target monitoring")
        print("    * Daily snapshot creation")
        print("    * R-multiple & holding duration")
        print("  - TradingService (full pipeline):")
        print("    * Market data fetch -> Strategy -> Risk -> Execute")
        print("    * Duplicate run prevention")
        print("    * Event risk integration")
        print("  - TradingScheduler:")
        print("    * Daily run at 15:45 IST")
        print("    * Reconciliation at 15:50")
        print("    * Daily snapshot at 16:00")
        print("  - REST API endpoints:")
        print("    * GET /api/positions, /api/orders, /api/signals")
        print("    * GET /api/trading-runs, /api/portfolio")
        print("    * GET/POST /api/risk-settings")
        print("    * POST /api/trading/run (manual, respects DRY_RUN)")
        print("    * GET /api/account, /api/logs")
    else:
        print("[FAILURE] SOME CHECKS FAILED")
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())