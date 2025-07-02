import requests
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger
from config import config
import re

class BaseScraper(ABC):
    """Base class for all news scrapers"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.driver = None
        
    def setup_driver(self):
        """Setup Selenium WebDriver"""
        if self.driver is None:
            chrome_options = Options()
            if config.HEADLESS_BROWSER:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            try:
                self.driver = webdriver.Chrome(
                    ChromeDriverManager().install(),
                    options=chrome_options
                )
                self.driver.set_page_load_timeout(config.BROWSER_TIMEOUT)
            except Exception as e:
                logger.error(f"Failed to setup WebDriver: {e}")
                raise
    
    def close_driver(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def get_soup(self, url: str, use_selenium: bool = False) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from URL"""
        try:
            if use_selenium:
                if not self.driver:
                    self.setup_driver()
                self.driver.get(url)
                time.sleep(2)  # Wait for page to load
                html = self.driver.page_source
            else:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                html = response.text
            
            return BeautifulSoup(html, 'html.parser')
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_text(self, element) -> str:
        """Safely extract text from BeautifulSoup element"""
        return element.get_text(strip=True) if element else ""
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common unwanted characters
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '--')  # Em dash
        text = text.replace('\u201c', '"')  # Left double quotation mark
        text = text.replace('\u201d', '"')  # Right double quotation mark
        
        return text.strip()
    
    def extract_date(self, date_str: str) -> Optional[datetime]:
        """Extract datetime from string"""
        if not date_str:
            return None
            
        # Common date formats
        date_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return datetime.now()
    
    def rate_limit(self, delay: float = 1.0):
        """Add delay between requests"""
        time.sleep(delay)
    
    @abstractmethod
    def scrape_articles(self) -> List[Dict[str, Any]]:
        """Scrape articles from the news source"""
        pass
    
    @abstractmethod
    def extract_article_details(self, article_url: str) -> Dict[str, Any]:
        """Extract detailed information from a single article"""
        pass
    
    def validate_article(self, article: Dict[str, Any]) -> bool:
        """Validate that article has required fields"""
        required_fields = ['title', 'url', 'published_date']
        return all(field in article and article[field] for field in required_fields)
    
    def is_biotech_relevant(self, title: str, content: str = "") -> bool:
        """Check if article is biotech relevant based on keywords"""
        text = f"{title} {content}".lower()
        
        return any(keyword.lower() in text for keyword in config.BIOTECH_KEYWORDS)
    
    def scrape_with_retry(self, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Scrape articles with retry logic"""
        for attempt in range(max_retries):
            try:
                articles = self.scrape_articles()
                logger.info(f"Successfully scraped {len(articles)} articles from {self.source_name}")
                return articles
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {self.source_name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All retry attempts failed for {self.source_name}")
                    return []
        
        return []
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_driver()

    def parse_article_timestamp(self, timestamp_text: str, base_url: str = "") -> Optional[datetime]:
        """Smart timestamp parsing with multiple format support"""
        if not timestamp_text:
            return datetime.now()
        
        # Clean the timestamp text
        timestamp_text = timestamp_text.strip().lower()
        current_time = datetime.now()
        
        # Handle relative time expressions
        relative_patterns = [
            (r'(\d+)\s*minutes?\s*ago', lambda m: current_time - timedelta(minutes=int(m.group(1)))),
            (r'(\d+)\s*hours?\s*ago', lambda m: current_time - timedelta(hours=int(m.group(1)))),
            (r'(\d+)\s*days?\s*ago', lambda m: current_time - timedelta(days=int(m.group(1)))),
            (r'just\s*now', lambda m: current_time),
            (r'(\d+)m\s*ago', lambda m: current_time - timedelta(minutes=int(m.group(1)))),
            (r'(\d+)h\s*ago', lambda m: current_time - timedelta(hours=int(m.group(1)))),
        ]
        
        for pattern, calculator in relative_patterns:
            match = re.search(pattern, timestamp_text)
            if match:
                return calculator(match)
        
        # Handle absolute timestamps with various formats
        absolute_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
            "%B %d, %Y %H:%M:%S",
            "%B %d, %Y %H:%M",
            "%B %d, %Y",
            "%b %d, %Y %H:%M:%S",
            "%b %d, %Y %H:%M",
            "%b %d, %Y",
            "%d %B %Y %H:%M:%S",
            "%d %B %Y %H:%M",
            "%d %B %Y",
            "%d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M",
            "%d %b %Y",
        ]
        
        # Try parsing with different formats
        for fmt in absolute_formats:
            try:
                return datetime.strptime(timestamp_text, fmt)
            except:
                continue
        
        # Try extracting date parts with regex
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2}):(\d{2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, timestamp_text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 6:  # Full datetime
                        year, month, day, hour, minute, second = map(int, groups)
                        return datetime(year, month, day, hour, minute, second)
                    elif len(groups) == 5:  # Date + hour:minute
                        year, month, day, hour, minute = map(int, groups)
                        return datetime(year, month, day, hour, minute, 0)
                    elif len(groups) == 3:  # Date only
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                            year, month, day = map(int, groups)
                        else:  # MM/DD/YYYY or DD/MM/YYYY
                            month, day, year = map(int, groups)
                        return datetime(year, month, day, 12, 0, 0)  # Default to noon
                except:
                    continue
        
        # If all else fails, return current time
        logger.warning(f"Could not parse timestamp: {timestamp_text}")
        return current_time

    def is_article_within_time_window(self, article_time: datetime, buffer_minutes: int = 5) -> bool:
        """Check if article is within acceptable time window for current scraping cycle"""
        if not config.ENABLE_SMART_TIME_FILTERING:
            return True
        
        current_time = datetime.now()
        time_diff_minutes = abs((current_time - article_time).total_seconds() / 60)
        
        # Article is acceptable if it's within our lookback window
        max_age_minutes = config.ARTICLE_LOOKBACK_WINDOW_MINUTES
        
        return time_diff_minutes <= max_age_minutes

    def extract_article_metadata(self, soup, url: str) -> Dict[str, Any]:
        """Enhanced metadata extraction with smart timestamp handling"""
        metadata = {}
        
        # Try to find publication time with multiple selectors
        time_selectors = [
            'time[datetime]',
            'span.timestamp',
            'div.date',
            'span.date',
            'div.publish-date',
            'span.publish-date',
            'div.publication-date',
            'meta[property="article:published_time"]',
            'meta[name="publish-date"]',
            '.article-date',
            '.post-date',
            '.entry-date'
        ]
        
        published_date = None
        for selector in time_selectors:
            try:
                time_element = soup.select_one(selector)
                if time_element:
                    # Try different attributes
                    time_text = (
                        time_element.get('datetime') or
                        time_element.get('content') or
                        time_element.get_text(strip=True)
                    )
                    
                    if time_text:
                        parsed_time = self.parse_article_timestamp(time_text, url)
                        if parsed_time and self.is_article_within_time_window(parsed_time):
                            published_date = parsed_time
                            break
            except Exception as e:
                continue
        
        if not published_date:
            published_date = datetime.now()
        
        metadata['published_date'] = published_date
        metadata['is_recent'] = self.is_article_within_time_window(published_date)
        
        return metadata