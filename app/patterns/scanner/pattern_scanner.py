import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.patterns.models import (
    OHLCVData,
    Candle,
    Timeframe,
    PatternDetection,
    PatternDirection,
    PatternStatus,
    PatternType,
)
from app.patterns.models.pattern_tracking import (
    TrackedPattern,
    PatternForwardTracking,
    PatternOutcome,
)
from app.patterns.registry import get_registry
from app.patterns.repositories.supabase_repository import get_supabase_repository, SupabasePatternRepository
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PatternScannerService:
    def __init__(self, supabase_repo: Optional[SupabasePatternRepository] = None):
        self.settings = get_settings()
        self.registry = get_registry()
        self.supabase_repo = supabase_repo or get_supabase_repository()
    
    def fetch_market_data(self, symbol: str, timeframe: str, days: int) -> Optional[OHLCVData]:
        try:
            period_map = {
                "1d": f"{days}d",
                "1wk": f"{days*7}d",
                "1mo": f"{days*30}d",
            }
            
            interval_map = {
                "1d": "1d",
                "1wk": "1wk",
                "1mo": "1mo",
            }
            
            period = period_map.get(timeframe, f"{days}d")
            interval = interval_map.get(timeframe, "1d")
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval, auto_adjust=True)
            
            if hist.empty or len(hist) < 50:
                logger.warning(f"Insufficient data for {symbol}: {len(hist)} candles")
                return None
            
            candles = []
            for idx, row in hist.iterrows():
                candles.append(Candle(
                    timestamp=idx.to_pydatetime(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]) if row["Volume"] > 0 else 0,
                ))
            
            return OHLCVData(
                symbol=symbol,
                timeframe=Timeframe(timeframe),
                candles=candles,
            )
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def scan_symbol(self, symbol: str, timeframe: str, lookback_days: int) -> List[TrackedPattern]:
        logger.info(f"Scanning {symbol} on {timeframe}...")
        
        ohlcv_data = self.fetch_market_data(symbol, timeframe, lookback_days)
        if not ohlcv_data:
            return []
        
        all_detections = []
        for detector in self.registry.get_all():
            try:
                detections = detector.detect(ohlcv_data)
                all_detections.extend(detections)
            except Exception as e:
                logger.error(f"Error in detector {detector.definition.name} for {symbol}: {e}")
        
        tracked_patterns = []
        for detection in all_detections:
            pattern_type = self._map_to_pattern_type(detection.pattern_name)
            if pattern_type is None:
                continue
            
            tracked = self._create_tracked_pattern(detection, pattern_type, ohlcv_data)
            if tracked:
                tracked_patterns.append(tracked)
        
        logger.info(f"Found {len(tracked_patterns)} patterns for {symbol}")
        return tracked_patterns
    
    def _map_to_pattern_type(self, pattern_name: str) -> Optional[PatternType]:
        mapping = {
            "DOUBLE_BOTTOM": PatternType.DOUBLE_BOTTOM,
            "DOUBLE_TOP": PatternType.DOUBLE_TOP,
            "ASCENDING_TRIANGLE": PatternType.ASCENDING_TRIANGLE_BREAKOUT,
            "DESCENDING_TRIANGLE": PatternType.DESCENDING_TRIANGLE_BREAKDOWN,
            "BULL_FLAG": PatternType.BULL_FLAG,
            "BEAR_FLAG": PatternType.BEAR_FLAG,
            "RECTANGLE_BREAKOUT_UP": PatternType.BREAKOUT_VOLUME,
            "RECTANGLE_BREAKDOWN": PatternType.BREAKOUT_VOLUME,
            "HEAD_AND_SHOULDERS": PatternType.RESISTANCE_REJECTION,
            "INVERSE_HEAD_AND_SHOULDERS": PatternType.SUPPORT_BOUNCE,
            "FALLING_WEDGE": PatternType.TREND_PULLBACK,
            "RISING_WEDGE": PatternType.TREND_PULLBACK,
            "CUP_AND_HANDLE": PatternType.BREAKOUT_RETEST,
            "ROUNDING_BOTTOM": PatternType.SUPPORT_BOUNCE,
            "ROUNDING_TOP": PatternType.RESISTANCE_REJECTION,
            "BREAKOUT_VOLUME": PatternType.BREAKOUT_VOLUME,
            "BREAKOUT_RETEST": PatternType.BREAKOUT_RETEST,
            "TREND_PULLBACK": PatternType.TREND_PULLBACK,
            "EMA_PULLBACK": PatternType.EMA_PULLBACK,
        }
        return mapping.get(pattern_name)
    
    def _create_tracked_pattern(
        self, 
        detection: PatternDetection, 
        pattern_type: PatternType,
        ohlcv_data: OHLCVData
    ) -> Optional[TrackedPattern]:
        try:
            detection_candle = ohlcv_data.candles[-1]
            
            stop_loss = detection.invalidation_level
            target_price = detection.target_levels.get("target") if detection.target_levels else None
            
            risk_reward = None
            if stop_loss and target_price and detection_candle.close:
                risk = abs(detection_candle.close - stop_loss)
                reward = abs(target_price - detection_candle.close)
                if risk > 0:
                    risk_reward = reward / risk
            
            key_levels = dict(detection.price_levels)
            if detection.invalidation_level:
                key_levels["invalidation"] = detection.invalidation_level
            
            return TrackedPattern(
                symbol=detection.symbol,
                timeframe=detection.timeframe.value,
                pattern_type=pattern_type,
                pattern_name=detection.pattern_name,
                direction=detection.direction.value,
                
                detection_timestamp=detection.detection_timestamp,
                detection_price=detection_candle.close,
                detection_volume=detection_candle.volume,
                
                pattern_start_date=detection.start_timestamp.date() if detection.start_timestamp else date.today(),
                pattern_end_date=detection.completion_timestamp.date() if detection.completion_timestamp else date.today(),
                pattern_bars=len(ohlcv_data.candles),
                
                key_levels=key_levels,
                stop_loss=stop_loss,
                target_price=target_price,
                risk_reward_ratio=risk_reward,
                
                quality_score=detection.quality_score,
                volume_confirmation=detection.volume_confirmation,
                metadata={
                    "explanation": detection.explanation,
                    "pivots": [p.model_dump(mode="json") for p in detection.pivots] if detection.pivots else [],
                    "market_regime": detection.market_regime.value if detection.market_regime else None,
                },
                
                outcome=PatternOutcome.PENDING,
            )
        except Exception as e:
            logger.error(f"Error creating tracked pattern: {e}")
            return None
    
    def scan_all_symbols(self, symbols: Optional[List[str]] = None, timeframe: Optional[str] = None) -> Dict[str, List[TrackedPattern]]:
        symbols = symbols or self.settings.pattern_symbols
        timeframe = timeframe or self.settings.PATTERN_SCAN_TIMEFRAME
        lookback_days = self.settings.PATTERN_SCAN_LOOKBACK_DAYS
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.scan_symbol, symbol, timeframe, lookback_days): symbol 
                for symbol in symbols
            }
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    patterns = future.result()
                    if patterns:
                        saved_patterns = []
                        for p in patterns:
                            saved = self.supabase_repo.save_tracked_pattern(p)
                            saved_patterns.append(saved)
                        
                        self._create_forward_tracking(saved_patterns)
                        results[symbol] = saved_patterns
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
        
        return results
    
    def _create_forward_tracking(self, patterns: List[TrackedPattern]):
        forward_days = self.settings.PATTERN_FORWARD_DAYS
        
        for pattern in patterns:
            try:
                tracking = PatternForwardTracking(
                    tracked_pattern_id=pattern.id,
                    symbol=pattern.symbol,
                    tracking_start_date=date.today(),
                    tracking_end_date=date.today() + timedelta(days=forward_days),
                    tracking_days=forward_days,
                )
                self.supabase_repo.save_forward_tracking(tracking)
            except Exception as e:
                logger.error(f"Error creating forward tracking for {pattern.id}: {e}")
    
    def update_pending_outcomes(self):
        pending = self.supabase_repo.get_pending_patterns(self.settings.pattern_symbols)
        
        if not pending:
            logger.info("No pending patterns to update")
            return
        
        symbols = list(set(p.symbol for p in pending))
        
        for symbol in symbols:
            self._update_symbol_outcomes(symbol, pending)
    
    def _update_symbol_outcomes(self, symbol: str, pending_patterns: List[TrackedPattern]):
        symbol_pending = [p for p in pending_patterns if p.symbol == symbol]
        if not symbol_pending:
            return
        
        oldest = min(p.detection_timestamp for p in symbol_pending)
        days_back = (datetime.utcnow() - oldest).days + self.settings.PATTERN_FORWARD_DAYS + 5
        
        ohlcv_data = self.fetch_market_data(symbol, "1d", days_back)
        if not ohlcv_data:
            return
        
        price_by_date = {
            c.timestamp.date(): {"open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in ohlcv_data.candles
        }
        
        for pattern in symbol_pending:
            self._evaluate_pattern_outcome(pattern, price_by_date)
    
    def _evaluate_pattern_outcome(self, pattern: TrackedPattern, price_by_date: Dict[date, Dict[str, float]]):
        detection_date = pattern.detection_timestamp.date()
        forward_end = detection_date + timedelta(days=self.settings.PATTERN_FORWARD_DAYS)
        
        max_favorable = 0.0
        max_adverse = 0.0
        outcome = PatternOutcome.PENDING
        outcome_price = None
        outcome_timestamp = None
        days_to_outcome = None
        
        daily_data = []
        
        for i in range(self.settings.PATTERN_FORWARD_DAYS + 1):
            check_date = detection_date + timedelta(days=i)
            if check_date in price_by_date:
                data = price_by_date[check_date]
                daily_data.append({
                    "date": check_date.isoformat(),
                    **data
                })
                
                if pattern.direction == "BULLISH":
                    move = (data["high"] - pattern.detection_price) / pattern.detection_price
                    adverse = (pattern.detection_price - data["low"]) / pattern.detection_price
                else:
                    move = (pattern.detection_price - data["low"]) / pattern.detection_price
                    adverse = (data["high"] - pattern.detection_price) / pattern.detection_price
                
                max_favorable = max(max_favorable, move)
                max_adverse = max(max_adverse, adverse)
                
                if pattern.stop_loss:
                    if pattern.direction == "BULLISH" and data["low"] <= pattern.stop_loss:
                        outcome = PatternOutcome.STOP_HIT
                        outcome_price = pattern.stop_loss
                        outcome_timestamp = datetime.combine(check_date, datetime.min.time())
                        days_to_outcome = i
                        break
                    elif pattern.direction == "BEARISH" and data["high"] >= pattern.stop_loss:
                        outcome = PatternOutcome.STOP_HIT
                        outcome_price = pattern.stop_loss
                        outcome_timestamp = datetime.combine(check_date, datetime.min.time())
                        days_to_outcome = i
                        break
                
                if pattern.target_price:
                    if pattern.direction == "BULLISH" and data["high"] >= pattern.target_price:
                        outcome = PatternOutcome.TARGET_HIT
                        outcome_price = pattern.target_price
                        outcome_timestamp = datetime.combine(check_date, datetime.min.time())
                        days_to_outcome = i
                        break
                    elif pattern.direction == "BEARISH" and data["low"] <= pattern.target_price:
                        outcome = PatternOutcome.TARGET_HIT
                        outcome_price = pattern.target_price
                        outcome_timestamp = datetime.combine(check_date, datetime.min.time())
                        days_to_outcome = i
                        break
        
        if outcome == PatternOutcome.PENDING and date.today() > forward_end:
            outcome = PatternOutcome.EXPIRED
            outcome_price = price_by_date.get(forward_end, {}).get("close")
            outcome_timestamp = datetime.combine(forward_end, datetime.min.time())
            days_to_outcome = self.settings.PATTERN_FORWARD_DAYS
        
        if outcome != PatternOutcome.PENDING:
            self.supabase_repo.update_pattern_outcome(
                pattern.id,
                outcome,
                outcome_price or 0,
                outcome_timestamp or datetime.utcnow(),
                max_favorable,
                max_adverse,
                days_to_outcome
            )
            
            self._save_detailed_forward_tracking(pattern.id, daily_data, max_favorable, max_adverse)
    
    def _save_detailed_forward_tracking(
        self, 
        pattern_id: str, 
        daily_data: List[Dict],
        max_favorable: float,
        max_adverse: float
    ):
        tracking = self.supabase_repo.get_forward_tracking(pattern_id)
        if not tracking:
            return
        
        prices = [d["close"] for d in daily_data if "close" in d]
        if not prices:
            return
        
        base_price = prices[0]
        
        tracking.daily_data = daily_data
        tracking.max_high = max(d["high"] for d in daily_data)
        tracking.max_low = min(d["low"] for d in daily_data)
        
        for i, d in enumerate(daily_data):
            days = i
            price = d["close"]
            ret = (price - base_price) / base_price
            
            if days == 1:
                tracking.price_at_1d = price
                tracking.return_1d = ret
            elif days == 3:
                tracking.price_at_3d = price
                tracking.return_3d = ret
            elif days == 5:
                tracking.price_at_5d = price
                tracking.return_5d = ret
            elif days == 10:
                tracking.price_at_10d = price
                tracking.return_10d = ret
            elif days == 20:
                tracking.price_at_20d = price
                tracking.return_20d = ret
        
        tracking.max_runup = max_favorable
        tracking.max_drawdown = max_adverse
        
        self.supabase_repo.save_forward_tracking(tracking)