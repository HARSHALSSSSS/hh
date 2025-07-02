import re
import numpy as np
from typing import Dict, Any, List, Tuple
from textblob import TextBlob
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from loguru import logger
from config import config

class SentimentAnalyzer:
    """Advanced sentiment analysis for biotech news articles"""
    
    def __init__(self):
        self.use_transformer = False
        self.transformer_pipeline = None
        self.biotech_keywords = config.BIOTECH_KEYWORDS
        
        # Try to load a more sophisticated model
        self._setup_transformer_model()
        
        # Biotech-specific sentiment modifiers
        self.positive_indicators = [
            'approval', 'approved', 'breakthrough', 'successful', 'positive results',
            'meets endpoint', 'exceeded expectations', 'significant improvement',
            'promising', 'efficacy', 'safe', 'well-tolerated', 'fast track',
            'orphan drug', 'priority review', 'accelerated approval', 'granted',
            'cleared', 'authorized', 'milestone', 'achievement', 'advance',
            'progress', 'partnership', 'collaboration', 'investment', 'funding'
        ]
        
        self.negative_indicators = [
            'rejected', 'denied', 'failed', 'discontinued', 'terminated',
            'adverse events', 'side effects', 'safety concerns', 'missed endpoint',
            'disappointing', 'delayed', 'suspended', 'halted', 'concerns',
            'warning', 'recall', 'investigation', 'lawsuit', 'decline',
            'loss', 'bankruptcy', 'restructuring', 'downsizing'
        ]
        
        # Clinical trial specific sentiment
        self.trial_positive = [
            'met primary endpoint', 'statistically significant', 'dose-dependent',
            'favorable safety profile', 'complete response', 'partial response',
            'stable disease', 'progression-free survival', 'overall survival',
            'biomarker improvement', 'quality of life improvement'
        ]
        
        self.trial_negative = [
            'failed to meet endpoint', 'no statistical significance', 'futility',
            'dose-limiting toxicity', 'progressive disease', 'serious adverse events',
            'black box warning', 'contraindication', 'resistance', 'relapse'
        ]
    
    def _setup_transformer_model(self):
        """Setup transformer-based sentiment model if available"""
        try:
            # Try to use a financial/biotech specific sentiment model
            model_names = [
                "ProsusAI/finbert",  # Financial sentiment
                "nlptown/bert-base-multilingual-uncased-sentiment",
                "cardiffnlp/twitter-roberta-base-sentiment-latest"
            ]
            
            for model_name in model_names:
                try:
                    self.transformer_pipeline = pipeline(
                        "sentiment-analysis",
                        model=model_name,
                        tokenizer=model_name,
                        device=0 if torch.cuda.is_available() else -1
                    )
                    self.use_transformer = True
                    logger.info(f"Loaded transformer model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load {model_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Failed to setup transformer model: {e}")
            logger.info("Falling back to TextBlob sentiment analysis")
    
    def analyze_sentiment(self, text: str, title: str = "") -> Dict[str, Any]:
        """Analyze sentiment of biotech news article"""
        if not text:
            return {
                'sentiment_score': 0.0,
                'sentiment_label': 'neutral',
                'confidence': 0.0,
                'method': 'none'
            }
        
        # Combine title and text, giving more weight to title
        combined_text = f"{title} {title} {text}"  # Title appears twice for emphasis
        
        # Get base sentiment
        base_sentiment = self._get_base_sentiment(combined_text)
        
        # Apply biotech-specific modifiers
        biotech_sentiment = self._apply_biotech_modifiers(combined_text, base_sentiment)
        
        # Apply clinical trial specific modifiers
        final_sentiment = self._apply_clinical_modifiers(combined_text, biotech_sentiment)
        
        # Apply P-value and statistical significance modifiers
        final_sentiment = self._apply_statistical_modifiers(combined_text, final_sentiment)
        
        # Normalize and classify
        return self._normalize_sentiment(final_sentiment, combined_text)
    
    def _get_base_sentiment(self, text: str) -> Dict[str, Any]:
        """Get base sentiment using available models"""
        if self.use_transformer and self.transformer_pipeline:
            return self._get_transformer_sentiment(text)
        else:
            return self._get_textblob_sentiment(text)
    
    def _get_transformer_sentiment(self, text: str) -> Dict[str, Any]:
        """Get sentiment using transformer model"""
        try:
            # Truncate text to model's max length
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            result = self.transformer_pipeline(text)[0]
            
            # Convert to standardized format
            label = result['label'].lower()
            score = result['score']
            
            # Map different model outputs to standard format
            if 'positive' in label or 'pos' in label:
                sentiment_score = score
            elif 'negative' in label or 'neg' in label:
                sentiment_score = -score
            else:  # neutral
                sentiment_score = 0.0
            
            return {
                'score': sentiment_score,
                'confidence': score,
                'method': 'transformer'
            }
            
        except Exception as e:
            logger.error(f"Transformer sentiment analysis failed: {e}")
            return self._get_textblob_sentiment(text)
    
    def _get_textblob_sentiment(self, text: str) -> Dict[str, Any]:
        """Get sentiment using TextBlob"""
        try:
            blob = TextBlob(text)
            sentiment_score = blob.sentiment.polarity  # -1 to 1
            confidence = abs(sentiment_score)
            
            return {
                'score': sentiment_score,
                'confidence': confidence,
                'method': 'textblob'
            }
            
        except Exception as e:
            logger.error(f"TextBlob sentiment analysis failed: {e}")
            return {
                'score': 0.0,
                'confidence': 0.0,
                'method': 'error'
            }
    
    def _apply_biotech_modifiers(self, text: str, base_sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Apply biotech-specific sentiment modifiers"""
        text_lower = text.lower()
        score = base_sentiment['score']
        confidence = base_sentiment['confidence']
        
        # Count positive and negative indicators
        positive_count = sum(1 for indicator in self.positive_indicators if indicator in text_lower)
        negative_count = sum(1 for indicator in self.negative_indicators if indicator in text_lower)
        
        # Apply modifiers
        if positive_count > negative_count:
            modifier = min(0.3, positive_count * 0.1)
            score += modifier
            confidence = min(1.0, confidence + 0.1)
        elif negative_count > positive_count:
            modifier = min(0.3, negative_count * 0.1)
            score -= modifier
            confidence = min(1.0, confidence + 0.1)
        
        # Special cases for strong indicators
        if any(strong in text_lower for strong in ['fda approval', 'breakthrough therapy', 'fast track']):
            score += 0.4
            confidence = min(1.0, confidence + 0.2)
        
        if any(strong in text_lower for strong in ['failed to meet', 'discontinued', 'terminated']):
            score -= 0.4
            confidence = min(1.0, confidence + 0.2)
        
        return {
            'score': score,
            'confidence': confidence,
            'method': base_sentiment['method']
        }
    
    def _apply_clinical_modifiers(self, text: str, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Apply clinical trial specific sentiment modifiers"""
        text_lower = text.lower()
        score = sentiment['score']
        confidence = sentiment['confidence']
        
        # Check for clinical trial positive indicators
        trial_pos_count = sum(1 for indicator in self.trial_positive if indicator in text_lower)
        trial_neg_count = sum(1 for indicator in self.trial_negative if indicator in text_lower)
        
        if trial_pos_count > 0:
            score += min(0.25, trial_pos_count * 0.15)
            confidence = min(1.0, confidence + 0.1)
        
        if trial_neg_count > 0:
            score -= min(0.25, trial_neg_count * 0.15)
            confidence = min(1.0, confidence + 0.1)
        
        return {
            'score': score,
            'confidence': confidence,
            'method': sentiment['method']
        }
    
    def _apply_statistical_modifiers(self, text: str, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Apply statistical significance modifiers based on P-values"""
        text_lower = text.lower()
        score = sentiment['score']
        confidence = sentiment['confidence']
        
        # Look for P-values
        p_value_patterns = [
            r'p\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)',
            r'p-value\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in p_value_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                try:
                    p_value = float(f"0.{match}" if not match.startswith('0') else match)
                    if 0 <= p_value <= 1:
                        if p_value < config.P_VALUE_THRESHOLD_HIGHLY_SIGNIFICANT:
                            score += 0.2  # Highly significant
                            confidence = min(1.0, confidence + 0.15)
                        elif p_value < config.P_VALUE_THRESHOLD_SIGNIFICANT:
                            score += 0.1  # Significant
                            confidence = min(1.0, confidence + 0.1)
                        else:
                            score -= 0.1  # Not significant
                        break
                except ValueError:
                    continue
        
        # Check for statistical significance mentions
        if 'statistically significant' in text_lower:
            score += 0.15
            confidence = min(1.0, confidence + 0.1)
        elif 'not statistically significant' in text_lower or 'no statistical significance' in text_lower:
            score -= 0.15
        
        return {
            'score': score,
            'confidence': confidence,
            'method': sentiment['method']
        }
    
    def _normalize_sentiment(self, sentiment: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Normalize sentiment score and assign label"""
        score = max(-1.0, min(1.0, sentiment['score']))  # Clamp to [-1, 1]
        confidence = min(1.0, sentiment['confidence'])
        
        # Assign label based on thresholds
        if score >= config.SENTIMENT_THRESHOLD_POSITIVE:
            label = 'positive'
        elif score <= config.SENTIMENT_THRESHOLD_NEGATIVE:
            label = 'negative'
        else:
            label = 'neutral'
        
        # Adjust confidence based on text length and biotech relevance
        text_length_factor = min(1.0, len(text) / 1000)  # Longer text = higher confidence
        biotech_relevance = self._calculate_biotech_relevance(text)
        
        final_confidence = confidence * text_length_factor * biotech_relevance
        
        return {
            'sentiment_score': round(score, 3),
            'sentiment_label': label,
            'confidence': round(final_confidence, 3),
            'method': sentiment['method'],
            'biotech_relevance': round(biotech_relevance, 3)
        }
    
    def _calculate_biotech_relevance(self, text: str) -> float:
        """Calculate how relevant the text is to biotech"""
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in self.biotech_keywords if keyword.lower() in text_lower)
        
        # Normalize by text length and keyword list length
        relevance = min(1.0, keyword_count / 5)  # 5 keywords = 100% relevance
        
        return max(0.1, relevance)  # Minimum 10% relevance
    
    def analyze_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for a batch of articles"""
        results = []
        
        for article in articles:
            try:
                title = article.get('title', '')
                text = article.get('full_text', '') or article.get('summary', '')
                
                sentiment = self.analyze_sentiment(text, title)
                
                result = {
                    'article_id': article.get('id'),
                    'url': article.get('url'),
                    **sentiment
                }
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error analyzing sentiment for article {article.get('url', 'unknown')}: {e}")
                results.append({
                    'article_id': article.get('id'),
                    'url': article.get('url'),
                    'sentiment_score': 0.0,
                    'sentiment_label': 'neutral',
                    'confidence': 0.0,
                    'method': 'error'
                })
        
        return results
    
    def get_sentiment_summary(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for sentiment analysis results"""
        if not articles:
            return {}
        
        sentiments = [a.get('sentiment_score', 0) for a in articles if 'sentiment_score' in a]
        labels = [a.get('sentiment_label', 'neutral') for a in articles if 'sentiment_label' in a]
        
        if not sentiments:
            return {}
        
        summary = {
            'total_articles': len(articles),
            'avg_sentiment': round(np.mean(sentiments), 3),
            'sentiment_std': round(np.std(sentiments), 3),
            'positive_count': labels.count('positive'),
            'negative_count': labels.count('negative'),
            'neutral_count': labels.count('neutral'),
            'most_positive': max(sentiments),
            'most_negative': min(sentiments)
        }
        
        # Calculate percentages
        total = len(labels)
        if total > 0:
            summary.update({
                'positive_percentage': round(summary['positive_count'] / total * 100, 1),
                'negative_percentage': round(summary['negative_count'] / total * 100, 1),
                'neutral_percentage': round(summary['neutral_count'] / total * 100, 1)
            })
        
        return summary