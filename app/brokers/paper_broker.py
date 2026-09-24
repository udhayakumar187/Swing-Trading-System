import uuid
from datetime import datetime
from typing import Optional
import logging
from threading import Lock

from app.brokers.base import (
    BrokerProvider, OrderRequest, OrderResponse, OrderStatus,
    OrderSide, OrderType, OrderProductType, Position, AccountInfo
)
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class PaperBrokerProvider(BrokerProvider):
    def __init__(self, initial_cash: float = 100000.0):
        self.settings = get_settings()
        self._connected = False
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, OrderResponse] = {}
        self._cash = initial_cash
        self._used_margin = 0.0
        self._lock = Lock()
        self._initial_cash = initial_cash
    
    def login(self) -> bool:
        with self._lock:
            self._connected = True
            logger.info("[DRY_RUN] Paper broker logged in")
            return True
    
    def logout(self) -> bool:
        with self._lock:
            self._connected = False
            logger.info("[DRY_RUN] Paper broker logged out")
            return True
    
    def is_connected(self) -> bool:
        return self._connected
    
    def get_account(self) -> AccountInfo:
        with self._lock:
            portfolio_value = self._cash + self._used_margin
            for pos in self._positions.values():
                portfolio_value += pos.quantity * pos.current_price
            
            return AccountInfo(
                account_id="PAPER_ACCOUNT",
                total_cash=self._initial_cash,
                available_cash=self._cash,
                used_margin=self._used_margin,
                portfolio_value=portfolio_value
            )
    
    def get_positions(self) -> list[Position]:
        with self._lock:
            return list(self._positions.values())
    
    def get_orders(self) -> list[OrderResponse]:
        with self._lock:
            return list(self._orders.values())
    
    def place_order(self, request: OrderRequest) -> OrderResponse:
        with self._lock:
            if not self._connected:
                return OrderResponse(
                    order_id="",
                    broker_order_id=None,
                    status=OrderStatus.REJECTED,
                    message="Not connected",
                    timestamp=datetime.now()
                )
            
            order_id = f"PAPER_{uuid.uuid4().hex[:12].upper()}"
            
            if request.order_type != OrderType.MARKET:
                return OrderResponse(
                    order_id=order_id,
                    broker_order_id=order_id,
                    status=OrderStatus.REJECTED,
                    message="Only MARKET orders supported in paper trading",
                    timestamp=datetime.now()
                )
            
            if request.product_type != OrderProductType.DELIVERY:
                return OrderResponse(
                    order_id=order_id,
                    broker_order_id=order_id,
                    status=OrderStatus.REJECTED,
                    message="Only DELIVERY product type supported",
                    timestamp=datetime.now()
                )
            
            if request.side == OrderSide.BUY:
                return self._execute_buy(order_id, request)
            else:
                return self._execute_sell(order_id, request)
    
    def _execute_buy(self, order_id: str, request: OrderRequest) -> OrderResponse:
        estimated_price = request.price or 0
        if estimated_price <= 0:
            estimated_price = self._get_last_price(request.symbol)
        
        if estimated_price <= 0:
            return OrderResponse(
                order_id=order_id,
                broker_order_id=order_id,
                status=OrderStatus.REJECTED,
                message="Cannot determine price for symbol",
                timestamp=datetime.now()
            )
        
        required_cash = request.quantity * estimated_price
        
        if required_cash > self._cash:
            return OrderResponse(
                order_id=order_id,
                broker_order_id=order_id,
                status=OrderStatus.REJECTED,
                message=f"Insufficient cash: need {required_cash:.2f}, have {self._cash:.2f}",
                timestamp=datetime.now()
            )
        
        self._cash -= required_cash
        self._used_margin += required_cash
        
        filled_price = estimated_price
        
        if request.symbol in self._positions:
            pos = self._positions[request.symbol]
            total_qty = pos.quantity + request.quantity
            total_cost = (pos.quantity * pos.average_price) + (request.quantity * filled_price)
            pos.average_price = total_cost / total_qty
            pos.quantity = total_qty
        else:
            self._positions[request.symbol] = Position(
                symbol=request.symbol,
                quantity=request.quantity,
                average_price=filled_price,
                current_price=filled_price,
                unrealized_pnl=0.0,
                product_type=request.product_type
            )
        
        order_response = OrderResponse(
            order_id=order_id,
            broker_order_id=order_id,
            status=OrderStatus.COMPLETE,
            message="[DRY_RUN] Order filled",
            timestamp=datetime.now(),
            filled_quantity=request.quantity,
            filled_price=filled_price
        )
        
        self._orders[order_id] = order_response
        
        logger.info(
            f"[DRY_RUN] BUY executed: {request.symbol} x{request.quantity} "
            f"@ {filled_price:.2f} (Order: {order_id})"
        )
        
        return order_response
    
    def _execute_sell(self, order_id: str, request: OrderRequest) -> OrderResponse:
        if request.symbol not in self._positions:
            return OrderResponse(
                order_id=order_id,
                broker_order_id=order_id,
                status=OrderStatus.REJECTED,
                message=f"No position to sell for {request.symbol}",
                timestamp=datetime.now()
            )
        
        pos = self._positions[request.symbol]
        
        if pos.quantity < request.quantity:
            return OrderResponse(
                order_id=order_id,
                broker_order_id=order_id,
                status=OrderStatus.REJECTED,
                message=f"Insufficient quantity: have {pos.quantity}, need {request.quantity}",
                timestamp=datetime.now()
            )
        
        filled_price = request.price or pos.current_price
        
        if filled_price <= 0:
            filled_price = self._get_last_price(request.symbol)
        
        if filled_price <= 0:
            filled_price = pos.average_price
        
        proceeds = request.quantity * filled_price
        self._cash += proceeds
        self._used_margin -= request.quantity * pos.average_price
        
        pos.quantity -= request.quantity
        pos.current_price = filled_price
        
        if pos.quantity == 0:
            del self._positions[request.symbol]
        
        order_response = OrderResponse(
            order_id=order_id,
            broker_order_id=order_id,
            status=OrderStatus.COMPLETE,
            message="[DRY_RUN] Order filled",
            timestamp=datetime.now(),
            filled_quantity=request.quantity,
            filled_price=filled_price
        )
        
        self._orders[order_id] = order_response
        
        logger.info(
            f"[DRY_RUN] SELL executed: {request.symbol} x{request.quantity} "
            f"@ {filled_price:.2f} (Order: {order_id})"
        )
        
        return order_response
    
    def _get_last_price(self, symbol: str) -> float:
        if symbol in self._positions:
            return self._positions[symbol].current_price
        return 0.0
    
    def update_market_price(self, symbol: str, price: float):
        with self._lock:
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.current_price = price
                pos.unrealized_pnl = (price - pos.average_price) * pos.quantity
    
    def cancel_order(self, order_id: str) -> bool:
        with self._lock:
            if order_id in self._orders:
                order = self._orders[order_id]
                if order.status in [OrderStatus.PENDING, OrderStatus.OPEN]:
                    order.status = OrderStatus.CANCELLED
                    order.message = "[DRY_RUN] Cancelled"
                    return True
            return False
    
    def get_order_status(self, order_id: str) -> OrderResponse:
        with self._lock:
            return self._orders.get(order_id, OrderResponse(
                order_id=order_id,
                broker_order_id=None,
                status=OrderStatus.UNKNOWN,
                message="Order not found",
                timestamp=datetime.now()
            ))
    
    def reconcile_orders(self) -> list[OrderResponse]:
        with self._lock:
            return list(self._orders.values())
    
    def reset(self):
        with self._lock:
            self._positions.clear()
            self._orders.clear()
            self._cash = self._initial_cash
            self._used_margin = 0.0
            logger.info("[DRY_RUN] Paper broker reset")