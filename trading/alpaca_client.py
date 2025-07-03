import alpaca_trade_api as tradeapi
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from config import config

class AlpacaClient:
    """Alpaca trading client for executing biotech trades"""
    
    def __init__(self):
        self.api_key = config.ALPACA_API_KEY
        self.secret_key = config.ALPACA_SECRET_KEY
        self.base_url = config.ALPACA_BASE_URL
        self.api = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Alpaca API client"""
        if not self.api_key or not self.secret_key:
            logger.warning("Alpaca API credentials not provided. Trading will be disabled.")
            return
        
        try:
            self.api = tradeapi.REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url,
                api_version='v2'
            )
            
            # Test connection
            account = self.api.get_account()
            logger.info(f"Connected to Alpaca API. Account status: {account.status}")
            logger.info(f"Buying power: ${float(account.buying_power):,.2f}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca client: {e}")
            self.api = None
    
    def is_connected(self) -> bool:
        """Check if client is connected to Alpaca"""
        return self.api is not None
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.is_connected():
            return {}
        
        try:
            account = self.api.get_account()
            # Convert the Pydantic Account model to a plain dict so we
            # don't accidentally access missing attributes when the SDK changes.
            # `__dict__` is available on both old and new SDK versions.
            acc_dict = account.__dict__ if hasattr(account, "__dict__") else dict(account)

            # Build a safe, backward-compatible response dict
            return {
                'account_id': acc_dict.get('id'),
                'status': acc_dict.get('status'),
                'cash': float(acc_dict.get('cash', 0)),
                'buying_power': float(acc_dict.get('buying_power', 0)),
                'portfolio_value': float(acc_dict.get('portfolio_value', 0)),
                'equity': float(acc_dict.get('equity', 0)),
                'pattern_day_trader': acc_dict.get('pattern_day_trader', False)
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        if not self.is_connected():
            return []
        
        try:
            positions = self.api.list_positions()
            
            position_list = []
            for position in positions:
                position_data = {
                    'symbol': position.symbol,
                    'quantity': float(position.qty),
                    'side': position.side,
                    'market_value': float(position.market_value),
                    'cost_basis': float(position.cost_basis),
                    'unrealized_pnl': float(position.unrealized_pnl),
                    'unrealized_pnl_percent': float(position.unrealized_plpc) * 100,
                    'current_price': float(position.current_price),
                    'avg_entry_price': float(position.avg_entry_price)
                }
                position_list.append(position_data)
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict[str, Any]]:
        """Get orders"""
        if not self.is_connected():
            return []
        
        try:
            orders = self.api.list_orders(
                status=status,
                limit=limit,
                direction='desc'
            )
            
            order_list = []
            for order in orders:
                order_data = {
                    'id': order.id,
                    'symbol': order.symbol,
                    'side': order.side,
                    'quantity': float(order.qty),
                    'filled_quantity': float(order.filled_qty or 0),
                    'order_type': order.order_type,
                    'status': order.status,
                    'limit_price': float(order.limit_price) if order.limit_price else None,
                    'stop_price': float(order.stop_price) if order.stop_price else None,
                    'created_at': order.created_at,
                    'updated_at': order.updated_at,
                    'filled_at': order.filled_at
                }
                order_list.append(order_data)
            
            return order_list
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = 'market', 
                   limit_price: Optional[float] = None, stop_price: Optional[float] = None,
                   time_in_force: str = 'day') -> Optional[Dict[str, Any]]:
        """Place a trading order"""
        if not self.is_connected():
            logger.error("Cannot place order: Not connected to Alpaca")
            return None
        
        try:
            # Validate inputs
            if side not in ['buy', 'sell']:
                raise ValueError(f"Invalid side: {side}")
            
            if order_type not in ['market', 'limit', 'stop', 'stop_limit']:
                raise ValueError(f"Invalid order type: {order_type}")
            
            if quantity <= 0:
                raise ValueError(f"Invalid quantity: {quantity}")
            
            # Check if we can trade this symbol
            if not self.is_tradeable(symbol):
                raise ValueError(f"Symbol {symbol} is not tradeable")
            
            # Build order parameters
            order_params = {
                'symbol': symbol,
                'qty': quantity,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force
            }
            
            if order_type in ['limit', 'stop_limit'] and limit_price:
                order_params['limit_price'] = limit_price
            
            if order_type in ['stop', 'stop_limit'] and stop_price:
                order_params['stop_price'] = stop_price
            
            # Place the order
            order = self.api.submit_order(**order_params)
            
            logger.info(f"Order placed: {side} {quantity} shares of {symbol} ({order_type})")
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'side': order.side,
                'quantity': float(order.qty),
                'order_type': order.order_type,
                'status': order.status,
                'limit_price': float(order.limit_price) if order.limit_price else None,
                'stop_price': float(order.stop_price) if order.stop_price else None,
                'created_at': order.created_at
            }
            
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if not self.is_connected():
            return False
        
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_market_data(self, symbol: str, timeframe: str = '1Day', 
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Get market data for a symbol"""
        if not self.is_connected():
            return []
        
        try:
            # Get bars data
            end = datetime.now()
            start = end - timedelta(days=100)
            
            bars = self.api.get_bars(
                symbol,
                timeframe,
                start=start.isoformat(),
                end=end.isoformat(),
                limit=limit
            )
            
            bar_list = []
            for bar in bars:
                bar_data = {
                    'timestamp': bar.t,
                    'open': float(bar.o),
                    'high': float(bar.h),
                    'low': float(bar.l),
                    'close': float(bar.c),
                    'volume': int(bar.v)
                }
                bar_list.append(bar_data)
            
            return bar_list
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return []
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        if not self.is_connected():
            return None
        
        try:
            # Get latest trade
            latest_trade = self.api.get_latest_trade(symbol)
            return float(latest_trade.price)
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def is_tradeable(self, symbol: str) -> bool:
        """Check if a symbol is tradeable"""
        if not self.is_connected():
            return False
        
        try:
            asset = self.api.get_asset(symbol)
            return asset.tradable and asset.status == 'active'
        except Exception as e:
            logger.warning(f"Error checking if {symbol} is tradeable: {e}")
            return False
    
    def get_portfolio_history(self, period: str = '1M') -> Dict[str, Any]:
        """Get portfolio performance history"""
        if not self.is_connected():
            return {}
        
        try:
            portfolio_history = self.api.get_portfolio_history(
                period=period,
                timeframe='1Day'
            )
            
            return {
                'equity': [float(x) for x in portfolio_history.equity],
                'profit_loss': [float(x) for x in portfolio_history.profit_loss],
                'profit_loss_pct': [float(x) for x in portfolio_history.profit_loss_pct],
                'timestamps': portfolio_history.timestamp
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return {}
    
    def calculate_position_size(self, symbol: str, risk_amount: float, 
                              stop_loss_price: float) -> Optional[int]:
        """Calculate position size based on risk amount and stop loss"""
        current_price = self.get_current_price(symbol)
        if not current_price:
            return None
        
        try:
            # Calculate risk per share
            risk_per_share = abs(current_price - stop_loss_price)
            
            if risk_per_share <= 0:
                return None
            
            # Calculate position size
            position_size = int(risk_amount / risk_per_share)
            
            # Get account buying power
            account = self.get_account_info()
            buying_power = account.get('buying_power', 0)
            
            # Make sure we don't exceed buying power
            max_shares = int(buying_power / current_price)
            position_size = min(position_size, max_shares)
            
            return max(1, position_size)  # At least 1 share
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return None
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get market status"""
        if not self.is_connected():
            return {}
        
        try:
            clock = self.api.get_clock()
            calendar = self.api.get_calendar(start=datetime.now().date(), 
                                           end=datetime.now().date())[0]
            
            return {
                'is_open': clock.is_open,
                'next_open': clock.next_open,
                'next_close': clock.next_close,
                'market_open': calendar.open,
                'market_close': calendar.close
            }
            
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {}
    
    def close_position(self, symbol: str, percentage: float = 100.0) -> Optional[Dict[str, Any]]:
        """Close a position (partially or fully)"""
        if not self.is_connected():
            return None
        
        try:
            # Get current position
            position = self.api.get_position(symbol)
            
            if not position:
                logger.warning(f"No position found for {symbol}")
                return None
            
            # Calculate quantity to close
            current_qty = float(position.qty)
            qty_to_close = int(current_qty * (percentage / 100.0))
            
            if qty_to_close <= 0:
                return None
            
            # Determine side (opposite of current position)
            side = 'sell' if current_qty > 0 else 'buy'
            
            # Place closing order
            return self.place_order(
                symbol=symbol,
                quantity=qty_to_close,
                side=side,
                order_type='market'
            )
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return None