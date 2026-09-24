import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.patterns.models.pattern_tracking import (
    TrackedPattern,
    PatternForwardTracking,
    PatternType,
    PatternOutcome,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SupabasePatternRepository:
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._init_client()
    
    def _init_client(self):
        if not self.settings.has_supabase:
            logger.warning("Supabase not configured, repository will not work")
            return
        
        try:
            from supabase import create_client
            self._client = create_client(self.settings.SUPABASE_URL, self.settings.SUPABASE_KEY)
            logger.info("Supabase client initialized")
        except ImportError:
            logger.error("supabase-py not installed. Run: pip install supabase")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
    
    def _ensure_client(self):
        if self._client is None:
            self._init_client()
        if self._client is None:
            raise RuntimeError("Supabase client not initialized. Check configuration.")
        return self._client
    
    def save_tracked_pattern(self, pattern: TrackedPattern) -> TrackedPattern:
        client = self._ensure_client()
        
        data = pattern.model_dump(mode="json")
        if pattern.id is None:
            data["id"] = str(uuid4())
        
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()
        
        if isinstance(pattern.detection_timestamp, datetime):
            data["detection_timestamp"] = pattern.detection_timestamp.isoformat()
        if isinstance(pattern.pattern_start_date, date):
            data["pattern_start_date"] = pattern.pattern_start_date.isoformat()
        if isinstance(pattern.pattern_end_date, date):
            data["pattern_end_date"] = pattern.pattern_end_date.isoformat()
        if isinstance(pattern.outcome_timestamp, datetime):
            data["outcome_timestamp"] = pattern.outcome_timestamp.isoformat()
        
        result = client.table("tracked_patterns").upsert(data).execute()
        
        if result.data:
            saved = TrackedPattern(**result.data[0])
            logger.info(f"Saved tracked pattern {saved.id} for {saved.symbol} - {saved.pattern_type}")
            return saved
        
        raise RuntimeError("Failed to save tracked pattern")
    
    def get_tracked_pattern(self, pattern_id: str) -> Optional[TrackedPattern]:
        client = self._ensure_client()
        
        result = client.table("tracked_patterns").select("*").eq("id", pattern_id).single().execute()
        
        if result.data:
            return TrackedPattern(**result.data)
        return None
    
    def get_patterns_by_symbol(
        self, 
        symbol: str, 
        pattern_type: Optional[PatternType] = None,
        outcome: Optional[PatternOutcome] = None,
        limit: int = 100
    ) -> List[TrackedPattern]:
        client = self._ensure_client()
        
        query = client.table("tracked_patterns").select("*").eq("symbol", symbol)
        
        if pattern_type:
            query = query.eq("pattern_type", pattern_type.value)
        if outcome:
            query = query.eq("outcome", outcome.value)
        
        result = query.order("detection_timestamp", desc=True).limit(limit).execute()
        
        return [TrackedPattern(**row) for row in result.data]
    
    def get_pending_patterns(self, symbols: Optional[List[str]] = None) -> List[TrackedPattern]:
        client = self._ensure_client()
        
        query = client.table("tracked_patterns").select("*").eq("outcome", PatternOutcome.PENDING.value)
        
        if symbols:
            query = query.in_("symbol", symbols)
        
        result = query.order("detection_timestamp", desc=True).execute()
        
        return [TrackedPattern(**row) for row in result.data]
    
    def update_pattern_outcome(
        self, 
        pattern_id: str, 
        outcome: PatternOutcome, 
        outcome_price: float,
        outcome_timestamp: datetime,
        max_favorable: Optional[float] = None,
        max_adverse: Optional[float] = None,
        days_to_outcome: Optional[int] = None
    ) -> Optional[TrackedPattern]:
        client = self._ensure_client()
        
        updates = {
            "outcome": outcome.value,
            "outcome_price": outcome_price,
            "outcome_timestamp": outcome_timestamp.isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if max_favorable is not None:
            updates["max_favorable_move"] = max_favorable
        if max_adverse is not None:
            updates["max_adverse_move"] = max_adverse
        if days_to_outcome is not None:
            updates["days_to_outcome"] = days_to_outcome
        
        result = client.table("tracked_patterns").update(updates).eq("id", pattern_id).execute()
        
        if result.data:
            return TrackedPattern(**result.data[0])
        return None
    
    def save_forward_tracking(self, tracking: PatternForwardTracking) -> PatternForwardTracking:
        client = self._ensure_client()
        
        data = tracking.model_dump(mode="json")
        if tracking.id is None:
            data["id"] = str(uuid4())
        
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()
        
        if isinstance(tracking.tracking_start_date, date):
            data["tracking_start_date"] = tracking.tracking_start_date.isoformat()
        if isinstance(tracking.tracking_end_date, date):
            data["tracking_end_date"] = tracking.tracking_end_date.isoformat()
        
        result = client.table("pattern_forward_tracking").upsert(data).execute()
        
        if result.data:
            return PatternForwardTracking(**result.data[0])
        
        raise RuntimeError("Failed to save forward tracking")
    
    def get_forward_tracking(self, tracked_pattern_id: str) -> Optional[PatternForwardTracking]:
        client = self._ensure_client()
        
        result = client.table("pattern_forward_tracking").select("*").eq("tracked_pattern_id", tracked_pattern_id).single().execute()
        
        if result.data:
            return PatternForwardTracking(**result.data)
        return None
    
    def get_pattern_statistics(
        self, 
        pattern_type: Optional[PatternType] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        client = self._ensure_client()
        
        query = client.table("tracked_patterns").select("*")
        
        if pattern_type:
            query = query.eq("pattern_type", pattern_type.value)
        if symbol:
            query = query.eq("symbol", symbol)
        
        result = query.execute()
        
        if not result.data:
            return []
        
        patterns = [TrackedPattern(**row) for row in result.data]
        
        stats = {}
        for p in patterns:
            key = f"{p.pattern_type.value}_{p.symbol}"
            if key not in stats:
                stats[key] = {
                    "pattern_type": p.pattern_type.value,
                    "symbol": p.symbol,
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "pending": 0,
                    "returns": [],
                    "r_multiples": [],
                    "days_to_outcome": [],
                }
            
            stats[key]["total"] += 1
            
            if p.outcome == PatternOutcome.TARGET_HIT:
                stats[key]["successful"] += 1
            elif p.outcome in [PatternOutcome.STOP_HIT, PatternOutcome.INVALIDATED]:
                stats[key]["failed"] += 1
            else:
                stats[key]["pending"] += 1
            
            if p.outcome in [PatternOutcome.TARGET_HIT, PatternOutcome.STOP_HIT, PatternOutcome.PARTIAL]:
                if p.detection_price and p.outcome_price:
                    ret = (p.outcome_price - p.detection_price) / p.detection_price
                    if p.direction == "BEARISH":
                        ret = -ret
                    stats[key]["returns"].append(ret)
                    
                    if p.stop_loss and p.detection_price:
                        risk = abs(p.detection_price - p.stop_loss)
                        if risk > 0:
                            r_mult = abs(p.outcome_price - p.detection_price) / risk
                            stats[key]["r_multiples"].append(r_mult)
                    
                    if p.days_to_outcome:
                        stats[key]["days_to_outcome"].append(p.days_to_outcome)
        
        result_list = []
        for key, s in stats.items():
            total = s["total"]
            if total > 0:
                win_rate = s["successful"] / total if total > 0 else 0
                avg_return = sum(s["returns"]) / len(s["returns"]) if s["returns"] else 0
                avg_r = sum(s["r_multiples"]) / len(s["r_multiples"]) if s["r_multiples"] else 0
                avg_days = sum(s["days_to_outcome"]) / len(s["days_to_outcome"]) if s["days_to_outcome"] else 0
                
                result_list.append({
                    "pattern_type": s["pattern_type"],
                    "symbol": s["symbol"],
                    "total_detections": total,
                    "successful": s["successful"],
                    "failed": s["failed"],
                    "pending": s["pending"],
                    "win_rate": round(win_rate * 100, 2),
                    "avg_return_pct": round(avg_return * 100, 2),
                    "avg_r_multiple": round(avg_r, 2),
                    "avg_days_to_outcome": round(avg_days, 1),
                })
        
        return result_list


_supabase_repo: Optional[SupabasePatternRepository] = None


def get_supabase_repository() -> SupabasePatternRepository:
    global _supabase_repo
    if _supabase_repo is None:
        _supabase_repo = SupabasePatternRepository()
    return _supabase_repo