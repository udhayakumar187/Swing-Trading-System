from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class OrderProductType(str, Enum):
    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    product_type: OrderProductType
    price: Optional[float] = None
    trigger_price: Optional[float] = None


@dataclass
class OrderResponse:
    order_id: str
    broker_order_id: Optional[str]
    status: OrderStatus
    message: str
    timestamp: datetime
    filled_quantity: int = 0
    filled_price: Optional[float] = None


@dataclass
class Position:
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float
    product_type: OrderProductType


@dataclass
class AccountInfo:
    account_id: str
    total_cash: float
    available_cash: float
    used_margin: float
    portfolio_value: float


class BrokerProvider(ABC):
    @abstractmethod
    def login(self) -> bool:
        pass
    
    @abstractmethod
    def logout(self) -> bool:
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        pass
    
    @abstractmethod
    def get_account(self) -> AccountInfo:
        pass
    
    @abstractmethod
    def get_positions(self) -> list[Position]:
        pass
    
    @abstractmethod
    def get_orders(self) -> list[OrderResponse]:
        pass
    
    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResponse:
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderResponse:
        pass
    
    @abstractmethod
    def reconcile_orders(self) -> list[OrderResponse]:
        pass