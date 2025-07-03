import re
import feedparser
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper
from config import config

class PRNewswireScraper(BaseScraper):
    """Scraper for PR Newswire healthcare and biotech news"""
    
    def __init__(self):
        super().__init__("prnewswire")
        self.urls = [
            config.NEWS_SOURCES["prnewswire"]["health_url"],
            config.NEWS_SOURCES["prnewswire"]["clinical_trials_url"],
            config.NEWS_SOURCES["prnewswire"]["fda_approval_url"],
            config.NEWS_SOURCES["prnewswire"]["biotechnology_url"],
            config.NEWS_SOURCES["prnewswire"]["pharmaceuticals_url"],
        ]

    def scrape_articles(self) -> List[Dict[str, Any]]:
        """Scrape articles from PR Newswire all relevant sections and RSS feed"""
        articles = []

        # Scrape all relevant web sections
        for url in self.urls:
            articles.extend(self._scrape_webpage(url))
        
        # Optionally, also include RSS feed if you want
        rss_articles = self._scrape_rss_feed()
        articles.extend(rss_articles)

        # Remove duplicates by URL
        seen_urls = set()
        unique_articles = []
        for article in articles:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        return unique_articles

    def _scrape_rss_feed(self) -> List[Dict[str, Any]]:
        """Scrape articles from RSS feed"""
        articles = []
        
        try:
            feed = feedparser.parse(self.rss_url)
            
            for entry in feed.entries[:25]:  # Limit to recent articles
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
            logger.error(f"Error parsing RSS feed: {e}")
        
        return articles
    
    def _scrape_webpage(self, url: str) -> List[Dict[str, Any]]:
        """Scrape articles from PR Newswire healthcare webpage"""
        articles = []
        
        soup = self.get_soup(url, use_selenium=True)
        if not soup:
            return articles
        
        # Find article containers
        article_selectors = [
            'div.card-content',
            'div.news-release',
            'article',
            'div.item',
            '.news-item'
        ]
        
        article_containers = []
        for selector in article_selectors:
            containers = soup.select(selector)
            if containers:
                article_containers = containers
                break
        
        for container in article_containers[:20]:  # Limit to recent articles
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
        
        # Extract title
        title_selectors = ['h3', 'h2', 'h4', '.title', '.headline', 'a']
        title_elem = None
        
        for selector in title_selectors:
            title_elem = container.select_one(selector)
            if title_elem:
                break
        
        if title_elem:
            article['title'] = self.clean_text(self.extract_text(title_elem))
            
            # Extract URL
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
            if not link_elem:
                link_elem = container.find('a')
            
            if link_elem:
                href = link_elem.get('href', '')
                article['url'] = self._make_absolute_url(href)
        
        # Extract summary
        summary_selectors = ['.summary', '.excerpt', '.description', 'p']
        for selector in summary_selectors:
            summary_elem = container.select_one(selector)
            if summary_elem:
                article['summary'] = self.clean_text(self.extract_text(summary_elem))
                break
        
        # Extract date
        date_selectors = ['time', '.date', '.published', '.timestamp']
        for selector in date_selectors:
            date_elem = container.select_one(selector)
            if date_elem:
                date_str = date_elem.get('datetime') or self.extract_text(date_elem)
                article['published_date'] = self.extract_date(date_str)
                break
        
        if 'published_date' not in article:
            article['published_date'] = datetime.now()
        
        return article
    
    def extract_article_details(self, article_url: str) -> Dict[str, Any]:
        """Extract detailed information from a single PR Newswire article"""
        details = {}
        
        soup = self.get_soup(article_url, use_selenium=True)
        if not soup:
            return details
        
        # Extract full article content
        content_selectors = [
            '.release-body',
            '.news-release-content',
            '.article-content',
            '.press-release-content',
            'article',
            '.content'
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if content_elem:
            details['full_text'] = self.clean_text(self.extract_text(content_elem))
        
        # Extract company information
        details.update(self._extract_company_info(soup))
        
        # Extract clinical trial information
        details.update(self._extract_clinical_info(soup))
        
        # Extract contact and financial information
        details.update(self._extract_contact_info(soup))
        
        self.rate_limit(1.0)
        return details
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract company-related information"""
        info = {}
        
        # Look for company name in title or first paragraph
        company_selectors = [
            '.company-name',
            '.organization',
            'h1',
            'h2'
        ]
        
        for selector in company_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = self.extract_text(elem)
                company_match = re.search(r'([A-Z][a-zA-Z\s&,\.]+(?:Inc|Corp|Ltd|LLC|Company|Co\.|Corporation|Pharmaceuticals|Biotech|Therapeutics))', text)
                if company_match:
                    info['company_name'] = company_match.group(1).strip()
                    break
        
        # Look for ticker symbols
        text = soup.get_text()
        ticker_patterns = [
            r'\(([A-Z]{2,5})\)',
            r'NYSE:\s*([A-Z]{2,5})',
            r'NASDAQ:\s*([A-Z]{2,5})',
            r'OTCQB:\s*([A-Z]{2,5})'
        ]
        
        for pattern in ticker_patterns:
            match = re.search(pattern, text)
            if match:
                info['company_ticker'] = match.group(1)
                break
        
        # Extract employee count and market cap if mentioned
        employee_patterns = [
            r'(\d+(?:,\d+)*)\s+employees?',
            r'employs?\s+(\d+(?:,\d+)*)',
            r'workforce\s+of\s+(\d+(?:,\d+)*)'
        ]
        
        for pattern in employee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    info['employee_count'] = int(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        return info
    
    def _extract_clinical_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract clinical trial and approval information"""
        info = {}
        
        text = soup.get_text().lower()
        
        # Extract P-values with various formats
        p_value_patterns = [
            r'p\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)',
            r'p-value\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistical significance.*?p\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistically significant.*?p\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)'
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
            'phase_1': [r'phase\s+i\b', r'phase\s+1\b', r'first-in-human', r'phase\s+1a', r'phase\s+1b'],
            'phase_2': [r'phase\s+ii\b', r'phase\s+2\b', r'phase\s+2a', r'phase\s+2b'],
            'phase_3': [r'phase\s+iii\b', r'phase\s+3\b', r'pivotal\s+trial', r'registration\s+trial']
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
                r'fda\s+approval', r'approved\s+by\s+the\s+fda', r'regulatory\s+approval',
                r'granted\s+approval', r'received\s+approval'
            ],
            'rejected': [
                r'rejected\s+by', r'denied\s+by', r'failed\s+to\s+meet',
                r'discontinued', r'terminated\s+early'
            ],
            'pending': [
                r'pending\s+approval', r'under\s+review', r'submitted.*?fda',
                r'awaiting\s+approval', r'application\s+submitted'
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
        
        return info
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract contact and additional company information"""
        info = {}
        
        # Look for contact sections
        contact_selectors = [
            '.contact-info',
            '.media-contact',
            '.investor-contact',
            '.press-contact'
        ]
        
        for selector in contact_selectors:
            contact_elem = soup.select_one(selector)
            if contact_elem:
                contact_text = self.extract_text(contact_elem)
                
                # Extract company size indicators
                if 'fortune 500' in contact_text.lower():
                    info['company_size'] = 'large'
                elif 'public company' in contact_text.lower():
                    info['company_size'] = 'public'
                elif 'private company' in contact_text.lower():
                    info['company_size'] = 'private'
                
                break
        
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
        
        if url.startswith('/'):
            return f"{self.base_url}{url}"
        else:
            return f"{self.base_url}/{url}"