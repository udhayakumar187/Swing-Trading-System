from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import Enum
import logging

from app.strategies.ema_pullback import TradeSignal
from app.models.position import Position, PositionStatus
from app.models.account import Account
from app.models.risk_settings import RiskSettings
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class RiskCheckResult(str, Enum):
    PASSED = "PASSED"
    REJECTED = "REJECTED"


class RejectionReason(str, Enum):
    STOP_TOO_WIDE = "SIGNAL_REJECTED_STOP_TOO_WIDE"
    DUPLICATE_POSITION = "SIGNAL_REJECTED_DUPLICATE_POSITION"
    DAILY_RISK_LIMIT = "SIGNAL_REJECTED_DAILY_RISK_LIMIT"
    INSUFFICIENT_CASH = "SIGNAL_REJECTED_INSUFFICIENT_CASH"
    EVENT_RISK = "SIGNAL_REJECTED_EVENT_RISK"
    INVALID_DATA = "SIGNAL_REJECTED_INVALID_DATA"
    MAX_POSITIONS_REACHED = "SIGNAL_REJECTED_MAX_POSITIONS"
    PORTFOLIO_RISK_EXCEEDED = "SIGNAL_REJECTED_PORTFOLIO_RISK"
    POSITION_CONCENTRATION = "SIGNAL_REJECTED_POSITION_CONCENTRATION"
    SECTOR_CONCENTRATION = "SIGNAL_REJECTED_SECTOR_CONCENTRATION"


@dataclass
class RiskCheck:
    passed: bool
    reason: Optional[RejectionReason] = None
    details: Optional[str] = None
    risk_amount: float = 0.0
    quantity: int = 0
    position_value: float = 0.0


@dataclass
class PositionSizingResult:
    quantity: int
    risk_amount: float
    position_value: float
    actual_risk_pct: float
    adjusted: bool = False
    adjustment_reason: Optional[str] = None


class RiskManager:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
    
    def validate_signal(
        self,
        signal: TradeSignal,
        account: Account,
        risk_settings: RiskSettings,
        open_positions: list[Position],
        daily_pnl: float,
        available_cash: float,
        event_risk: bool = False
    ) -> RiskCheck:
        if signal.decision == "REJECTED":
            return RiskCheck(
                passed=False,
                reason=RejectionReason(signal.reason) if signal.reason else RejectionReason.INVALID_DATA,
                details=signal.reason
            )
        
        if signal.stop_loss <= 0:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.INVALID_DATA,
                details="Stop loss <= 0"
            )
        
        stop_loss_distance = signal.entry_price - signal.stop_loss
        if stop_loss_distance <= 0:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.INVALID_DATA,
                details="Entry price <= stop loss"
            )
        
        stop_loss_pct = stop_loss_distance / signal.entry_price
        if stop_loss_pct > risk_settings.max_stop_loss_percent:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.STOP_TOO_WIDE,
                details=f"Stop loss {stop_loss_pct:.2%} > max {risk_settings.max_stop_loss_percent:.2%}"
            )
        
        if signal.risk_reward_ratio < risk_settings.min_risk_reward:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.INVALID_DATA,
                details=f"Risk/reward {signal.risk_reward_ratio:.2f} < min {risk_settings.min_risk_reward}"
            )
        
        for pos in open_positions:
            if pos.symbol == signal.symbol and pos.status == PositionStatus.OPEN:
                return RiskCheck(
                    passed=False,
                    reason=RejectionReason.DUPLICATE_POSITION,
                    details=f"Active position exists for {signal.symbol}"
                )
        
        if len(open_positions) >= risk_settings.max_open_positions:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.MAX_POSITIONS_REACHED,
                details=f"Max open positions ({risk_settings.max_open_positions}) reached"
            )
        
        daily_loss_limit = account.total_capital * risk_settings.max_daily_loss_percent
        if daily_pnl <= -daily_loss_limit:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.DAILY_RISK_LIMIT,
                details=f"Daily loss {daily_pnl:.2f} exceeds limit {daily_loss_limit:.2f}"
            )
        
        if event_risk:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.EVENT_RISK,
                details="Corporate event risk detected"
            )
        
        sizing_result = self.calculate_position_size(
            signal=signal,
            account=account,
            risk_settings=risk_settings,
            available_cash=available_cash,
            open_positions=open_positions
        )
        
        if sizing_result.quantity < 1:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.INSUFFICIENT_CASH,
                details=f"Calculated quantity < 1: {sizing_result.quantity}"
            )
        
        existing_risk = self.calculate_portfolio_risk(open_positions, account.total_capital)
        new_risk = sizing_result.risk_amount
        total_risk = existing_risk + new_risk
        max_total_risk = account.total_capital * risk_settings.max_risk_percent * risk_settings.max_open_positions
        
        if total_risk > max_total_risk:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.PORTFOLIO_RISK_EXCEEDED,
                details=f"Portfolio risk {total_risk:.2f} > max {max_total_risk:.2f}"
            )
        
        position_value = sizing_result.position_value
        concentration_pct = position_value / account.total_capital
        if concentration_pct > risk_settings.max_position_concentration_percent:
            return RiskCheck(
                passed=False,
                reason=RejectionReason.POSITION_CONCENTRATION,
                details=f"Position concentration {concentration_pct:.2%} > max {risk_settings.max_position_concentration_percent:.2%}"
            )
        
        return RiskCheck(
            passed=True,
            risk_amount=sizing_result.risk_amount,
            quantity=sizing_result.quantity,
            position_value=sizing_result.position_value
        )
    
    def calculate_position_size(
        self,
        signal: TradeSignal,
        account: Account,
        risk_settings: RiskSettings,
        available_cash: float,
        open_positions: list[Position]
    ) -> PositionSizingResult:
        risk_per_share = signal.entry_price - signal.stop_loss
        if risk_per_share <= 0:
            return PositionSizingResult(
                quantity=0,
                risk_amount=0,
                position_value=0,
                actual_risk_pct=0
            )
        
        max_risk_amount = account.total_capital * risk_settings.max_risk_percent
        
        quantity = int(max_risk_amount / risk_per_share)
        
        position_value = quantity * signal.entry_price
        
        if position_value > available_cash:
            quantity = int(available_cash / signal.entry_price)
            position_value = quantity * signal.entry_price
            adjusted = True
            adjustment_reason = "Adjusted for available cash"
        else:
            adjusted = False
            adjustment_reason = None
        
        if quantity < 1:
            return PositionSizingResult(
                quantity=0,
                risk_amount=0,
                position_value=0,
                actual_risk_pct=0,
                adjusted=adjusted,
                adjustment_reason=adjustment_reason
            )
        
        actual_risk_amount = quantity * risk_per_share
        actual_risk_pct = actual_risk_amount / account.total_capital
        
        return PositionSizingResult(
            quantity=quantity,
            risk_amount=actual_risk_amount,
            position_value=position_value,
            actual_risk_pct=actual_risk_pct,
            adjusted=adjusted,
            adjustment_reason=adjustment_reason
        )
    
    def calculate_portfolio_risk(self, positions: list[Position], total_capital: float) -> float:
        total_risk = 0.0
        for pos in positions:
            if pos.status == PositionStatus.OPEN:
                risk_per_share = pos.entry_price - pos.stop_loss
                if risk_per_share > 0:
                    total_risk += risk_per_share * pos.quantity
        return total_risk
    
    def check_daily_loss_limit(self, account: Account, risk_settings: RiskSettings, daily_pnl: float) -> tuple[bool, Optional[str]]:
        daily_loss_limit = account.total_capital * risk_settings.max_daily_loss_percent
        if daily_pnl <= -daily_loss_limit:
            return True, f"Daily loss limit exceeded: {daily_pnl:.2f} <= -{daily_loss_limit:.2f}"
        return False, None
    
    def can_open_new_positions(self, open_positions: list[Position], risk_settings: RiskSettings) -> tuple[bool, Optional[str]]:
        open_count = sum(1 for p in open_positions if p.status == PositionStatus.OPEN)
        if open_count >= risk_settings.max_open_positions:
            return False, f"Max open positions ({risk_settings.max_open_positions}) reached"
        return True, None