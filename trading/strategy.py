from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from loguru import logger
from config import config

class TradingStrategy:
    """Biotech news-based trading strategy"""
    
    def __init__(self):
        self.positions = {}  # Track our positions
        self.signals = []  # Track trading signals
        
    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single article and generate trading signal"""
        signal = {
            'article_id': article.get('id'),
            'timestamp': datetime.now(),
            'symbol': article.get('company_ticker'),
            'company_name': article.get('company_name'),
            'action': 'HOLD',  # BUY, SELL, HOLD
            'confidence': 0.0,
            'reasoning': [],
            'target_price': None,
            'stop_loss': None,
            'position_size': 0.0
        }
        
        if not signal['symbol']:
            signal['reasoning'].append("No ticker symbol found")
            return signal
        
        # Analyze various factors
        sentiment_score = self._analyze_sentiment(article, signal)
        clinical_score = self._analyze_clinical_data(article, signal)
        regulatory_score = self._analyze_regulatory_status(article, signal)
        financial_score = self._analyze_financial_metrics(article, signal)
        
        # Combine scores with weights
        weights = {
            'sentiment': 0.25,
            'clinical': 0.35,
            'regulatory': 0.30,
            'financial': 0.10
        }
        
        total_score = (
            sentiment_score * weights['sentiment'] +
            clinical_score * weights['clinical'] +
            regulatory_score * weights['regulatory'] +
            financial_score * weights['financial']
        )
        
        # Generate final signal based on total score
        signal = self._generate_signal(total_score, signal, article)
        
        return signal
    
    def _analyze_sentiment(self, article: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Analyze sentiment factors"""
        score = 0.0
        
        sentiment_score = article.get('sentiment_score', 0)
        sentiment_label = article.get('sentiment_label', 'neutral')
        confidence = article.get('confidence', 0)
        
        # Base sentiment contribution
        if sentiment_label == 'positive' and sentiment_score > config.SENTIMENT_THRESHOLD_POSITIVE:
            score += 0.6 * confidence
            signal['reasoning'].append(f"Positive sentiment: {sentiment_score:.3f}")
        elif sentiment_label == 'negative' and sentiment_score < config.SENTIMENT_THRESHOLD_NEGATIVE:
            score -= 0.6 * confidence
            signal['reasoning'].append(f"Negative sentiment: {sentiment_score:.3f}")
        
        # Biotech relevance factor
        biotech_relevance = article.get('biotech_relevance', 0)
        if biotech_relevance > 0.7:
            score *= 1.2  # Boost score for highly relevant biotech news
            signal['reasoning'].append(f"High biotech relevance: {biotech_relevance:.3f}")
        
        return max(-1.0, min(1.0, score))
    
    def _analyze_clinical_data(self, article: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Analyze clinical trial data"""
        score = 0.0
        
        # P-value analysis
        p_value = article.get('p_value')
        if p_value is not None:
            if p_value < config.P_VALUE_THRESHOLD_HIGHLY_SIGNIFICANT:
                score += 0.8
                signal['reasoning'].append(f"Highly significant p-value: {p_value}")
            elif p_value < config.P_VALUE_THRESHOLD_SIGNIFICANT:
                score += 0.5
                signal['reasoning'].append(f"Significant p-value: {p_value}")
            else:
                score -= 0.3
                signal['reasoning'].append(f"Non-significant p-value: {p_value}")
        
        # Trial phase analysis
        trial_phase = article.get('trial_phase')
        if trial_phase:
            phase_scores = {
                'phase_1': 0.1,  # Early stage, lower weight
                'phase_2': 0.3,  # Promising, moderate weight
                'phase_3': 0.5   # Late stage, higher weight
            }
            phase_score = phase_scores.get(trial_phase, 0)
            score += phase_score
            signal['reasoning'].append(f"Trial phase {trial_phase}: +{phase_score}")
        
        # Patient count (enrollment size can indicate trial importance)
        patient_count = article.get('patient_count')
        if patient_count:
            if patient_count >= 1000:
                score += 0.2
                signal['reasoning'].append(f"Large trial size: {patient_count} patients")
            elif patient_count >= 300:
                score += 0.1
                signal['reasoning'].append(f"Medium trial size: {patient_count} patients")
        
        # Clinical endpoints
        if article.get('primary_endpoint'):
            score += 0.1
            signal['reasoning'].append("Primary endpoint data available")
        
        return max(-1.0, min(1.0, score))
    
    def _analyze_regulatory_status(self, article: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Analyze regulatory approval status"""
        score = 0.0
        
        approval_status = article.get('approval_status')
        if approval_status:
            status_scores = {
                'approved': 0.9,      # Strong positive
                'breakthrough': 0.7,   # Very positive
                'pending': 0.2,       # Mild positive
                'rejected': -0.8      # Strong negative
            }
            
            status_score = status_scores.get(approval_status, 0)
            score += status_score
            signal['reasoning'].append(f"Regulatory status '{approval_status}': {status_score:+.1f}")
        
        # Regulatory designations
        designations = article.get('regulatory_designations', [])
        for designation in designations:
            if 'breakthrough' in designation.lower():
                score += 0.3
                signal['reasoning'].append(f"Breakthrough therapy designation")
            elif 'fast track' in designation.lower():
                score += 0.2
                signal['reasoning'].append(f"Fast track designation")
            elif 'orphan drug' in designation.lower():
                score += 0.2
                signal['reasoning'].append(f"Orphan drug designation")
        
        # Indication importance (rare diseases often have premium pricing)
        indication = article.get('indication', '').lower()
        if indication:
            rare_diseases = ['rare', 'orphan', 'ultra-rare', 'pediatric']
            if any(term in indication for term in rare_diseases):
                score += 0.1
                signal['reasoning'].append(f"Rare disease indication: {indication}")
        
        return max(-1.0, min(1.0, score))
    
    def _analyze_financial_metrics(self, article: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Analyze financial and market metrics"""
        score = 0.0
        
        # Market cap analysis
        market_cap = article.get('market_cap')
        if market_cap:
            if market_cap < config.MIN_MARKET_CAP:
                score -= 0.3  # Too small, higher risk
                signal['reasoning'].append(f"Small market cap: ${market_cap/1e6:.1f}M")
            elif market_cap > 50e9:  # > $50B
                score -= 0.1  # Large cap, less volatile
                signal['reasoning'].append(f"Large market cap: ${market_cap/1e9:.1f}B")
            else:
                score += 0.1  # Mid cap, good balance
                signal['reasoning'].append(f"Mid market cap: ${market_cap/1e9:.1f}B")
        
        # Employee count (company size indicator)
        employee_count = article.get('employee_count')
        if employee_count:
            if employee_count < config.MIN_EMPLOYEE_COUNT:
                score -= 0.1
                signal['reasoning'].append(f"Small team: {employee_count} employees")
            elif employee_count > 10000:
                score += 0.1
                signal['reasoning'].append(f"Large organization: {employee_count} employees")
        
        # Funding information
        funding_amount = article.get('funding_amount')
        if funding_amount and funding_amount > 100e6:  # > $100M
            score += 0.2
            signal['reasoning'].append(f"Large funding: ${funding_amount/1e6:.1f}M")
        
        # Stock price volatility (beta)
        beta = article.get('beta')
        if beta:
            if beta > 2.0:
                score -= 0.1  # Very volatile
                signal['reasoning'].append(f"High volatility (beta: {beta:.2f})")
            elif beta < 0.5:
                score -= 0.05  # Low volatility (less responsive)
                signal['reasoning'].append(f"Low volatility (beta: {beta:.2f})")
        
        return max(-1.0, min(1.0, score))
    
    def _generate_signal(self, total_score: float, signal: Dict[str, Any], 
                        article: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final trading signal based on total score"""
        
        # Determine action based on score thresholds
        if total_score >= 0.6:
            signal['action'] = 'BUY'
            signal['confidence'] = min(0.95, total_score)
        elif total_score <= -0.6:
            signal['action'] = 'SELL'
            signal['confidence'] = min(0.95, abs(total_score))
        else:
            signal['action'] = 'HOLD'
            signal['confidence'] = 1.0 - abs(total_score)
        
        # Calculate position sizing based on confidence and risk
        signal['position_size'] = self._calculate_position_size(
            signal['confidence'], article
        )
        
        # Set stop loss and target prices
        current_price = article.get('current_price')
        if current_price and signal['action'] in ['BUY', 'SELL']:
            signal['stop_loss'], signal['target_price'] = self._calculate_price_targets(
                current_price, signal['action'], signal['confidence']
            )
        
        # Add overall score to reasoning
        signal['reasoning'].append(f"Total score: {total_score:.3f}")
        signal['total_score'] = total_score
        
        return signal
    
    def _calculate_position_size(self, confidence: float, article: Dict[str, Any]) -> float:
        """Calculate position size as percentage of portfolio"""
        base_size = config.MAX_POSITION_SIZE
        
        # Adjust based on confidence
        confidence_multiplier = confidence
        
        # Adjust based on market cap (smaller companies = smaller positions)
        market_cap = article.get('market_cap', 0)
        if market_cap > 0:
            if market_cap < 1e9:  # < $1B
                size_multiplier = 0.5
            elif market_cap < 10e9:  # < $10B
                size_multiplier = 0.8
            else:
                size_multiplier = 1.0
        else:
            size_multiplier = 0.3  # Unknown market cap = conservative
        
        # Adjust based on volatility
        beta = article.get('beta', 1.0)
        volatility_multiplier = max(0.3, min(1.0, 1.0 / beta)) if beta > 0 else 0.5
        
        final_size = base_size * confidence_multiplier * size_multiplier * volatility_multiplier
        
        return max(0.01, min(base_size, final_size))  # Between 1% and max position size
    
    def _calculate_price_targets(self, current_price: float, action: str, 
                               confidence: float) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and target prices"""
        if action == 'BUY':
            # Stop loss below current price
            stop_loss = current_price * (1 - config.STOP_LOSS_PERCENTAGE)
            # Target price above current price, scaled by confidence
            target_multiplier = 1 + (config.TAKE_PROFIT_PERCENTAGE * confidence)
            target_price = current_price * target_multiplier
            
        elif action == 'SELL':
            # Stop loss above current price (for short positions)
            stop_loss = current_price * (1 + config.STOP_LOSS_PERCENTAGE)
            # Target price below current price
            target_multiplier = 1 - (config.TAKE_PROFIT_PERCENTAGE * confidence)
            target_price = current_price * target_multiplier
            
        else:
            return None, None
        
        return round(stop_loss, 2), round(target_price, 2)
    
    def analyze_portfolio_risk(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall portfolio risk from multiple signals"""
        if not articles:
            return {}
        
        signals = [self.analyze_article(article) for article in articles]
        buy_signals = [s for s in signals if s['action'] == 'BUY']
        sell_signals = [s for s in signals if s['action'] == 'SELL']
        
        # Calculate portfolio metrics
        total_position_size = sum(s['position_size'] for s in buy_signals)
        avg_confidence = np.mean([s['confidence'] for s in signals if s['action'] != 'HOLD'])
        
        # Sector concentration risk
        symbols = [s['symbol'] for s in buy_signals if s['symbol']]
        unique_symbols = len(set(symbols))
        concentration_risk = 1.0 - (unique_symbols / max(1, len(symbols)))
        
        # Market cap diversification
        market_caps = [a.get('market_cap', 0) for a in articles if a.get('market_cap')]
        market_cap_std = np.std(market_caps) if market_caps else 0
        
        return {
            'total_buy_signals': len(buy_signals),
            'total_sell_signals': len(sell_signals),
            'total_position_size': round(total_position_size, 3),
            'avg_confidence': round(avg_confidence, 3) if avg_confidence == avg_confidence else 0,  # NaN check
            'concentration_risk': round(concentration_risk, 3),
            'market_cap_diversification': round(market_cap_std / 1e9, 2) if market_cap_std > 0 else 0,
            'risk_score': self._calculate_overall_risk_score(
                total_position_size, concentration_risk, len(buy_signals)
            )
        }
    
    def _calculate_overall_risk_score(self, total_position_size: float, 
                                    concentration_risk: float, signal_count: int) -> float:
        """Calculate overall risk score (0-1, higher = riskier)"""
        # Position size risk
        size_risk = min(1.0, total_position_size / 0.5)  # Risk increases as we approach 50% allocation
        
        # Concentration risk (already 0-1)
        
        # Signal count risk (too few or too many signals)
        if signal_count == 0:
            count_risk = 0
        elif signal_count <= 3:
            count_risk = 0.2
        elif signal_count <= 10:
            count_risk = 0.1
        else:
            count_risk = 0.3  # Too many signals might indicate overtrading
        
        # Combine risk factors
        overall_risk = (size_risk * 0.4 + concentration_risk * 0.4 + count_risk * 0.2)
        
        return round(min(1.0, overall_risk), 3)
    
    def filter_signals_by_risk(self, signals: List[Dict[str, Any]], 
                             max_portfolio_risk: float = 0.7) -> List[Dict[str, Any]]:
        """Filter signals to maintain portfolio risk below threshold"""
        if not signals:
            return []
        
        # Sort by confidence (highest first)
        sorted_signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)
        
        filtered_signals = []
        current_position_size = 0.0
        
        for signal in sorted_signals:
            if signal['action'] not in ['BUY', 'SELL']:
                continue
            
            new_position_size = current_position_size + signal['position_size']
            
            # Check if adding this signal would exceed risk limits
            if new_position_size <= max_portfolio_risk:
                filtered_signals.append(signal)
                current_position_size = new_position_size
            else:
                # Try to reduce position size to fit
                available_size = max_portfolio_risk - current_position_size
                if available_size > 0.01:  # At least 1% position
                    signal_copy = signal.copy()
                    signal_copy['position_size'] = available_size
                    signal_copy['reasoning'].append(
                        f"Position size reduced from {signal['position_size']:.3f} to {available_size:.3f} for risk management"
                    )
                    filtered_signals.append(signal_copy)
                    break  # Portfolio is now at max risk
        
        return filtered_signals
    
    def get_signal_summary(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of trading signals"""
        if not signals:
            return {}
        
        buy_signals = [s for s in signals if s['action'] == 'BUY']
        sell_signals = [s for s in signals if s['action'] == 'SELL']
        hold_signals = [s for s in signals if s['action'] == 'HOLD']
        
        summary = {
            'total_signals': len(signals),
            'buy_count': len(buy_signals),
            'sell_count': len(sell_signals),
            'hold_count': len(hold_signals),
            'avg_buy_confidence': round(np.mean([s['confidence'] for s in buy_signals]), 3) if buy_signals else 0,
            'avg_sell_confidence': round(np.mean([s['confidence'] for s in sell_signals]), 3) if sell_signals else 0,
            'total_buy_position_size': round(sum(s['position_size'] for s in buy_signals), 3),
            'symbols': list(set(s['symbol'] for s in signals if s['symbol'])),
            'highest_confidence_signal': max(signals, key=lambda x: x['confidence']) if signals else None
        }
        
        return summary