# How to Run the Biotech Trading System

## Prerequisites

### 1. Python Environment
- Python 3.8+ required
- Virtual environment recommended

### 2. System Dependencies
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3-pip python3-venv

# For other systems, ensure you have Python 3.8+ and pip installed
```

## Setup Instructions

### 1. Create Virtual Environment
```bash
# Navigate to your project directory
cd /path/to/biotech-trading-system

# Create virtual environment
python3 -m venv biotech_env

# Activate virtual environment
source biotech_env/bin/activate  # Linux/Mac
# OR on Windows:
# biotech_env\Scripts\activate
```

### 2. Install Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# Key dependencies include:
# - requests>=2.28.0
# - beautifulsoup4>=4.11.0
# - sqlalchemy>=1.4.0
# - yfinance>=0.2.0
# - nltk>=3.8
# - textblob>=0.17.0
# - alpaca-trade-api>=3.0.0
# - python-dotenv>=1.0.0
# - schedule>=1.2.0
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# Email Configuration (Required for notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=recipient@gmail.com

# Trading Configuration (Optional - defaults to paper trading)
ALPACA_API_KEY=your-alpaca-api-key
ALPACA_SECRET_KEY=your-alpaca-secret-key
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading (safe)
# ALPACA_BASE_URL=https://api.alpaca.markets      # Live trading (CAUTION!)

# Database Configuration (Optional - defaults to SQLite)
DATABASE_URL=sqlite:///biotech_trading.db

# Trading Parameters (Optional - has safe defaults)
MAX_POSITION_SIZE=1000
RELEVANCE_THRESHOLD=0.7
PAPER_TRADING=true
EMAIL_RATE_LIMIT=20
```

### 4. Database Setup
```bash
# Initialize the database (run once)
python -c "from my.database.models import create_tables; create_tables()"
```

### 5. Download NLP Data
```bash
# Download required NLTK data
python -c "import nltk; nltk.download('vader_lexicon'); nltk.download('punkt')"
```

## Running the System

### Option 1: Full System (Recommended)
```bash
# Activate virtual environment
source biotech_env/bin/activate

# Run the main trading system
python my/main.py
```

This will:
- Start scraping every 15 minutes during market hours (7 AM - 4 PM)
- Process articles with biotech relevance analysis
- Send email notifications for high-relevance articles
- Execute trades based on sentiment and market signals
- Use the 20-minute smart time window to catch all articles

### Option 2: Test Individual Components

#### Test News Scraping
```bash
python -c "
from my.scraper.stocktitan import StockTitanScraper
from my.scraper.prnewswire import PRNewswireScraper
scraper = StockTitanScraper()
articles = scraper.scrape()
print(f'Found {len(articles)} articles')
"
```

#### Test Email Notifications
```bash
python -c "
from my.notifications import EmailNotifier
notifier = EmailNotifier()
notifier.send_test_email()
"
```

#### Test NLP Analysis
```bash
python -c "
from my.nlp.extractor import BiotechExtractor
extractor = BiotechExtractor()
result = extractor.extract_biotech_info('FDA approves new cancer drug in Phase III trials')
print(result)
"
```

### Option 3: Specific Scraper Testing
```bash
# Test specific news sources
python my/scraper/stocktitan.py      # StockTitan news
python my/scraper/prnewswire.py      # PR Newswire
python my/scraper/businesswire.py    # BusinessWire
python my/scraper/yahoo.py           # Yahoo Finance
```

## System Behavior

### Timing Schedule
- **Scraping Interval**: Every 15 minutes during market hours
- **Market Hours**: 7:00 AM - 4:00 PM Eastern Time
- **Smart Window**: 20-minute lookback to catch articles published slightly before scraping
- **Weekend/Holiday**: System pauses automatically

### Email Notifications
You'll receive 6 types of emails:

1. **New Articles Alert** (Every 15 min): Summary of all new articles
2. **High-Relevance Alert** (Immediate): Detailed analysis for articles ≥0.8 relevance
3. **Trading Signal Alert** (Real-time): Buy/sell recommendations
4. **Trade Execution Alert** (Immediate): Confirmation of executed trades
5. **Risk Management Alert** (As needed): Portfolio warnings
6. **Daily Health Report** (End of day): System performance

### Safety Features
- **Paper Trading**: Enabled by default (no real money at risk)
- **Position Limits**: Maximum $1,000 per position by default
- **Risk Management**: Automatic stops and portfolio limits
- **Email Rate Limiting**: Maximum 20 emails per hour

## Monitoring and Logs

### View System Status
```bash
# Check recent activity
tail -f logs/trading_system.log

# View database content
python -c "
from my.database.models import Article, Trade
from my.database import get_session
session = get_session()
print(f'Articles: {session.query(Article).count()}')
print(f'Trades: {session.query(Trade).count()}')
"
```

### Common Log Locations
- `logs/trading_system.log` - Main system log
- `logs/scraper.log` - News scraping activity
- `logs/email.log` - Email notifications
- `logs/trading.log` - Trade execution

## Troubleshooting

### Email Issues
1. **Gmail**: Use App Passwords, not regular password
2. **2FA**: Must be enabled for App Passwords
3. **SMTP Settings**: Verify server and port for your provider

### Trading Issues
1. **Alpaca Keys**: Ensure paper trading keys are used initially
2. **Market Hours**: System only trades during market hours
3. **Insufficient Funds**: Check paper trading account balance

### Scraping Issues
1. **Network**: Ensure stable internet connection
2. **Rate Limits**: Built-in delays prevent blocking
3. **URL Changes**: News sites occasionally change URLs

### Performance
1. **Database**: SQLite suitable for development, PostgreSQL for production
2. **Memory**: System uses ~100-200MB RAM typically
3. **Disk**: Logs and database grow over time

## Security Notes

- **Never commit** `.env` file with real credentials
- **Use paper trading** until thoroughly tested
- **Monitor email** rate limits to avoid spam flags
- **Backup database** regularly for trade history
- **Keep API keys** secure and rotate regularly

## Production Deployment

For production use:
1. Use PostgreSQL instead of SQLite
2. Set up proper logging rotation
3. Configure system service/daemon
4. Set up monitoring and alerting
5. Use environment variables instead of .env file
6. Consider Docker containerization

## Support

If you encounter issues:
1. Check logs for error messages
2. Verify all environment variables are set
3. Test individual components before running full system
4. Ensure virtual environment is activated
5. Check network connectivity for news sources