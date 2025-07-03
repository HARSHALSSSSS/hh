import re
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper
from config import config

class StockTitanScraper(BaseScraper):
    """Scraper for StockTitan biotech and clinical trials news"""
    
    def __init__(self):
        super().__init__("stocktitan")
        self.urls = [
            config.NEWS_SOURCES["stocktitan"]["base_url"],
            config.NEWS_SOURCES["stocktitan"]["fda_approvals_url"],
            config.NEWS_SOURCES["stocktitan"]["clinical_trials_url"],
        ]
    
    def scrape_articles(self) -> List[Dict[str, Any]]:
        """Scrape articles from all relevant StockTitan sections (no keyword filtering)"""
        articles = []
        for url in self.urls:
            articles.extend(self._scrape_section(url))
        # Remove duplicates by URL
        seen_urls = set()
        unique_articles = []
        for article in articles:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        return unique_articles
    
    def _scrape_section(self, url: str) -> List[Dict[str, Any]]:
        articles = []
        soup = self.get_soup(url, use_selenium=True)
        if not soup:
            return articles
        # Find article containers
        article_containers = soup.find_all('div', class_=['article-item', 'news-item', 'post-item'])
        if not article_containers:
            article_containers = soup.find_all('a', href=re.compile(r'/news/|/article/|/post/'))
        for container in article_containers[:20]:
            try:
                article = self._extract_article_from_container(container, url)
                if article and self.validate_article(article):
                    articles.append(article)
            except Exception as e:
                logger.error(f"Error extracting article from container: {e}")
                continue
        self.rate_limit(1.0)
        return articles
    
    def _extract_article_from_container(self, container, url: str) -> Dict[str, Any]:
        """Extract article data from a container element"""
        article = {
            'source': self.source_name,
            'url': url
        }
        
        # Extract title
        title_elem = (
            container.find('h2') or 
            container.find('h3') or 
            container.find('a', class_=re.compile(r'title|headline')) or
            container.find('a')
        )
        
        if title_elem:
            article['title'] = self.clean_text(self.extract_text(title_elem))
            
            # Extract URL
            if title_elem.name == 'a':
                article['url'] = self._make_absolute_url(title_elem.get('href', ''))
            else:
                link_elem = title_elem.find('a') or container.find('a')
                if link_elem:
                    article['url'] = self._make_absolute_url(link_elem.get('href', ''))
        
        # Extract summary/description
        summary_elem = (
            container.find('p', class_=re.compile(r'summary|excerpt|description')) or
            container.find('div', class_=re.compile(r'summary|excerpt|description')) or
            container.find('p')
        )
        
        if summary_elem:
            article['summary'] = self.clean_text(self.extract_text(summary_elem))
        
        # Extract date
        date_elem = (
            container.find('time') or
            container.find('span', class_=re.compile(r'date|time')) or
            container.find('div', class_=re.compile(r'date|time'))
        )
        
        if date_elem:
            date_str = date_elem.get('datetime') or self.extract_text(date_elem)
            article['published_date'] = self.extract_date(date_str)
        else:
            article['published_date'] = datetime.now()
        
        return article
    
    def extract_article_details(self, article_url: str) -> Dict[str, Any]:
        """Extract detailed information from a single StockTitan article"""
        details = {}
        
        soup = self.get_soup(article_url, use_selenium=True)
        if not soup:
            return details
        
        # Extract full article content
        content_selectors = [
            'div.article-content',
            'div.post-content',
            'div.news-content',
            'article',
            'div.content'
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
        
        # Extract financial/market information
        details.update(self._extract_financial_info(soup))
        
        self.rate_limit(1.0)
        return details
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract company-related information"""
        info = {}
        
        text = soup.get_text().lower()
        
        # Look for company mentions with ticker symbols
        ticker_pattern = r'\b([A-Z]{2,5})\b'
        company_pattern = r'([A-Z][a-zA-Z\s&,\.]+(?:Inc|Corp|Ltd|LLC|Company|Co\.|Corporation|Pharmaceuticals|Biotech|Therapeutics))'
        
        tickers = re.findall(ticker_pattern, soup.get_text())
        companies = re.findall(company_pattern, soup.get_text())
        
        if tickers:
            info['company_ticker'] = tickers[0]
        
        if companies:
            info['company_name'] = companies[0].strip()
        
        # Extract employee count if mentioned
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
        
        # Extract P-values
        p_value_patterns = [
            r'p\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)',
            r'p-value\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistical significance.*?p\s*[=<]\s*0?\.?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in p_value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    p_value = float(f"0.{match.group(1)}" if not match.group(1).startswith('0') else match.group(1))
                    if 0 <= p_value <= 1:
                        info['p_value'] = p_value
                        break
                except ValueError:
                    continue
        
        # Detect trial phases
        phase_patterns = {
            'phase_1': [r'phase\s+i\b', r'phase\s+1\b', r'first-in-human'],
            'phase_2': [r'phase\s+ii\b', r'phase\s+2\b'],
            'phase_3': [r'phase\s+iii\b', r'phase\s+3\b', r'pivotal\s+trial']
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
            'approved': [r'fda\s+approval', r'approved\s+by', r'regulatory\s+approval'],
            'rejected': [r'rejected', r'denied', r'failed\s+to\s+meet', r'discontinued'],
            'pending': [r'pending\s+approval', r'under\s+review', r'submitted.*?fda'],
            'breakthrough': [r'breakthrough\s+therapy', r'fast\s+track', r'orphan\s+drug']
        }
        
        for status, patterns in approval_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    info['approval_status'] = status
                    break
            if 'approval_status' in info:
                break
        
        return info
    
    def _extract_financial_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract financial and market information"""
        info = {}
        
        text = soup.get_text()
        
        # Extract market cap
        market_cap_patterns = [
            r'market\s+cap(?:italization)?\s+of\s+\$?([\d,\.]+)\s*([bmk])?',
            r'\$?([\d,\.]+)\s*([bmk])?\s+market\s+cap'
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
        
        return info
    
    def _make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL"""
        if not url:
            return ""
        
        if url.startswith('http'):
            return url
        
        base_url = config.NEWS_SOURCES["stocktitan"]["base_url"]
        
        if url.startswith('/'):
            return f"{base_url}{url}"
        else:
            return f"{base_url}/{url}"