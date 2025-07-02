import re
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper
from config import config

class BusinessWireScraper(BaseScraper):
    """Scraper for BusinessWire biotech and healthcare news"""
    
    def __init__(self):
        super().__init__("businesswire")
        self.base_url = config.NEWS_SOURCES["businesswire"]["base_url"]
        self.biotech_url = config.NEWS_SOURCES["businesswire"]["biotech_url"]
    
    def scrape_articles(self) -> List[Dict[str, Any]]:
        """Scrape articles from BusinessWire biotech section"""
        articles = []
        
        soup = self.get_soup(self.biotech_url, use_selenium=True)
        if not soup:
            return articles
        
        # Find article containers - BusinessWire uses specific structures
        article_selectors = [
            '.bw-release-main',
            '.module-headline',
            '.item-content',
            'article',
            '.news-item'
        ]
        
        article_containers = []
        for selector in article_selectors:
            containers = soup.select(selector)
            if containers:
                article_containers = containers
                break
        
        # Fallback: look for links that contain typical BusinessWire patterns
        if not article_containers:
            article_containers = soup.find_all('a', href=re.compile(r'/news/home/\d+/en/'))
        
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
        
        # Extract title
        title_selectors = [
            'h2',
            'h3', 
            '.headline',
            '.title',
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
            
            # Extract URL
            if title_elem.name == 'a':
                article['url'] = self._make_absolute_url(title_elem.get('href', ''))
            else:
                link_elem = title_elem.find('a') or container.find('a')
                if link_elem:
                    article['url'] = self._make_absolute_url(link_elem.get('href', ''))
        elif container.name == 'a':
            # Container itself is a link
            article['url'] = self._make_absolute_url(container.get('href', ''))
            article['title'] = self.clean_text(self.extract_text(container))
        
        # Extract summary/description
        summary_selectors = [
            '.summary',
            '.excerpt', 
            '.description',
            'p'
        ]
        
        for selector in summary_selectors:
            if isinstance(container, BeautifulSoup):
                summary_elem = container.select_one(selector)
            else:
                summary_elem = container.find(selector.replace('.', ''), class_=selector[1:] if selector.startswith('.') else None) or container.select_one(selector)
            if summary_elem:
                article['summary'] = self.clean_text(self.extract_text(summary_elem))
                break
        
        # Extract date
        date_selectors = [
            'time',
            '.date',
            '.published',
            '.timestamp'
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
        
        # Check biotech relevance
        article['is_biotech_relevant'] = self.is_biotech_relevant(
            article.get('title', ''), 
            article.get('summary', '')
        )
        
        return article
    
    def extract_article_details(self, article_url: str) -> Dict[str, Any]:
        """Extract detailed information from a single BusinessWire article"""
        details = {}
        
        soup = self.get_soup(article_url, use_selenium=True)
        if not soup:
            return details
        
        # Extract full article content
        content_selectors = [
            '.bw-release-body',
            '.release-body',
            '.article-content',
            '.press-release-content',
            '.news-content',
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
        
        # Extract structured data from BusinessWire format
        details.update(self._extract_company_info(soup))
        details.update(self._extract_clinical_info(soup))
        details.update(self._extract_business_info(soup))
        
        self.rate_limit(1.0)
        return details
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract company-related information"""
        info = {}
        
        # BusinessWire often has company info in specific sections
        company_selectors = [
            '.bw-company-info',
            '.company-name',
            '.organization'
        ]
        
        for selector in company_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = self.extract_text(elem)
                company_match = re.search(r'([A-Z][a-zA-Z\s&,\.]+(?:Inc|Corp|Ltd|LLC|Company|Co\.|Corporation|Pharmaceuticals|Biotech|Therapeutics))', text)
                if company_match:
                    info['company_name'] = company_match.group(1).strip()
                    break
        
        # Look in article title and first paragraph if not found
        if 'company_name' not in info:
            title_text = soup.find('h1')
            if title_text:
                title_text = self.extract_text(title_text)
                company_match = re.search(r'([A-Z][a-zA-Z\s&,\.]+(?:Inc|Corp|Ltd|LLC|Company|Co\.|Corporation|Pharmaceuticals|Biotech|Therapeutics))', title_text)
                if company_match:
                    info['company_name'] = company_match.group(1).strip()
        
        # Look for ticker symbols in various formats
        full_text = soup.get_text()
        ticker_patterns = [
            r'\(([A-Z]{2,5})\)',
            r'NYSE:\s*([A-Z]{2,5})',
            r'NASDAQ:\s*([A-Z]{2,5})',
            r'OTCQB:\s*([A-Z]{2,5})',
            r'TSX:\s*([A-Z]{2,5})',
            r'LSE:\s*([A-Z]{2,5})'
        ]
        
        for pattern in ticker_patterns:
            match = re.search(pattern, full_text)
            if match:
                info['company_ticker'] = match.group(1)
                break
        
        # Extract employee count
        employee_patterns = [
            r'(\d+(?:,\d+)*)\s+employees?',
            r'employs?\s+(?:over\s+|more\s+than\s+)?(\d+(?:,\d+)*)',
            r'workforce\s+of\s+(?:over\s+|more\s+than\s+)?(\d+(?:,\d+)*)',
            r'team\s+of\s+(?:over\s+|more\s+than\s+)?(\d+(?:,\d+)*)\s+(?:employees?|people)'
        ]
        
        for pattern in employee_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    info['employee_count'] = int(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # Extract market cap and financial info
        market_cap_patterns = [
            r'market\s+cap(?:italization)?\s+of\s+\$?([\d,\.]+)\s*([bmk])?',
            r'\$?([\d,\.]+)\s*([bmk])?\s+market\s+cap',
            r'valued\s+at\s+\$?([\d,\.]+)\s*([bmk])?'
        ]
        
        for pattern in market_cap_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
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
        
        return info
    
    def _extract_clinical_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract clinical trial and regulatory information"""
        info = {}
        
        text = soup.get_text().lower()
        
        # Extract P-values with enhanced patterns
        p_value_patterns = [
            r'p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'p-value\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistical significance.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistically significant.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'primary endpoint.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'met.*?endpoint.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)'
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
        
        # Detect trial phases with more comprehensive patterns
        phase_patterns = {
            'phase_1': [
                r'phase\s+i\b', r'phase\s+1\b', r'first-in-human', 
                r'phase\s+1a', r'phase\s+1b', r'dose-escalation'
            ],
            'phase_2': [
                r'phase\s+ii\b', r'phase\s+2\b', r'phase\s+2a', 
                r'phase\s+2b', r'proof-of-concept'
            ],
            'phase_3': [
                r'phase\s+iii\b', r'phase\s+3\b', r'pivotal\s+trial', 
                r'registration\s+trial', r'confirmatory\s+trial'
            ]
        }
        
        for phase, patterns in phase_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    info['trial_phase'] = phase
                    break
            if 'trial_phase' in info:
                break
        
        # Detect approval status with BusinessWire-specific patterns
        approval_patterns = {
            'approved': [
                r'fda\s+approval', r'approved\s+by\s+the\s+fda', r'regulatory\s+approval',
                r'granted\s+approval', r'received\s+approval', r'marketing\s+authorization',
                r'clearance\s+from', r'license\s+granted'
            ],
            'rejected': [
                r'rejected\s+by', r'denied\s+by', r'failed\s+to\s+meet',
                r'discontinued', r'terminated\s+early', r'did\s+not\s+meet',
                r'unsuccessful', r'negative\s+results'
            ],
            'pending': [
                r'pending\s+approval', r'under\s+review', r'submitted.*?fda',
                r'awaiting\s+approval', r'application\s+submitted', r'filed\s+with',
                r'regulatory\s+submission'
            ],
            'breakthrough': [
                r'breakthrough\s+therapy', r'fast\s+track', r'orphan\s+drug',
                r'priority\s+review', r'accelerated\s+approval', r'rare\s+pediatric',
                r'qualified\s+infectious\s+disease'
            ]
        }
        
        for status, patterns in approval_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    info['approval_status'] = status
                    break
            if 'approval_status' in info:
                break
        
        # Extract indication/disease information
        indication_patterns = [
            r'for\s+the\s+treatment\s+of\s+([a-z\s,]+)',
            r'treating\s+([a-z\s,]+)',
            r'indication:\s*([a-z\s,]+)',
            r'to\s+treat\s+([a-z\s,]+)'
        ]
        
        for pattern in indication_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                indication = match.group(1).strip()
                if len(indication) < 100:  # Reasonable length
                    info['indication'] = indication
                    break
        
        return info
    
    def _extract_business_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract business and financial information"""
        info = {}
        
        text = soup.get_text().lower()
        
        # Extract partnership/collaboration info
        partnership_patterns = [
            r'partnership\s+with\s+([a-z\s,\.]+)',
            r'collaboration\s+with\s+([a-z\s,\.]+)',
            r'acquired\s+by\s+([a-z\s,\.]+)',
            r'merger\s+with\s+([a-z\s,\.]+)'
        ]
        
        for pattern in partnership_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                partner = match.group(1).strip()
                if len(partner) < 50:  # Reasonable length
                    info['partnership'] = partner
                    break
        
        # Extract funding information
        funding_patterns = [
            r'\$?([\d,\.]+)\s*([bmk])?\s+(?:in\s+)?(?:funding|investment|financing)',
            r'raised\s+\$?([\d,\.]+)\s*([bmk])?',
            r'series\s+[a-z]\s+\$?([\d,\.]+)\s*([bmk])?'
        ]
        
        for pattern in funding_patterns:
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
                    
                    info['funding_amount'] = value
                    break
                except ValueError:
                    continue
        
        return info
    
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