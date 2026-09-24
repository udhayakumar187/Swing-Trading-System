import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from app.brokers import (
    BrokerProvider, OrderRequest, OrderResponse, OrderStatus,
    OrderSide, OrderType, OrderProductType, create_broker_provider
)
from app.models.order import Order, OrderSide as ModelOrderSide, OrderType as ModelOrderType, OrderProductType as ModelOrderProductType, OrderStatus as ModelOrderStatus
from app.models.position import Position, PositionStatus
from app.models.signal import Signal, SignalDecision
from app.models.trading_run import TradingRun, TradingRunStatus
from app.strategies.ema_pullback import TradeSignal
from app.core.database import get_db
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    LIVE = "LIVE"


@dataclass
class ExecutionResult:
    success: bool
    order: Optional[Order] = None
    position: Optional[Position] = None
    broker_response: Optional[OrderResponse] = None
    error_message: Optional[str] = None


class ExecutionService:
    def __init__(self, broker: Optional[BrokerProvider] = None):
        self.settings = get_settings()
        self.broker = broker or create_broker_provider()
        self.execution_mode = ExecutionMode.DRY_RUN if self.settings.is_dry_run else ExecutionMode.LIVE
    
    def execute_signal(
        self,
        signal: TradeSignal,
        trading_run: TradingRun,
        account_id: int
    ) -> ExecutionResult:
        logger.info(
            f"[{self.execution_mode.value}] Executing signal: {signal.symbol} "
            f"qty={signal.quantity} entry={signal.entry_price:.2f} "
            f"sl={signal.stop_loss:.2f} target={signal.target_price:.2f} "
            f"risk={signal.risk_amount:.2f} R:R={signal.risk_reward_ratio:.2f}"
        )
        
        if self.execution_mode == ExecutionMode.DRY_RUN:
            logger.info(f"[DRY_RUN] Simulated order - NO REAL BROKER CALL")
        
        db = next(get_db())
        try:
            order = self._create_order_record(signal, trading_run, account_id, db)
            db.add(order)
            db.commit()
            db.refresh(order)
            
            if self.execution_mode == ExecutionMode.LIVE:
                broker_response = self._submit_to_broker(signal, order)
            else:
                broker_response = self._simulate_broker_fill(signal, order)
            
            order.broker_order_id = broker_response.broker_order_id
            order.status = self._map_broker_status(broker_response.status)
            order.filled_at = broker_response.timestamp if broker_response.status == OrderStatus.COMPLETE else None
            order.error_message = broker_response.message if broker_response.status == OrderStatus.REJECTED else None
            db.commit()
            
            if broker_response.status == OrderStatus.COMPLETE:
                position = self._create_position(signal, order, trading_run, account_id, db)
                db.add(position)
                db.commit()
                db.refresh(position)
                
                signal.decision = SignalDecision.EXECUTED
                db.commit()
                
                logger.info(f"[{self.execution_mode.value}] Order filled: {order.broker_order_id}")
                return ExecutionResult(
                    success=True,
                    order=order,
                    position=position,
                    broker_response=broker_response
                )
            else:
                signal.decision = SignalDecision.REJECTED
                signal.reason = f"BROKER_REJECTED: {broker_response.message}"
                db.commit()
                
                logger.warning(f"[{self.execution_mode.value}] Order rejected: {broker_response.message}")
                return ExecutionResult(
                    success=False,
                    order=order,
                    broker_response=broker_response,
                    error_message=broker_response.message
                )
                
        except Exception as e:
            logger.error(f"[{self.execution_mode.value}] Execution failed: {e}")
            db.rollback()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
        finally:
            db.close()
    
    def _create_order_record(
        self,
        signal: TradeSignal,
        trading_run: TradingRun,
        account_id: int,
        db
    ) -> Order:
        return Order(
            account_id=account_id,
            symbol=signal.symbol,
            side=ModelOrderSide.BUY,
            quantity=signal.quantity,
            order_type=ModelOrderType.MARKET,
            product_type=ModelOrderProductType.DELIVERY,
            price=signal.entry_price,
            status=ModelOrderStatus.PENDING,
            paper_or_live=self.execution_mode.value
        )
    
    def _submit_to_broker(self, signal: TradeSignal, order: Order) -> OrderResponse:
        request = OrderRequest(
            symbol=signal.symbol,
            side=OrderSide.BUY,
            quantity=signal.quantity,
            order_type=OrderType.MARKET,
            product_type=OrderProductType.DELIVERY,
            price=signal.entry_price
        )
        return self.broker.place_order(request)
    
    def _simulate_broker_fill(self, signal: TradeSignal, order: Order) -> OrderResponse:
        from app.brokers.paper_broker import PaperBrokerProvider
        
        if isinstance(self.broker, PaperBrokerProvider):
            request = OrderRequest(
                symbol=signal.symbol,
                side=OrderSide.BUY,
                quantity=signal.quantity,
                order_type=OrderType.MARKET,
                product_type=OrderProductType.DELIVERY,
                price=signal.entry_price
            )
            return self.broker.place_order(request)
        else:
            return OrderResponse(
                order_id=f"SIM_{order.id}",
                broker_order_id=f"SIM_{order.id}",
                status=OrderStatus.COMPLETE,
                message="[DRY_RUN] Simulated fill",
                timestamp=datetime.now(),
                filled_quantity=signal.quantity,
                filled_price=signal.entry_price
            )
    
    def _map_broker_status(self, broker_status: OrderStatus) -> ModelOrderStatus:
        mapping = {
            OrderStatus.PENDING: ModelOrderStatus.PENDING,
            OrderStatus.OPEN: ModelOrderStatus.OPEN,
            OrderStatus.PARTIAL: ModelOrderStatus.PARTIAL,
            OrderStatus.COMPLETE: ModelOrderStatus.COMPLETE,
            OrderStatus.REJECTED: ModelOrderStatus.REJECTED,
            OrderStatus.CANCELLED: ModelOrderStatus.CANCELLED,
            OrderStatus.EXPIRED: ModelOrderStatus.EXPIRED,
            OrderStatus.UNKNOWN: ModelOrderStatus.UNKNOWN,
        }
        return mapping.get(broker_status, ModelOrderStatus.UNKNOWN)
    
    def _create_position(
        self,
        signal: TradeSignal,
        order: Order,
        trading_run: TradingRun,
        account_id: int,
        db
    ) -> Position:
        return Position(
            account_id=account_id,
            symbol=signal.symbol,
            exchange="NSE",
            quantity=signal.quantity,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            target_price=signal.target_price,
            status=PositionStatus.OPEN,
            entry_timestamp=datetime.now(),
            strategy_name=signal.strategy_name,
            signal_id=None,
            broker_order_id=order.broker_order_id,
            paper_or_live=self.execution_mode.value
        )
    
    def reconcile_orders(self, account_id: int) -> list[Order]:
        db = next(get_db())
        try:
            pending_orders = db.query(Order).filter(
                Order.account_id == account_id,
                Order.status.in_([ModelOrderStatus.PENDING, ModelOrderStatus.OPEN])
            ).all()
            
            reconciled = []
            for order in pending_orders:
                if self.execution_mode == ExecutionMode.LIVE and order.broker_order_id:
                    broker_response = self.broker.get_order_status(order.broker_order_id)
                    order.status = self._map_broker_status(broker_response.status)
                    order.filled_at = broker_response.timestamp if broker_response.status == OrderStatus.COMPLETE else None
                    order.error_message = broker_response.message if broker_response.status == OrderStatus.REJECTED else None
                else:
                    broker_response = self.broker.get_order_status(order.broker_order_id)
                    order.status = self._map_broker_status(broker_response.status)
                
                if order.status == ModelOrderStatus.COMPLETE and not order.filled_at:
                    order.filled_at = datetime.now()
                
                reconciled.append(order)
            
            db.commit()
            return reconciled
            
        except Exception as e:
            logger.error(f"Order reconciliation failed: {e}")
            db.rollback()
            return []
        finally:
            db.close()