import requests
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger
from config import config

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