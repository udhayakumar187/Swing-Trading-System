import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from app.brokers.base import (
    BrokerProvider, OrderRequest, OrderResponse, OrderStatus,
    OrderSide, OrderType, OrderProductType, Position, AccountInfo
)
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class AngelOneBrokerProvider(BrokerProvider):
    def __init__(self):
        self.settings = get_settings()
        self._connected = False
        self._session_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._api_key = self.settings.ANGEL_ONE_API_KEY
        self._client_id = self.settings.ANGEL_ONE_CLIENT_ID
        self._password = self.settings.ANGEL_ONE_PASSWORD
        self._totp_secret = self.settings.ANGEL_ONE_TOTP_SECRET
        
        if not all([self._api_key, self._client_id, self._password, self._totp_secret]):
            logger.warning("Angel One credentials not fully configured")
    
    def login(self) -> bool:
        if self.settings.is_dry_run:
            logger.info("[DRY_RUN] Angel One login skipped (DRY_RUN mode)")
            return False
        
        try:
            import pyotp
            import requests
            
            totp = pyotp.TOTP(self._totp_secret).now()
            
            url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": self._api_key,
            }
            payload = {
                "clientcode": self._client_id,
                "password": self._password,
                "totp": totp
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if data.get("status") and data.get("data"):
                self._session_token = data["data"].get("jwtToken")
                self._refresh_token = data["data"].get("refreshToken")
                self._feed_token = data["data"].get("feedToken")
                self._user_id = data["data"].get("clientcode")
                self._connected = True
                logger.info("Angel One login successful")
                return True
            else:
                logger.error(f"Angel One login failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Angel One login exception: {e}")
            return False
    
    def logout(self) -> bool:
        if self.settings.is_dry_run:
            return True
        
        try:
            if not self._session_token:
                return True
            
            import requests
            
            url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/logout"
            headers = {
                "Authorization": f"Bearer {self._session_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-PrivateKey": self._api_key,
            }
            payload = {"clientcode": self._client_id}
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            self._session_token = None
            self._refresh_token = None
            self._feed_token = None
            self._connected = False
            
            logger.info("Angel One logout successful")
            return True
            
        except Exception as e:
            logger.error(f"Angel One logout exception: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        return self._connected and self._session_token is not None
    
    def get_account(self) -> AccountInfo:
        if self.settings.is_dry_run:
            return AccountInfo(
                account_id="DRY_RUN",
                total_cash=0,
                available_cash=0,
                used_margin=0,
                portfolio_value=0
            )
        
        if not self.is_connected():
            raise Exception("Not connected to Angel One")
        
        try:
            import requests
            
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/getRMS"
            headers = self._get_headers()
            payload = {"clientcode": self._client_id}
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if data.get("status") and data.get("data"):
                d = data["data"]
                return AccountInfo(
                    account_id=self._client_id,
                    total_cash=float(d.get("net", 0)),
                    available_cash=float(d.get("availablecash", 0)),
                    used_margin=float(d.get("usedmargin", 0)),
                    portfolio_value=float(d.get("net", 0))
                )
            else:
                raise Exception(f"Failed to get account: {data.get('message')}")
                
        except Exception as e:
            logger.error(f"Get account failed: {e}")
            raise
    
    def get_positions(self) -> list[Position]:
        if self.settings.is_dry_run:
            return []
        
        if not self.is_connected():
            raise Exception("Not connected to Angel One")
        
        try:
            import requests
            
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/portfolio/v1/getPositions"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers, timeout=30)
            data = response.json()
            
            positions = []
            if data.get("status") and data.get("data"):
                for p in data["data"]:
                    positions.append(Position(
                        symbol=p.get("tradingsymbol", ""),
                        quantity=int(p.get("netqty", 0)),
                        average_price=float(p.get("buyavgprice", 0)),
                        current_price=float(p.get("ltp", 0)),
                        unrealized_pnl=float(p.get("unrealised", 0)),
                        product_type=OrderProductType(p.get("producttype", "DELIVERY"))
                    ))
            return positions
            
        except Exception as e:
            logger.error(f"Get positions failed: {e}")
            raise
    
    def get_orders(self) -> list[OrderResponse]:
        if self.settings.is_dry_run:
            return []
        
        if not self.is_connected():
            raise Exception("Not connected to Angel One")
        
        try:
            import requests
            
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/order/v1/getOrderBook"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers, timeout=30)
            data = response.json()
            
            orders = []
            if data.get("status") and data.get("data"):
                for o in data["data"]:
                    orders.append(OrderResponse(
                        order_id=o.get("orderid", ""),
                        broker_order_id=o.get("orderid", ""),
                        status=self._map_order_status(o.get("orderstatus", "")),
                        message=o.get("text", ""),
                        timestamp=datetime.fromisoformat(o.get("updatetime", datetime.now().isoformat())),
                        filled_quantity=int(o.get("filledshares", 0)),
                        filled_price=float(o.get("averageprice", 0)) if o.get("averageprice") else None
                    ))
            return orders
            
        except Exception as e:
            logger.error(f"Get orders failed: {e}")
            raise
    
    def place_order(self, request: OrderRequest) -> OrderResponse:
        if self.settings.is_dry_run:
            logger.warning("[DRY_RUN] Angel One order placement blocked")
            return OrderResponse(
                order_id="",
                broker_order_id=None,
                status=OrderStatus.REJECTED,
                message="LIVE trading disabled - DRY_RUN mode",
                timestamp=datetime.now()
            )
        
        if not self.is_connected():
            raise Exception("Not connected to Angel One")
        
        try:
            import requests
            
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/order/v1/placeOrder"
            headers = self._get_headers()
            
            payload = {
                "variety": "NORMAL",
                "tradingsymbol": request.symbol.replace(".NS", ""),
                "symboltoken": self._get_symbol_token(request.symbol),
                "transactiontype": request.side.value,
                "exchange": "NSE",
                "ordertype": request.order_type.value,
                "producttype": request.product_type.value,
                "duration": "DAY",
                "price": str(request.price) if request.price else "0",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(request.quantity)
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if data.get("status") and data.get("data"):
                order_id = data["data"].get("orderid", "")
                return OrderResponse(
                    order_id=order_id,
                    broker_order_id=order_id,
                    status=OrderStatus.OPEN,
                    message="Order placed successfully",
                    timestamp=datetime.now()
                )
            else:
                return OrderResponse(
                    order_id="",
                    broker_order_id=None,
                    status=OrderStatus.REJECTED,
                    message=data.get("message", "Order rejected"),
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Place order failed: {e}")
            return OrderResponse(
                order_id="",
                broker_order_id=None,
                status=OrderStatus.REJECTED,
                message=f"Exception: {str(e)}",
                timestamp=datetime.now()
            )
    
    def cancel_order(self, order_id: str) -> bool:
        if self.settings.is_dry_run:
            return True
        
        if not self.is_connected():
            raise Exception("Not connected to Angel One")
        
        try:
            import requests
            
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/order/v1/cancelOrder"
            headers = self._get_headers()
            payload = {
                "variety": "NORMAL",
                "orderid": order_id
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            return data.get("status", False)
            
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> OrderResponse:
        if self.settings.is_dry_run:
            return OrderResponse(
                order_id=order_id,
                broker_order_id=None,
                status=OrderStatus.UNKNOWN,
                message="DRY_RUN mode",
                timestamp=datetime.now()
            )
        
        if not self.is_connected():
            raise Exception("Not connected to Angel One")
        
        try:
            import requests
            
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/order/v1/getOrderDetail"
            headers = self._get_headers()
            payload = {"orderid": order_id}
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if data.get("status") and data.get("data"):
                o = data["data"]
                return OrderResponse(
                    order_id=o.get("orderid", ""),
                    broker_order_id=o.get("orderid", ""),
                    status=self._map_order_status(o.get("orderstatus", "")),
                    message=o.get("text", ""),
                    timestamp=datetime.fromisoformat(o.get("updatetime", datetime.now().isoformat())),
                    filled_quantity=int(o.get("filledshares", 0)),
                    filled_price=float(o.get("averageprice", 0)) if o.get("averageprice") else None
                )
            else:
                return OrderResponse(
                    order_id=order_id,
                    broker_order_id=None,
                    status=OrderStatus.UNKNOWN,
                    message="Order not found",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Get order status failed: {e}")
            raise
    
    def reconcile_orders(self) -> list[OrderResponse]:
        return self.get_orders()
    
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._session_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self._api_key,
            "X-ClientCode": self._client_id,
            "X-FeedToken": self._feed_token or ""
        }
    
    def _map_order_status(self, status: str) -> OrderStatus:
        status_map = {
            "OPEN": OrderStatus.OPEN,
            "COMPLETE": OrderStatus.COMPLETE,
            "REJECTED": OrderStatus.REJECTED,
            "CANCELLED": OrderStatus.CANCELLED,
            "PARTIAL": OrderStatus.PARTIAL,
            "EXPIRED": OrderStatus.EXPIRED,
        }
        return status_map.get(status.upper(), OrderStatus.UNKNOWN)
    
    def _get_symbol_token(self, symbol: str) -> str:
        symbol_map = {
            "RELIANCE.NS": "2885",
            "TCS.NS": "11536",
            "INFY.NS": "1594",
            "SBIN.NS": "3045",
            "HDFCBANK.NS": "1333",
        }
        return symbol_map.get(symbol, "0")


def create_broker_provider() -> BrokerProvider:
    settings = get_settings()
    if settings.is_live:
        return AngelOneBrokerProvider()
    else:
        from app.brokers.paper_broker import PaperBrokerProvider
        return PaperBrokerProvider(initial_cash=settings.TOTAL_PORTFOLIO_CAPITAL)