from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from loguru import logger
from config import config

class RiskManager:
    """Risk management system for biotech trading"""
    
    def __init__(self):
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.current_positions = {}
        
    def check_trade_limits(self, signal: Dict[str, Any], account_info: Dict[str, Any]) -> Dict[str, bool]:
        """Check if trade passes risk management rules"""
        checks = {
            'max_daily_trades': self._check_max_daily_trades(),
            'position_size_limit': self._check_position_size_limit(signal, account_info),
            'portfolio_concentration': self._check_portfolio_concentration(signal),
            'market_hours': self._check_market_hours(),
            'sufficient_capital': self._check_sufficient_capital(signal, account_info),
            'stop_loss_required': self._check_stop_loss_required(signal),
            'volatility_limit': self._check_volatility_limit(signal)
        }
        
        # Overall approval
        checks['approved'] = all(checks.values())
        
        return checks
    
    def _check_max_daily_trades(self) -> bool:
        """Check if we haven't exceeded daily trade limit"""
        return self.daily_trades < config.MAX_DAILY_TRADES
    
    def _check_position_size_limit(self, signal: Dict[str, Any], account_info: Dict[str, Any]) -> bool:
        """Check if position size is within limits"""
        portfolio_value = account_info.get('portfolio_value', 0)
        if portfolio_value <= 0:
            return False
        
        position_value = signal.get('position_size', 0) * portfolio_value
        max_position_value = config.MAX_POSITION_SIZE * portfolio_value
        
        return position_value <= max_position_value
    
    def _check_portfolio_concentration(self, signal: Dict[str, Any]) -> bool:
        """Check if adding this position would create excessive concentration"""
        symbol = signal.get('symbol')
        if not symbol:
            return False
        
        # Check sector concentration (all biotech positions)
        biotech_allocation = sum(pos.get('allocation', 0) for pos in self.current_positions.values())
        new_allocation = signal.get('position_size', 0)
        
        # Don't allow more than 80% in biotech sector
        return (biotech_allocation + new_allocation) <= 0.8
    
    def _check_market_hours(self) -> bool:
        """Check if market is open or opening soon"""
        now = datetime.now().time()
        market_open = config.TRADING_HOURS['start']
        market_close = config.TRADING_HOURS['end']
        
        # Allow trading 30 minutes before market open to 30 minutes after close
        extended_open = (datetime.combine(datetime.today(), market_open) - timedelta(minutes=30)).time()
        extended_close = (datetime.combine(datetime.today(), market_close) + timedelta(minutes=30)).time()
        
        return extended_open <= now <= extended_close
    
    def _check_sufficient_capital(self, signal: Dict[str, Any], account_info: Dict[str, Any]) -> bool:
        """Check if we have sufficient capital for the trade"""
        buying_power = account_info.get('buying_power', 0)
        portfolio_value = account_info.get('portfolio_value', 0)
        
        if portfolio_value <= 0:
            return False
        
        required_capital = signal.get('position_size', 0) * portfolio_value
        
        # Need at least 110% of required capital to account for price movements
        return buying_power >= (required_capital * 1.1)
    
    def _check_stop_loss_required(self, signal: Dict[str, Any]) -> bool:
        """Check if stop loss is properly set"""
        if signal.get('action') not in ['BUY', 'SELL']:
            return True  # No stop loss required for HOLD
        
        stop_loss = signal.get('stop_loss')
        return stop_loss is not None
    
    def _check_volatility_limit(self, signal: Dict[str, Any]) -> bool:
        """Check if the stock's volatility is within acceptable limits"""
        # For now, accept all volatility levels
        # Could be enhanced with real volatility data
        return True
    
    def calculate_position_risk(self, signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Calculate risk metrics for a position"""
        stop_loss = signal.get('stop_loss')
        position_size = signal.get('position_size', 0)
        
        if not stop_loss or not current_price:
            return {}
        
        # Calculate risk per share
        risk_per_share = abs(current_price - stop_loss)
        
        # Calculate total risk amount
        portfolio_value = 100000  # Default if not available
        position_value = position_size * portfolio_value
        shares = position_value / current_price if current_price > 0 else 0
        total_risk = risk_per_share * shares
        
        # Calculate risk as percentage of portfolio
        risk_percentage = (total_risk / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        # Calculate reward to risk ratio
        target_price = signal.get('target_price')
        reward_per_share = abs(target_price - current_price) if target_price else 0
        risk_reward_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
        
        return {
            'risk_per_share': round(risk_per_share, 2),
            'total_risk_amount': round(total_risk, 2),
            'risk_percentage': round(risk_percentage, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'position_value': round(position_value, 2),
            'estimated_shares': int(shares)
        }
    
    def update_position(self, symbol: str, position_data: Dict[str, Any]):
        """Update position tracking"""
        self.current_positions[symbol] = position_data
    
    def remove_position(self, symbol: str):
        """Remove position from tracking"""
        if symbol in self.current_positions:
            del self.current_positions[symbol]
    
    def calculate_portfolio_risk(self) -> Dict[str, Any]:
        """Calculate overall portfolio risk metrics"""
        if not self.current_positions:
            return {
                'total_positions': 0,
                'total_risk': 0.0,
                'concentration_risk': 0.0,
                'max_single_position': 0.0,
                'risk_score': 0.0
            }
        
        # Calculate total risk
        total_risk = sum(pos.get('risk_percentage', 0) for pos in self.current_positions.values())
        
        # Calculate concentration risk
        position_sizes = [pos.get('allocation', 0) for pos in self.current_positions.values()]
        max_position = max(position_sizes) if position_sizes else 0
        
        # Concentration risk using Herfindahl index
        herfindahl_index = sum(size ** 2 for size in position_sizes)
        concentration_risk = herfindahl_index * 100  # Convert to percentage
        
        # Overall risk score (0-100, higher = riskier)
        risk_factors = [
            min(100, total_risk * 2),  # Total risk factor
            min(100, concentration_risk),  # Concentration factor
            min(100, max_position * 200),  # Single position factor
            min(100, len(self.current_positions) * 5)  # Number of positions factor
        ]
        
        overall_risk_score = np.mean(risk_factors)
        
        return {
            'total_positions': len(self.current_positions),
            'total_risk_percentage': round(total_risk, 2),
            'concentration_risk': round(concentration_risk, 2),
            'max_single_position': round(max_position * 100, 2),
            'risk_score': round(overall_risk_score, 1),
            'risk_level': self._get_risk_level(overall_risk_score)
        }
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level description"""
        if risk_score <= 20:
            return 'LOW'
        elif risk_score <= 40:
            return 'MODERATE'
        elif risk_score <= 60:
            return 'HIGH'
        elif risk_score <= 80:
            return 'VERY HIGH'
        else:
            return 'EXTREME'
    
    def should_reduce_position_size(self, signal: Dict[str, Any]) -> Tuple[bool, float]:
        """Check if position size should be reduced for risk management"""
        portfolio_risk = self.calculate_portfolio_risk()
        current_risk_score = portfolio_risk.get('risk_score', 0)
        
        # If risk is already high, reduce position sizes
        if current_risk_score > 60:
            reduction_factor = 0.5  # Reduce by 50%
            return True, reduction_factor
        elif current_risk_score > 40:
            reduction_factor = 0.75  # Reduce by 25%
            return True, reduction_factor
        
        return False, 1.0
    
    def get_emergency_stop_recommendation(self) -> Dict[str, Any]:
        """Get recommendation for emergency stop of trading"""
        portfolio_risk = self.calculate_portfolio_risk()
        
        emergency_conditions = []
        should_stop = False
        
        # Check various emergency conditions
        if portfolio_risk.get('risk_score', 0) > 80:
            emergency_conditions.append("Portfolio risk score exceeds 80")
            should_stop = True
        
        if self.daily_pnl < -0.05:  # More than 5% daily loss
            emergency_conditions.append("Daily loss exceeds 5%")
            should_stop = True
        
        if portfolio_risk.get('total_risk_percentage', 0) > 30:
            emergency_conditions.append("Total portfolio risk exceeds 30%")
            should_stop = True
        
        if portfolio_risk.get('max_single_position', 0) > 15:
            emergency_conditions.append("Single position exceeds 15% of portfolio")
            should_stop = True
        
        return {
            'should_stop_trading': should_stop,
            'emergency_conditions': emergency_conditions,
            'recommendation': 'STOP_TRADING' if should_stop else 'CONTINUE',
            'risk_score': portfolio_risk.get('risk_score', 0)
        }
    
    def validate_signal_risk_reward(self, signal: Dict[str, Any]) -> bool:
        """Validate that signal has acceptable risk/reward ratio"""
        risk_metrics = self.calculate_position_risk(signal, signal.get('current_price', 0))
        risk_reward_ratio = risk_metrics.get('risk_reward_ratio', 0)
        
        # Require at least 1:1.5 risk/reward ratio
        return risk_reward_ratio >= 1.5
    
    def adjust_position_size_for_risk(self, signal: Dict[str, Any], 
                                    account_info: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust position size based on risk management rules"""
        adjusted_signal = signal.copy()
        
        # Check if we need to reduce position size
        should_reduce, reduction_factor = self.should_reduce_position_size(signal)
        
        if should_reduce:
            original_size = adjusted_signal.get('position_size', 0)
            new_size = original_size * reduction_factor
            adjusted_signal['position_size'] = new_size
            
            if 'reasoning' not in adjusted_signal:
                adjusted_signal['reasoning'] = []
            
            adjusted_signal['reasoning'].append(
                f"Position size reduced from {original_size:.3f} to {new_size:.3f} "
                f"due to portfolio risk (factor: {reduction_factor})"
            )
        
        # Ensure position size doesn't exceed maximum
        max_size = config.MAX_POSITION_SIZE
        if adjusted_signal.get('position_size', 0) > max_size:
            adjusted_signal['position_size'] = max_size
            
            if 'reasoning' not in adjusted_signal:
                adjusted_signal['reasoning'] = []
            
            adjusted_signal['reasoning'].append(
                f"Position size capped at maximum: {max_size}"
            )
        
        return adjusted_signal
    
    def reset_daily_counters(self):
        """Reset daily trading counters"""
        self.daily_trades = 0
        self.daily_pnl = 0.0
    
    def record_trade(self, trade_result: Dict[str, Any]):
        """Record a completed trade"""
        self.daily_trades += 1
        
        # Update P&L if available
        pnl = trade_result.get('realized_pnl', 0)
        self.daily_pnl += pnl
        
        # Update position tracking
        symbol = trade_result.get('symbol')
        if symbol:
            if trade_result.get('action') == 'BUY':
                self.update_position(symbol, {
                    'allocation': trade_result.get('position_size', 0),
                    'entry_price': trade_result.get('price', 0),
                    'quantity': trade_result.get('quantity', 0),
                    'entry_date': datetime.now()
                })
            elif trade_result.get('action') == 'SELL':
                self.remove_position(symbol)
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        portfolio_risk = self.calculate_portfolio_risk()
        emergency_stop = self.get_emergency_stop_recommendation()
        
        return {
            'daily_trades': self.daily_trades,
            'max_daily_trades': config.MAX_DAILY_TRADES,
            'daily_pnl': round(self.daily_pnl, 3),
            'portfolio_risk': portfolio_risk,
            'emergency_stop': emergency_stop,
            'active_positions': len(self.current_positions),
            'trading_allowed': not emergency_stop['should_stop_trading']
        }