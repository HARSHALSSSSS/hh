import re
import yfinance as yf
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from config import config

class BiotechExtractor:
    """Extract biotech-specific information from news articles"""
    
    def __init__(self):
        self.company_cache = {}  # Cache for company information
        
    def extract_all_info(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all biotech information from an article"""
        text = f"{article.get('title', '')} {article.get('summary', '')} {article.get('full_text', '')}"
        
        extracted_info = {}
        
        # Extract basic company information
        extracted_info.update(self.extract_company_info(text))
        
        # Extract clinical trial information
        extracted_info.update(self.extract_clinical_info(text))
        
        # Extract regulatory information
        extracted_info.update(self.extract_regulatory_info(text))
        
        # Extract financial information
        extracted_info.update(self.extract_financial_info(text))
        
        # Extract pipeline information
        extracted_info.update(self.extract_pipeline_info(text))
        
        # Get additional company data from external sources
        if 'company_ticker' in extracted_info:
            market_data = self.get_market_data(extracted_info['company_ticker'])
            extracted_info.update(market_data)
        
        return extracted_info
    
    def extract_company_info(self, text: str) -> Dict[str, Any]:
        """Extract company name, ticker, and basic info"""
        info = {}
        
        # Extract company names with various patterns
        company_patterns = [
            # Full company names with suffixes
            r'([A-Z][a-zA-Z\s&,\.]+(?:Inc|Corp|Ltd|LLC|Company|Co\.|Corporation|Pharmaceuticals|Biotech|Therapeutics|Sciences|AG|SE|SA|NV)\.?)',
            # Company name before ticker
            r'([A-Z][a-zA-Z\s&,\.]{3,40})\s*\(([A-Z]{2,5})\)',
            # Biotech-specific patterns
            r'([A-Z][a-zA-Z\s]{3,30}(?:Pharmaceuticals|Biotech|Therapeutics|Sciences|Medicine|Health))',
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        company_name = match[0].strip()
                        if len(match) > 1:
                            info['company_ticker'] = match[1].strip()
                    else:
                        company_name = match.strip()
                    
                    # Validate company name length and format
                    if 5 <= len(company_name) <= 60 and self._is_valid_company_name(company_name):
                        info['company_name'] = company_name
                        break
                
                if 'company_name' in info:
                    break
        
        # Extract ticker symbols if not found above
        if 'company_ticker' not in info:
            ticker_patterns = [
                r'\(([A-Z]{2,5})\)',
                r'NYSE:\s*([A-Z]{2,5})',
                r'NASDAQ:\s*([A-Z]{2,5})',
                r'OTCQB:\s*([A-Z]{2,5})',
                r'ticker:\s*([A-Z]{2,5})',
                r'symbol:\s*([A-Z]{2,5})'
            ]
            
            for pattern in ticker_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    ticker = match.group(1).upper()
                    if self._is_valid_ticker(ticker):
                        info['company_ticker'] = ticker
                        break
        
        # Extract employee count
        employee_patterns = [
            r'(\d+(?:,\d+)*)\s+employees?',
            r'employs?\s+(?:about\s+|approximately\s+|over\s+|more\s+than\s+)?(\d+(?:,\d+)*)',
            r'workforce\s+of\s+(?:about\s+|approximately\s+|over\s+|more\s+than\s+)?(\d+(?:,\d+)*)',
            r'staff\s+of\s+(?:about\s+|approximately\s+|over\s+|more\s+than\s+)?(\d+(?:,\d+)*)',
            r'team\s+of\s+(?:about\s+|approximately\s+|over\s+|more\s+than\s+)?(\d+(?:,\d+)*)\s+(?:employees?|people)'
        ]
        
        for pattern in employee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    employee_count = int(match.group(1).replace(',', ''))
                    if 1 <= employee_count <= 1_000_000:  # Reasonable range
                        info['employee_count'] = employee_count
                        break
                except ValueError:
                    continue
        
        return info
    
    def extract_clinical_info(self, text: str) -> Dict[str, Any]:
        """Extract clinical trial and study information"""
        info = {}
        text_lower = text.lower()
        
        # Extract P-values with multiple patterns
        p_value_patterns = [
            r'p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'p-value\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'statistical significance.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'primary endpoint.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)',
            r'met.*?endpoint.*?p\s*[=<≤]\s*0?\.?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in p_value_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
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
                r'phase\s+1a', r'phase\s+1b', r'dose-escalation',
                r'safety\s+study', r'dose-finding'
            ],
            'phase_2': [
                r'phase\s+ii\b', r'phase\s+2\b', r'phase\s+2a',
                r'phase\s+2b', r'proof-of-concept', r'efficacy\s+study'
            ],
            'phase_3': [
                r'phase\s+iii\b', r'phase\s+3\b', r'pivotal\s+trial',
                r'registration\s+trial', r'confirmatory\s+study',
                r'late-stage\s+trial'
            ]
        }
        
        for phase, patterns in phase_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    info['trial_phase'] = phase
                    break
            if 'trial_phase' in info:
                break
        
        # Extract trial endpoints and outcomes
        endpoint_patterns = [
            r'primary\s+endpoint[:\s]+([^\.]{10,100})',
            r'secondary\s+endpoint[:\s]+([^\.]{10,100})',
            r'overall\s+response\s+rate[:\s]*(\d+(?:\.\d+)?%?)',
            r'progression-free\s+survival[:\s]*(\d+(?:\.\d+)?\s*months?)',
            r'overall\s+survival[:\s]*(\d+(?:\.\d+)?\s*months?)'
        ]
        
        for pattern in endpoint_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                endpoint_value = match.group(1).strip()
                if 'primary endpoint' in pattern:
                    info['primary_endpoint'] = endpoint_value
                elif 'secondary endpoint' in pattern:
                    info['secondary_endpoint'] = endpoint_value
                elif 'response rate' in pattern:
                    info['response_rate'] = endpoint_value
                elif 'progression-free' in pattern:
                    info['progression_free_survival'] = endpoint_value
                elif 'overall survival' in pattern:
                    info['overall_survival'] = endpoint_value
        
        # Extract patient population and enrollment
        patient_patterns = [
            r'(\d+)\s+patients?',
            r'enrolled?\s+(\d+)',
            r'(\d+)\s+subjects?',
            r'study\s+of\s+(\d+)',
            r'n\s*=\s*(\d+)'
        ]
        
        for pattern in patient_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    patient_count = int(match.group(1))
                    if 1 <= patient_count <= 100000:  # Reasonable range
                        info['patient_count'] = patient_count
                        break
                except ValueError:
                    continue
        
        return info
    
    def extract_regulatory_info(self, text: str) -> Dict[str, Any]:
        """Extract regulatory approval and status information"""
        info = {}
        text_lower = text.lower()
        
        # Detect approval status with detailed patterns
        approval_patterns = {
            'approved': [
                r'fda\s+approval', r'approved\s+by\s+(?:the\s+)?fda', r'regulatory\s+approval',
                r'granted\s+approval', r'received\s+approval', r'marketing\s+authorization',
                r'clearance\s+from\s+(?:the\s+)?fda', r'license\s+granted', r'cleared\s+by\s+(?:the\s+)?fda'
            ],
            'rejected': [
                r'rejected\s+by\s+(?:the\s+)?fda', r'denied\s+by', r'failed\s+to\s+meet\s+(?:primary\s+)?endpoint',
                r'discontinued', r'terminated\s+early', r'did\s+not\s+meet',
                r'unsuccessful', r'negative\s+results', r'complete\s+response\s+letter'
            ],
            'pending': [
                r'pending\s+approval', r'under\s+review\s+by\s+(?:the\s+)?fda', r'submitted.*?fda',
                r'awaiting\s+approval', r'application\s+submitted', r'filed\s+with\s+(?:the\s+)?fda',
                r'regulatory\s+submission', r'nda\s+submitted', r'bla\s+submitted'
            ],
            'breakthrough': [
                r'breakthrough\s+therapy', r'fast\s+track', r'orphan\s+drug',
                r'priority\s+review', r'accelerated\s+approval', r'rare\s+pediatric\s+disease',
                r'qualified\s+infectious\s+disease\s+product'
            ]
        }
        
        for status, patterns in approval_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    info['approval_status'] = status
                    break
            if 'approval_status' in info:
                break
        
        # Extract regulatory designations
        designation_patterns = [
            r'(breakthrough\s+therapy)(?:\s+designation)?',
            r'(fast\s+track)(?:\s+designation)?',
            r'(orphan\s+drug)(?:\s+designation)?',
            r'(priority\s+review)(?:\s+designation)?',
            r'(accelerated\s+approval)(?:\s+pathway)?'
        ]
        
        designations = []
        for pattern in designation_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                designations.append(match.group(1))
        
        if designations:
            info['regulatory_designations'] = designations
        
        # Extract indication/disease information
        indication_patterns = [
            r'for\s+the\s+treatment\s+of\s+([a-z\s\-,]{5,50})',
            r'treating\s+([a-z\s\-,]{5,50})',
            r'indication[:\s]*([a-z\s\-,]{5,50})',
            r'to\s+treat\s+([a-z\s\-,]{5,50})',
            r'therapy\s+for\s+([a-z\s\-,]{5,50})'
        ]
        
        for pattern in indication_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                indication = match.group(1).strip()
                # Clean up the indication
                indication = re.sub(r'\s+', ' ', indication)
                indication = indication.rstrip('.,;')
                if 5 <= len(indication) <= 50:
                    info['indication'] = indication
                    break
        
        return info
    
    def extract_financial_info(self, text: str) -> Dict[str, Any]:
        """Extract financial and market information"""
        info = {}
        
        # Extract market cap
        market_cap_patterns = [
            r'market\s+cap(?:italization)?\s+of\s+\$?([\d,\.]+)\s*([bmk])?',
            r'\$?([\d,\.]+)\s*([bmk])?\s+market\s+cap',
            r'valued\s+at\s+\$?([\d,\.]+)\s*([bmk])?',
            r'market\s+value\s+of\s+\$?([\d,\.]+)\s*([bmk])?'
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
        
        # Extract funding information
        funding_patterns = [
            r'\$?([\d,\.]+)\s*([bmk])?\s+(?:in\s+)?(?:funding|investment|financing|capital)',
            r'raised\s+\$?([\d,\.]+)\s*([bmk])?',
            r'series\s+[a-z]\s+(?:round\s+of\s+)?\$?([\d,\.]+)\s*([bmk])?',
            r'invested\s+\$?([\d,\.]+)\s*([bmk])?',
            r'financing\s+of\s+\$?([\d,\.]+)\s*([bmk])?'
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
        
        # Extract stock price information
        stock_patterns = [
            r'shares?\s+(?:are\s+)?(?:trading\s+)?(?:at\s+)?\$?([\d,\.]+)',
            r'stock\s+price\s+(?:of\s+)?\$?([\d,\.]+)',
            r'trading\s+at\s+\$?([\d,\.]+)',
            r'price\s+(?:per\s+share\s+)?of\s+\$?([\d,\.]+)'
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
    
    def extract_pipeline_info(self, text: str) -> Dict[str, Any]:
        """Extract drug pipeline and development information"""
        info = {}
        text_lower = text.lower()
        
        # Extract drug/compound names
        drug_patterns = [
            r'drug\s+(?:called\s+|named\s+)?([a-z0-9\-]{3,20})',
            r'compound\s+([a-z0-9\-]{3,20})',
            r'therapy\s+([a-z0-9\-]{3,20})',
            r'treatment\s+([a-z0-9\-]{3,20})',
            r'candidate\s+([a-z0-9\-]{3,20})'
        ]
        
        drugs = []
        for pattern in drug_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if len(match) >= 3 and match not in drugs:
                    drugs.append(match)
        
        if drugs:
            info['drug_names'] = drugs[:5]  # Limit to first 5 drugs found
        
        # Extract mechanism of action
        moa_patterns = [
            r'(?:mechanism\s+of\s+action|moa)[:\s]*([^\.]{10,100})',
            r'targets?\s+([a-z0-9\-\s]{5,30})',
            r'inhibitor\s+of\s+([a-z0-9\-\s]{5,30})',
            r'agonist\s+of\s+([a-z0-9\-\s]{5,30})',
            r'antagonist\s+of\s+([a-z0-9\-\s]{5,30})'
        ]
        
        for pattern in moa_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                moa = match.group(1).strip()
                if 5 <= len(moa) <= 100:
                    info['mechanism_of_action'] = moa
                    break
        
        # Extract therapeutic area
        therapeutic_areas = [
            'oncology', 'immunology', 'neurology', 'cardiology', 'infectious disease',
            'rare disease', 'ophthalmology', 'dermatology', 'gastroenterology',
            'respiratory', 'endocrinology', 'hematology', 'nephrology'
        ]
        
        for area in therapeutic_areas:
            if area in text_lower:
                info['therapeutic_area'] = area
                break
        
        return info
    
    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Get real-time market data for a ticker"""
        if ticker in self.company_cache:
            return self.company_cache[ticker]
        
        try:
            stock = yf.Ticker(ticker)
            info_data = stock.info
            
            market_data = {}
            
            # Extract key financial metrics
            if 'marketCap' in info_data:
                market_data['market_cap'] = info_data['marketCap']
            
            if 'fullTimeEmployees' in info_data:
                market_data['employee_count'] = info_data['fullTimeEmployees']
            
            if 'currentPrice' in info_data:
                market_data['current_price'] = info_data['currentPrice']
            
            if 'volume' in info_data:
                market_data['volume'] = info_data['volume']
            
            if 'averageVolume' in info_data:
                market_data['avg_volume'] = info_data['averageVolume']
            
            if 'beta' in info_data:
                market_data['beta'] = info_data['beta']
            
            if 'sector' in info_data:
                market_data['sector'] = info_data['sector']
            
            if 'industry' in info_data:
                market_data['industry'] = info_data['industry']
            
            # Cache the result
            self.company_cache[ticker] = market_data
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data for {ticker}: {e}")
            return {}
    
    def _is_valid_company_name(self, name: str) -> bool:
        """Validate if a string looks like a company name"""
        # Basic validation rules
        if not name or len(name) < 5:
            return False
        
        # Should start with capital letter
        if not name[0].isupper():
            return False
        
        # Should not be all caps (likely an acronym)
        if name.isupper():
            return False
        
        # Should contain at least one space or common company suffix
        company_suffixes = ['Inc', 'Corp', 'Ltd', 'LLC', 'Company', 'Pharmaceuticals', 'Biotech', 'Therapeutics']
        if not any(suffix in name for suffix in company_suffixes) and ' ' not in name:
            return False
        
        return True
    
    def _is_valid_ticker(self, ticker: str) -> bool:
        """Validate if a string looks like a stock ticker"""
        if not ticker or len(ticker) < 1 or len(ticker) > 5:
            return False
        
        # Should be all uppercase letters
        if not ticker.isupper() or not ticker.isalpha():
            return False
        
        return True