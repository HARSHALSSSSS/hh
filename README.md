# Biotech News Trading System

A comprehensive automated trading system that scrapes biotech news, analyzes sentiment, extracts key information, and makes intelligent trading decisions based on clinical trial results, regulatory approvals, and market sentiment.

## 🚀 Features

### News Scraping & Analysis
- **Multi-source scraping**: StockTitan, PR Newswire, BusinessWire, Yahoo Finance
- **Real-time monitoring**: Scrapes news every 15 minutes during market hours
- **Advanced NLP**: Sentiment analysis with biotech-specific keywords and patterns
- **Information extraction**: P-values, trial phases, approval status, company data

### Trading Intelligence
- **Multi-factor analysis**: Combines sentiment, clinical data, regulatory status, and financial metrics
- **Risk management**: Position sizing, stop losses, portfolio concentration limits
- **Automated execution**: Integrates with Alpaca for paper and live trading
- **Performance tracking**: Complete trade history and P&L tracking

### Risk Management
- **Position limits**: Maximum 5% per position by default
- **Daily trade limits**: Configurable maximum trades per day
- **Portfolio monitoring**: Real-time risk assessment and emergency stops
- **Stop losses**: Automatic 10% stop losses with configurable take profits

## 📋 Requirements

- Python 3.8+
- Chrome/Chromium browser (for web scraping)
- Alpaca Trading Account (paper trading recommended for testing)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd biotech-trading-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Configure Alpaca API**
   - Sign up for [Alpaca](https://alpaca.markets/)
   - Get your API keys from the dashboard
   - Add them to your `.env` file

## ⚙️ Configuration

### Required Configuration (.env file)

```bash
# Alpaca Trading API (Required)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading

# Optional configurations
MAX_POSITION_SIZE=0.05  # 5% max per position
STOP_LOSS_PERCENTAGE=0.1  # 10% stop loss
MAX_DAILY_TRADES=10
```

### Key Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_POSITION_SIZE` | 0.05 | Maximum position size as % of portfolio |
| `STOP_LOSS_PERCENTAGE` | 0.1 | Stop loss percentage (10%) |
| `TAKE_PROFIT_PERCENTAGE` | 0.2 | Take profit percentage (20%) |
| `MAX_DAILY_TRADES` | 10 | Maximum trades per day |
| `P_VALUE_THRESHOLD_SIGNIFICANT` | 0.05 | P-value threshold for significance |
| `MIN_MARKET_CAP` | 100M | Minimum market cap filter |
| `SCRAPE_INTERVAL_MINUTES` | 15 | News scraping frequency |

## 🏃 Running the System

### Start the main system
```bash
python main.py
```

### Initialize database only
```bash
python -c "from database import init_database; init_database()"
```

### Test individual components
```bash
# Test news scraping
python -c "from scraper import StockTitanScraper; scraper = StockTitanScraper(); print(len(scraper.scrape_articles()))"

# Test sentiment analysis
python -c "from nlp import SentimentAnalyzer; analyzer = SentimentAnalyzer(); print(analyzer.analyze_sentiment('FDA approves breakthrough cancer therapy', 'Great news'))"

# Test trading connection
python -c "from trading import AlpacaClient; client = AlpacaClient(); print(client.get_account_info())"
```

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   News Sources  │    │   NLP Analysis  │    │ Trading Engine  │
│                 │    │                 │    │                 │
│ • StockTitan    │───▶│ • Sentiment     │───▶│ • Signal Gen    │
│ • PR Newswire   │    │ • Info Extract  │    │ • Risk Mgmt     │
│ • BusinessWire  │    │ • P-value Det   │    │ • Execution     │
│ • Yahoo Finance │    │ • Approval Det  │    │ • Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     SQLite Database                        │
│  Articles • Companies • Trades • Logs • Performance       │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Trading Strategy

The system uses a multi-factor scoring approach:

### Sentiment Analysis (25% weight)
- TextBlob + transformer models for base sentiment
- Biotech-specific positive/negative indicators
- Clinical trial outcome keywords
- Statistical significance detection

### Clinical Data (35% weight)
- **P-value analysis**: Highly significant (p<0.01), significant (p<0.05)
- **Trial phases**: Phase 3 > Phase 2 > Phase 1
- **Patient enrollment**: Larger trials weighted higher
- **Endpoint achievement**: Primary/secondary endpoint data

### Regulatory Status (30% weight)
- **FDA approval**: Strong positive signal
- **Breakthrough therapy**: Very positive
- **Rejection/discontinuation**: Strong negative
- **Special designations**: Fast track, orphan drug, etc.

### Financial Metrics (10% weight)
- Market cap analysis (avoid micro-caps)
- Employee count (company size indicator)
- Recent funding events
- Stock volatility (beta)

## 📈 Example Trading Signals

### Strong BUY Signal
```
Company: Moderna (MRNA)
Action: BUY
Confidence: 0.85
Position Size: 4.2%
Reasoning:
- Positive sentiment: 0.742
- Highly significant p-value: 0.003
- Trial phase phase_3: +0.5
- Regulatory status 'approved': +0.9
- Large funding: $250.0M
```

### Risk Management Override
```
Position size reduced from 0.050 to 0.025 due to portfolio risk
Daily trades: 8/10 remaining
Portfolio risk score: 45.2 (MODERATE)
Emergency stop: False
```

## 🛡️ Risk Management Features

### Position-Level Risk
- Maximum 5% position size (configurable)
- Automatic stop losses at 10%
- Risk/reward ratio minimum 1:1.5
- Volatility-adjusted position sizing

### Portfolio-Level Risk
- Maximum 80% allocation to biotech sector
- Concentration risk monitoring (Herfindahl index)
- Daily trade limits
- Emergency stop conditions

### Emergency Stop Triggers
- Portfolio risk score > 80
- Daily loss > 5%
- Total portfolio risk > 30%
- Single position > 15% of portfolio

## 📝 Logging and Monitoring

### System Logs
- Real-time logging to file and console
- Structured JSON logs for analysis
- Performance metrics tracking
- Error reporting and alerts

### Database Tracking
- All articles scraped and processed
- Complete trading history
- Risk management decisions
- Performance analytics

### Health Checks
- Daily system health monitoring
- Database connection status
- API connectivity checks
- Scraping activity verification

## 🔧 Customization

### Adding New News Sources
1. Create scraper class inheriting from `BaseScraper`
2. Implement `scrape_articles()` and `extract_article_details()`
3. Add to `NEWS_SOURCES` in config
4. Register in main system

### Custom Trading Signals
1. Modify `TradingStrategy.analyze_article()`
2. Adjust scoring weights in `_generate_signal()`
3. Add new factors to analysis methods
4. Update risk management rules

### Enhanced NLP
1. Add custom sentiment models in `SentimentAnalyzer`
2. Extend keyword lists in config
3. Add new extraction patterns in `BiotechExtractor`
4. Implement custom preprocessing

## 🚨 Important Disclaimers

⚠️ **Risk Warning**: Trading involves substantial risk of loss. This system is for educational purposes.

⚠️ **Paper Trading**: Start with paper trading (default configuration) to test the system.

⚠️ **Market Data**: System relies on publicly available news and may have delays.

⚠️ **No Guarantees**: Past performance does not guarantee future results.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the logs in `biotech_trader.log`
- Verify API credentials and permissions
- Test individual components first

## 🔄 Future Enhancements

- Real-time WebSocket feeds
- Machine learning models for signal generation
- Options trading strategies
- Portfolio optimization algorithms
- Web dashboard for monitoring
- Mobile app integration
- Advanced backtesting framework