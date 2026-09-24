#!/usr/bin/env python
"""
Seed script to create initial account and watchlist data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import create_tables, get_db
from app.core.config import get_settings
from app.models.account import Account
from app.models.watchlist import Watchlist
from app.models.risk_settings import RiskSettings


def seed():
    settings = get_settings()
    create_tables()
    
    db = next(get_db())
    try:
        account = db.query(Account).filter(Account.id == 1).first()
        if not account:
            account = Account(
                broker_name="Angel One",
                client_id="TEST_CLIENT",
                account_name="Swing Trading Account",
                is_active=True,
                is_paper=settings.is_dry_run,
                total_capital=settings.TOTAL_PORTFOLIO_CAPITAL,
                available_cash=settings.TOTAL_PORTFOLIO_CAPITAL,
                max_risk_percent=settings.MAX_RISK_PERCENT,
                max_daily_loss_percent=settings.MAX_DAILY_LOSS_PERCENT,
                max_open_positions=settings.MAX_OPEN_POSITIONS,
                max_stop_loss_percent=settings.MAX_STOP_LOSS_PERCENT,
                min_risk_reward=settings.MIN_RISK_REWARD
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            print(f"Created account: {account.id}")
        
        risk_settings = db.query(RiskSettings).filter(RiskSettings.account_id == account.id).first()
        if not risk_settings:
            risk_settings = RiskSettings(
                account_id=account.id,
                max_risk_percent=settings.MAX_RISK_PERCENT,
                max_daily_loss_percent=settings.MAX_DAILY_LOSS_PERCENT,
                max_open_positions=settings.MAX_OPEN_POSITIONS,
                max_stop_loss_percent=settings.MAX_STOP_LOSS_PERCENT,
                min_risk_reward=settings.MIN_RISK_REWARD,
                swing_low_lookback=settings.SWING_LOW_LOOKBACK,
                event_exclusion_window=settings.EVENT_EXCLUSION_WINDOW
            )
            db.add(risk_settings)
            db.commit()
            print("Created risk settings")
        
        default_symbols = [
            ("RELIANCE.NS", "Reliance Industries", "Energy"),
            ("TCS.NS", "Tata Consultancy Services", "Technology"),
            ("INFY.NS", "Infosys", "Technology"),
            ("SBIN.NS", "State Bank of India", "Banking"),
            ("HDFCBANK.NS", "HDFC Bank", "Banking"),
            ("ICICIBANK.NS", "ICICI Bank", "Banking"),
            ("HINDUNILVR.NS", "Hindustan Unilever", "FMCG"),
            ("ITC.NS", "ITC Limited", "FMCG"),
            ("BHARTIARTL.NS", "Bharti Airtel", "Telecom"),
            ("KOTAKBANK.NS", "Kotak Mahindra Bank", "Banking"),
        ]
        
        for symbol, name, sector in default_symbols:
            existing = db.query(Watchlist).filter(
                Watchlist.account_id == account.id,
                Watchlist.symbol == symbol
            ).first()
            if not existing:
                watchlist = Watchlist(
                    account_id=account.id,
                    symbol=symbol,
                    exchange="NSE",
                    name=name,
                    sector=sector,
                    is_active=True
                )
                db.add(watchlist)
        
        db.commit()
        print(f"Seeded {len(default_symbols)} symbols to watchlist")
        print("Seeding complete!")
        
    finally:
        db.close()


if __name__ == "__main__":
    seed()