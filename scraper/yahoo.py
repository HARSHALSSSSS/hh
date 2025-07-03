import re
import feedparser
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper
from config import config

class YahooScraper(BaseScraper):
    """Scraper for Yahoo News biotech and health section"""
    
    def __init__(self):
        super().__init__("yahoo")
        self.base_url = config.NEWS_SOURCES["yahoo"]["base_url"]
        self.biotech_url = config.NEWS_SOURCES["yahoo"]["biotech_url"]
        self.rss_url = config.NEWS_SOURCES["yahoo"]["rss_url"]
    
    def scrape_articles(self) -> List[Dict[str, Any]]:
        """Scrape articles from Yahoo News biotech section and RSS"""
        articles = []
        
        # First try RSS feed
        rss_articles = self._scrape_rss_feed()
        articles.extend(rss_articles)
        
        # Then scrape webpage for additional articles
        web_articles = self._scrape_webpage()
        articles.extend(web_articles)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in articles:
            if article.get('url') not in seen_urls:
                seen_urls.add(article.get('url'))
                unique_articles.append(article)
        
        return unique_articles
    
    def _scrape_rss_feed(self) -> List[Dict[str, Any]]:
        """Scrape articles from Yahoo RSS feed"""
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:30]:  # Limit to recent articles
                article = {
                    'source': self.source_name,
                    'title': self.clean_text(entry.get('title', '')),
                    'url': entry.get('link', ''),
                    'summary': self.clean_text(entry.get('summary', '')),
                    'published_date': self._parse_rss_date(entry.get('published', '')),
                }
                if self.validate_article(article):
                    articles.append(article)
        except Exception as e:
            logger.error(f"Error parsing Yahoo RSS feed: {e}")
        return articles
    
    def _scrape_webpage(self) -> List[Dict[str, Any]]:
        """Scrape articles from Yahoo biotech webpage"""
        articles = []
        soup = self.get_soup(self.biotech_url, use_selenium=True)
        if not soup:
            return articles
        article_selectors = [
            'div[data-test-locator="stream-item"]',
            '.js-stream-content',
            '.stream-item',
            '.item',
            'article',
            '.news-article'
        ]
        article_containers = []
        for selector in article_selectors:
            containers = soup.select(selector)
            if containers:
                article_containers = containers
                break
        if not article_containers:
            article_containers = soup.find_all('h3')
        for container in article_containers[:25]:  # Limit to recent articles
            try:
                article = self._extract_article_from_container(container)
                if article and self.validate_article(article):
                    articles.append(article)
            except Exception as e:
                logger.error(f"Error extracting article from container: {e}")
                continue
        self.rate_limit(1.0)
        return articles
    
    def _extract_article_from_container(self, container) -> Dict[str, Any]:
        """Extract article data from a container element"""
        article = {
            'source': self.source_name
        }
        title_selectors = [
            'h3',
            'h2',
            'h4',
            '.title',
            '.headline',
            'a'
        ]
        title_elem = None
        for selector in title_selectors:
            if isinstance(container, BeautifulSoup):
                title_elem = container.select_one(selector)
            else:
                title_elem = container.find(selector.replace('.', ''), class_=selector[1:] if selector.startswith('.') else None) or container.select_one(selector)
            if title_elem:
                break
        if title_elem:
            article['title'] = self.clean_text(self.extract_text(title_elem))
            if title_elem.name == 'a':
                article['url'] = self._make_absolute_url(title_elem.get('href', ''))
            else:
                link_elem = title_elem.find('a') or container.find('a')
                if link_elem:
                    article['url'] = self._make_absolute_url(link_elem.get('href', ''))
        elif container.name == 'a':
            article['url'] = self._make_absolute_url(container.get('href', ''))
            article['title'] = self.clean_text(self.extract_text(container))
        summary_selectors = [
            '.summary',
            '.excerpt',
            '.description',
            '.teaser',
            'p'
        ]
        for selector in summary_selectors:
            if isinstance(container, BeautifulSoup):
                summary_elem = container.select_one(selector)
            else:
                summary_elem = container.find(selector.replace('.', ''), class_=selector[1:] if selector.startswith('.') else None) or container.select_one(selector)
            if summary_elem:
                summary_text = self.clean_text(self.extract_text(summary_elem))
                if len(summary_text) > 50:
                    article['summary'] = summary_text
                    break
        date_selectors = [
            'time',
            '.date',
            '.published',
            '.timestamp',
            '[data-test-locator="published-date"]'
        ]
        for selector in date_selectors:
            if isinstance(container, BeautifulSoup):
                date_elem = container.select_one(selector)
            else:
                date_elem = container.find(selector.replace('.', ''), class_=selector[1:] if selector.startswith('.') else None) or container.select_one(selector)
            if date_elem:
                date_str = date_elem.get('datetime') or self.extract_text(date_elem)
                article['published_date'] = self.extract_date(date_str)
                break
        if 'published_date' not in article:
            article['published_date'] = datetime.now()
        return article
    
    def extract_article_details(self, article_url: str) -> Dict[str, Any]:
        """Extract detailed information from a single Yahoo article"""
        details = {}
        
        soup = self.get_soup(article_url, use_selenium=True)
        if not soup:
            return details
        
        # Extract full article content - Yahoo has specific structures
        content_selectors = [
            '.caas-body',
            '.article-body',
            '.content-body',
            '[data-test-locator="article-body"]',
            '.story-body',
            'article',
            '.content'
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if content_elem:
            # Remove ads, related links, and other noise
            for noise in content_elem.find_all(['aside', '.ad', '.advertisement', '.related']):
                noise.decompose()
            
            details['full_text'] = self.clean_text(self.extract_text(content_elem))
        
        # Extract company information
        details.update(self._extract_company_info(soup))
        
        # Extract clinical trial information
        details.update(self._extract_clinical_info(soup))
        
        # Extract financial information
        details.update(self._extract_financial_info(soup))
        
        self.rate_limit(1.0)
        return details
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract company-related information"""
        info = {}
        
        # Look for company names in various places
        text = soup.get_text()
        
        # Extract company names with common patterns
        company_patterns = [
            r'([A-Z][a-zA-Z\s&,\.]+(?:Inc|Corp|Ltd|LLC|Company|Co\.|Corporation|Pharmaceuticals|Biotech|Therapeutics|Sciences))',
            r'([A-Z][a-zA-Z\s&,\.]{3,30})\s*\([A-Z]{2,5}\)',  # Company name before ticker
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Take the first reasonable match
                for match in matches:
                    company_name = match.strip() if isinstance(match, str) else match[0].strip()
                    if 10 <= len(company_name) <= 60:  # Reasonable length
                        info['company_name'] = company_name
                        break
                if 'company_name' in info:
                    break
        
        # Look for ticker symbols
        ticker_patterns = [
            r'\(([A-Z]{2,5})\)',
            r'NYSE:\s*([A-Z]{2,5})',
            r'NASDAQ:\s*([A-Z]{2,5})',
            r'OTCQB:\s*([A-Z]{2,5})',
            r'ticker:\s*([A-Z]{2,5})'
        ]
        
        for pattern in ticker_patterns:
            match = re.search(pattern, text)
            if match:
                info['company_ticker'] = match.group(1)
                break
        
        # Extract employee count if mentioned
        employee_patterns = [
            r'(\d+(?:,\d+)*)\s+employees?',
            r'employs?\s+(?:about\s+|approximately\s+|over\s+)?(\d+(?:,\d+)*)',
            r'workforce\s+of\s+(?:about\s+|approximately\s+|over\s+)?(\d+(?:,\d+)*)',
            r'staff\s+of\s+(?:about\s+|approximately\s+|over\s+)?(\d+(?:,\d+)*)'
        ]
        
        for pattern in employee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    employee_count = int(match.group(1).replace(',', ''))
                    if 10 <= employee_count <= 1_000_000:  # Reasonable range
                        info['employee_count'] = employee_count
                        break
                except ValueError:
                    continue
        
        return info
    
    def _extract_clinical_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract clinical trial and approval information"""
        info = {}
        
        text = soup.get_text().lower()
        
        # Extract P-values
        p_value_patterns = [
            r'p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'p-value\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistical significance.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistically significant.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in p_value_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    p_value = float(f"0.{match}" if not match.startswith('0') else match)
                    if 0 <= p_value <= 1:
                        info['p_value'] = p_value
                        break
                except ValueError:
                    continue
            if 'p_value' in info:
                break
        
        # Detect trial phases
        phase_patterns = {
            'phase_1': [
                r'phase\s+i\b', r'phase\s+1\b', r'first-in-human',
                r'phase\s+1a', r'phase\s+1b', r'safety\s+study'
            ],
            'phase_2': [
                r'phase\s+ii\b', r'phase\s+2\b', r'phase\s+2a',
                r'phase\s+2b', r'efficacy\s+study'
            ],
            'phase_3': [
                r'phase\s+iii\b', r'phase\s+3\b', r'pivotal\s+trial',
                r'registration\s+trial', r'confirmatory\s+study'
            ]
        }
        
        for phase, patterns in phase_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    info['trial_phase'] = phase
                    break
            if 'trial_phase' in info:
                break
        
        # Detect approval status
        approval_patterns = {
            'approved': [
                r'fda\s+approval', r'approved\s+by.*?fda', r'regulatory\s+approval',
                r'granted\s+approval', r'received\s+approval', r'clearance.*?fda'
            ],
            'rejected': [
                r'rejected\s+by', r'denied\s+by', r'failed\s+to\s+meet',
                r'discontinued', r'terminated', r'unsuccessful'
            ],
            'pending': [
                r'pending\s+approval', r'under\s+review', r'submitted.*?fda',
                r'awaiting\s+approval', r'application.*?submitted'
            ],
            'breakthrough': [
                r'breakthrough\s+therapy', r'fast\s+track', r'orphan\s+drug',
                r'priority\s+review', r'accelerated\s+approval'
            ]
        }
        
        for status, patterns in approval_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    info['approval_status'] = status
                    break
            if 'approval_status' in info:
                break
        
        # Extract drug/treatment names
        drug_patterns = [
            r'drug\s+called\s+([a-z0-9\-]+)',
            r'treatment\s+([a-z0-9\-]+)',
            r'therapy\s+([a-z0-9\-]+)',
            r'compound\s+([a-z0-9\-]+)'
        ]
        
        for pattern in drug_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                drug_name = match.group(1).strip()
                if 3 <= len(drug_name) <= 20:  # Reasonable length
                    info['drug_name'] = drug_name
                    break
        
        return info
    
    def _extract_financial_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract financial and market information"""
        info = {}
        
        text = soup.get_text()
        
        # Extract market cap
        market_cap_patterns = [
            r'market\s+cap(?:italization)?\s+of\s+\$?([\d,\.]+)\s*([bmk])?',
            r'\$?([\d,\.]+)\s*([bmk])?\s+market\s+cap',
            r'valued\s+at\s+\$?([\d,\.]+)\s*([bmk])?'
        ]
        
        for pattern in market_cap_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    multiplier = match.group(2)
                    
                    if multiplier:
                        multiplier = multiplier.lower()
                        if multiplier == 'b':
                            value *= 1_000_000_000
                        elif multiplier == 'm':
                            value *= 1_000_000
                        elif multiplier == 'k':
                            value *= 1_000
                    
                    info['market_cap'] = value
                    break
                except ValueError:
                    continue
        
        # Extract stock price information
        stock_patterns = [
            r'shares?\s+(?:are\s+)?(?:trading\s+)?(?:at\s+)?\$?([\d,\.]+)',
            r'stock\s+price\s+(?:of\s+)?\$?([\d,\.]+)',
            r'trading\s+at\s+\$?([\d,\.]+)'
        ]
        
        for pattern in stock_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1).replace(',', ''))
                    if 0.01 <= price <= 10000:  # Reasonable stock price range
                        info['stock_price'] = price
                        break
                except ValueError:
                    continue
        
        return info
    
    def _parse_rss_date(self, date_str: str) -> datetime:
        """Parse RSS date format"""
        if not date_str:
            return datetime.now()
        
        try:
            # RSS dates are typically in RFC 822 format
            import email.utils
            timestamp = email.utils.parsedate_to_datetime(date_str)
            return timestamp
        except:
            return self.extract_date(date_str)
    
    def _make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL"""
        if not url:
            return ""
        
        if url.startswith('http'):
            return url
        
        # Yahoo sometimes uses protocol-relative URLs
        if url.startswith('//'):
            return f"https:{url}"
        
        if url.startswith('/'):
            return f"{self.base_url}{url}"
        else:
            return f"{self.base_url}/{url}"