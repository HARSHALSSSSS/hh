import os
from typing import List, Dict, Any
from pydantic import BaseSettings, validator
from datetime import time

class Config(BaseSettings):
    """Configuration settings for the biotech trading system"""
    
    # Database settings
    DATABASE_URL: str = "sqlite:///biotech_trader.db"
    
    # Scraping settings - RESTORED TO 15 MINUTES WITH SMART TIME WINDOW
    SCRAPE_INTERVAL_MINUTES: int = 15  # Back to 15 minutes as requested
    SCRAPE_START_TIME: time = time(7, 0)  # 7:00 AM
    SCRAPE_END_TIME: time = time(16, 0)   # 4:00 PM
    
    # SMART ARTICLE TIME WINDOW SYSTEM
    ARTICLE_TIME_BUFFER_MINUTES: int = 5  # Look for articles released 5 min before/after our scraping
    ARTICLE_LOOKBACK_WINDOW_MINUTES: int = 20  # Total window: last 20 minutes (15 + 5 buffer)
    ENABLE_SMART_TIME_FILTERING: bool = True  # Enable intelligent time-based article filtering
    
    # Enhanced timing settings for article detection
    SCRAPE_OFFSET_SECONDS: int = 30  # Small random offset (30 seconds max) to avoid exact timing conflicts
    RAPID_SCRAPE_ENABLED: bool = False  # Disabled as requested - keeping 15 min interval
    RAPID_SCRAPE_INTERVALS: List[time] = []  # Empty - no rapid scraping
    
    # Article freshness and relevance settings  
    MAX_ARTICLE_AGE_HOURS: int = 2  # Only process articles published within last 2 hours
    DUPLICATE_CHECK_HOURS: int = 24  # Check for duplicates within 24 hours
    ARTICLE_RELEVANCE_SCORE_THRESHOLD: float = 0.7  # Only process highly relevant biotech articles
    
    # News sources
    NEWS_SOURCES: Dict[str, Dict[str, Any]] = {
        "stocktitan": {
            "base_url": "https://www.stocktitan.net",
            "biotech_url": "https://www.stocktitan.net/news/",
            "clinical_trials_url": "https://www.stocktitan.net/news/",
            "enabled": True
        },
        "prnewswire": {
            "base_url": "https://www.prnewswire.com",
            "biotech_url": "https://www.prnewswire.com/news-releases/biotechnology-latest-news/biotechnology-latest-news-list/",
            "rss_url": "https://www.prnewswire.com/rss/news-releases-biotechnology-latest-news-list.rss",
            "enabled": True
        },
        "businesswire": {
            "base_url": "https://www.businesswire.com",
            "biotech_url": "https://www.businesswire.com/news/home/technology-business-finance-news/pharmaceuticals-biotechnology",
            "enabled": True
        },
        "yahoo": {
            "base_url": "https://news.yahoo.com",
            "biotech_url": "https://news.yahoo.com/health/",
            "rss_url": "https://news.yahoo.com/rss/health",
            "enabled": True
        }
    }
    
    # Trading settings
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"  # Paper trading by default
    
    # Risk management
    MAX_POSITION_SIZE: float = 0.05  # 5% of portfolio per position
    STOP_LOSS_PERCENTAGE: float = 0.1  # 10% stop loss
    TAKE_PROFIT_PERCENTAGE: float = 0.2  # 20% take profit
    MAX_DAILY_TRADES: int = 10
    
    # Sentiment analysis settings
    SENTIMENT_THRESHOLD_POSITIVE: float = 0.1
    SENTIMENT_THRESHOLD_NEGATIVE: float = -0.1
    
    # P-value thresholds
    P_VALUE_THRESHOLD_SIGNIFICANT: float = 0.05
    P_VALUE_THRESHOLD_HIGHLY_SIGNIFICANT: float = 0.01
    
    # Company size filters
    MIN_MARKET_CAP: float = 100_000_000  # $100M minimum market cap
    MIN_EMPLOYEE_COUNT: int = 50
    
    # Biotech keywords for filtering
    BIOTECH_KEYWORDS: List[str] = [
        "biotech", "biotechnology", "pharmaceutical", "drug", "clinical trial",
        "FDA approval", "phase I", "phase II", "phase III", "pipeline",
        "oncology", "immunotherapy", "vaccine", "treatment", "therapy",
        "regulatory", "biologics", "gene therapy", "cell therapy",
        "personalized medicine", "precision medicine", "orphan drug",
        "rare disease", "breakthrough therapy", "fast track"
    ]
    
    # Email notifications
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    NOTIFICATION_EMAILS: List[str] = []
    
    # Email notification preferences
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    SEND_NEW_ARTICLES_ALERTS: bool = True
    SEND_HIGH_RELEVANCE_ALERTS: bool = True
    SEND_TRADING_SIGNAL_ALERTS: bool = True
    SEND_TRADE_EXECUTION_ALERTS: bool = True
    SEND_RISK_ALERTS: bool = True
    SEND_DAILY_HEALTH_REPORTS: bool = True
    
    # Email frequency controls
    MIN_ARTICLES_FOR_BATCH_EMAIL: int = 3  # Only send batch emails if >= 3 articles
    HIGH_RELEVANCE_THRESHOLD_FOR_EMAIL: float = 0.8  # Send immediate alerts for articles above this score
    MAX_EMAILS_PER_HOUR: int = 20  # Rate limiting for email alerts
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "biotech_trader.log"
    
    # Selenium settings
    HEADLESS_BROWSER: bool = True
    BROWSER_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator('ALPACA_API_KEY')
    def validate_alpaca_key(cls, v):
        if not v:
            print("Warning: ALPACA_API_KEY not set. Trading will be disabled.")
        return v

# Global configuration instance
config = Config()

# Trading hours (market hours)
TRADING_HOURS = {
    "start": time(9, 30),   # 9:30 AM EST
    "end": time(16, 0)      # 4:00 PM EST
}

# Approval status keywords
APPROVAL_KEYWORDS = {
    "approved": ["approved", "approval", "granted", "cleared"],
    "rejected": ["rejected", "denied", "failed", "discontinued"],
    "pending": ["pending", "under review", "submitted"],
    "breakthrough": ["breakthrough therapy", "fast track", "orphan drug"],
    "phase_1": ["phase 1", "phase I", "first-in-human"],
    "phase_2": ["phase 2", "phase II"],
    "phase_3": ["phase 3", "phase III", "pivotal trial"],
    "nda": ["NDA", "new drug application", "BLA", "biologics license application"]
}