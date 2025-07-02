#!/usr/bin/env python3
"""
Biotech News Trading System
A comprehensive system that scrapes biotech news, analyzes sentiment,
extracts key information, and makes automated trading decisions.
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger
from sqlalchemy.orm import sessionmaker

# Import our modules
from config import config
from database import init_database, SessionLocal, Article, Company, Trade, ScrapingLog
from scraper import StockTitanScraper, PRNewswireScraper, BusinessWireScraper, YahooScraper
from nlp import SentimentAnalyzer, BiotechExtractor
from trading import AlpacaClient, TradingStrategy, RiskManager

class BiotechTradingSystem:
    """Main biotech trading system orchestrator"""
    
    def __init__(self):
        self.db_session = SessionLocal()
        
        # Initialize components
        self.scrapers = {
            'stocktitan': StockTitanScraper(),
            'prnewswire': PRNewswireScraper(),
            'businesswire': BusinessWireScraper(),
            'yahoo': YahooScraper()
        }
        
        self.sentiment_analyzer = SentimentAnalyzer()
        self.biotech_extractor = BiotechExtractor()
        self.trading_strategy = TradingStrategy()
        self.risk_manager = RiskManager()
        self.alpaca_client = AlpacaClient()
        
        # System state
        self.is_running = False
        self.last_scrape_time = None
        
        logger.info("Biotech Trading System initialized")
    
    def start_system(self):
        """Start the trading system"""
        logger.info("Starting Biotech Trading System...")
        
        # Initialize database
        init_database()
        
        # Schedule scraping jobs
        self._schedule_jobs()
        
        # Reset daily counters
        self.risk_manager.reset_daily_counters()
        
        self.is_running = True
        logger.info("System started successfully!")
        
        # Start the main loop
        self._run_scheduler()
    
    def stop_system(self):
        """Stop the trading system"""
        logger.info("Stopping Biotech Trading System...")
        self.is_running = False
        
        # Close database connection
        self.db_session.close()
        
        # Close scraper drivers
        for scraper in self.scrapers.values():
            scraper.close_driver()
        
        logger.info("System stopped successfully!")
    
    def _schedule_jobs(self):
        """Schedule all periodic jobs"""
        
        # News scraping every 15 minutes during market hours
        schedule.every(config.SCRAPE_INTERVAL_MINUTES).minutes.do(self._run_news_scraping)
        
        # Process unprocessed articles every 10 minutes
        schedule.every(10).minutes.do(self._process_unprocessed_articles)
        
        # Generate trading signals every 5 minutes during market hours
        schedule.every(5).minutes.do(self._generate_trading_signals)
        
        # Execute approved trades every 2 minutes during market hours
        schedule.every(2).minutes.do(self._execute_trades)
        
        # Daily risk management reset
        schedule.every().day.at("06:00").do(self.risk_manager.reset_daily_counters)
        
        # Daily system health check
        schedule.every().day.at("07:00").do(self._daily_health_check)
        
        # Portfolio rebalancing check
        schedule.every().hour.do(self._check_portfolio_rebalancing)
        
        logger.info("Jobs scheduled successfully")
    
    def _run_scheduler(self):
        """Run the job scheduler"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _run_news_scraping(self):
        """Run news scraping from all sources"""
        if not self._is_scraping_time():
            return
        
        logger.info("Starting news scraping cycle...")
        
        total_articles = 0
        total_new = 0
        
        for source_name, scraper in self.scrapers.items():
            if not config.NEWS_SOURCES[source_name].get('enabled', True):
                continue
            
            try:
                scrape_start = datetime.now()
                
                # Scrape articles
                articles = scraper.scrape_with_retry()
                
                scrape_end = datetime.now()
                duration = (scrape_end - scrape_start).total_seconds()
                
                # Process and save articles
                new_articles = self._save_articles(articles, source_name)
                
                # Log scraping results
                self._log_scraping_result(
                    source_name, len(articles), new_articles,
                    scrape_start, scrape_end, duration
                )
                
                total_articles += len(articles)
                total_new += new_articles
                
            except Exception as e:
                logger.error(f"Error scraping {source_name}: {e}")
                self._log_scraping_result(
                    source_name, 0, 0,
                    datetime.now(), datetime.now(), 0,
                    status="error", error_message=str(e)
                )
        
        self.last_scrape_time = datetime.now()
        logger.info(f"Scraping completed: {total_new} new articles out of {total_articles} total")
    
    def _save_articles(self, articles: List[Dict[str, Any]], source: str) -> int:
        """Save scraped articles to database"""
        new_articles_count = 0
        
        for article_data in articles:
            try:
                # Check if article already exists
                existing = self.db_session.query(Article).filter(
                    Article.url == article_data.get('url')
                ).first()
                
                if existing:
                    continue
                
                # Create new article
                article = Article(
                    title=article_data.get('title', ''),
                    summary=article_data.get('summary', ''),
                    url=article_data.get('url', ''),
                    source=source,
                    published_date=article_data.get('published_date', datetime.now()),
                    is_biotech_relevant=article_data.get('is_biotech_relevant', False)
                )
                
                self.db_session.add(article)
                new_articles_count += 1
                
            except Exception as e:
                logger.error(f"Error saving article: {e}")
                continue
        
        try:
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Error committing articles: {e}")
            self.db_session.rollback()
            return 0
        
        return new_articles_count
    
    def _process_unprocessed_articles(self):
        """Process articles that haven't been analyzed yet"""
        logger.info("Processing unprocessed articles...")
        
        # Get unprocessed biotech-relevant articles
        unprocessed_articles = self.db_session.query(Article).filter(
            Article.is_processed == False,
            Article.is_biotech_relevant == True
        ).limit(50).all()  # Process in batches
        
        if not unprocessed_articles:
            return
        
        logger.info(f"Processing {len(unprocessed_articles)} articles...")
        
        for article in unprocessed_articles:
            try:
                # Extract detailed article content if URL available
                if article.url:
                    source_scraper = self.scrapers.get(article.source)
                    if source_scraper:
                        details = source_scraper.extract_article_details(article.url)
                        if details.get('full_text'):
                            article.full_text = details['full_text']
                
                # Perform sentiment analysis
                article_dict = {
                    'title': article.title,
                    'summary': article.summary,
                    'full_text': article.full_text or ''
                }
                
                sentiment_result = self.sentiment_analyzer.analyze_sentiment(
                    article_dict['full_text'] or article_dict['summary'],
                    article_dict['title']
                )
                
                # Update article with sentiment data
                article.sentiment_score = sentiment_result.get('sentiment_score', 0)
                article.sentiment_label = sentiment_result.get('sentiment_label', 'neutral')
                
                # Extract biotech information
                extracted_info = self.biotech_extractor.extract_all_info(article_dict)
                
                # Update article with extracted information
                if extracted_info.get('company_name'):
                    article.company_name = extracted_info['company_name']
                if extracted_info.get('company_ticker'):
                    article.company_ticker = extracted_info['company_ticker']
                if extracted_info.get('p_value') is not None:
                    article.p_value = extracted_info['p_value']
                if extracted_info.get('approval_status'):
                    article.approval_status = extracted_info['approval_status']
                if extracted_info.get('trial_phase'):
                    article.trial_phase = extracted_info['trial_phase']
                
                # Find or create company record
                if article.company_ticker:
                    company = self._find_or_create_company(
                        article.company_ticker,
                        article.company_name,
                        extracted_info
                    )
                    if company:
                        article.company_id = company.id
                
                # Mark as processed
                article.is_processed = True
                
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {e}")
                continue
        
        try:
            self.db_session.commit()
            logger.info(f"Successfully processed {len(unprocessed_articles)} articles")
        except Exception as e:
            logger.error(f"Error committing processed articles: {e}")
            self.db_session.rollback()
    
    def _generate_trading_signals(self):
        """Generate trading signals from recent articles"""
        if not self._is_trading_time():
            return
        
        logger.info("Generating trading signals...")
        
        # Get recent processed articles (last 4 hours)
        cutoff_time = datetime.now() - timedelta(hours=4)
        recent_articles = self.db_session.query(Article).filter(
            Article.published_date >= cutoff_time,
            Article.is_processed == True,
            Article.is_biotech_relevant == True,
            Article.company_ticker.isnot(None)
        ).all()
        
        if not recent_articles:
            logger.info("No recent articles for signal generation")
            return
        
        # Group articles by company/ticker
        articles_by_ticker = {}
        for article in recent_articles:
            ticker = article.company_ticker
            if ticker:
                if ticker not in articles_by_ticker:
                    articles_by_ticker[ticker] = []
                articles_by_ticker[ticker].append(article)
        
        signals = []
        
        for ticker, ticker_articles in articles_by_ticker.items():
            try:
                # Combine information from multiple articles
                combined_article = self._combine_articles(ticker_articles)
                
                # Generate trading signal
                signal = self.trading_strategy.analyze_article(combined_article)
                
                if signal.get('action') != 'HOLD':
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error generating signal for {ticker}: {e}")
                continue
        
        # Risk filter signals
        if signals:
            filtered_signals = self.trading_strategy.filter_signals_by_risk(signals)
            
            # Store signals for execution
            self._store_trading_signals(filtered_signals)
            
            logger.info(f"Generated {len(filtered_signals)} trading signals from {len(signals)} candidates")
        else:
            logger.info("No trading signals generated")
    
    def _execute_trades(self):
        """Execute approved trading signals"""
        if not self._is_trading_time() or not self.alpaca_client.is_connected():
            return
        
        # Check if trading is allowed by risk manager
        risk_summary = self.risk_manager.get_risk_summary()
        if not risk_summary.get('trading_allowed', False):
            logger.warning("Trading suspended by risk manager")
            return
        
        logger.info("Executing trades...")
        
        # Get pending signals (this would typically come from a signals table)
        # For now, we'll work with recent high-confidence signals
        signals = self._get_pending_signals()
        
        if not signals:
            return
        
        account_info = self.alpaca_client.get_account_info()
        if not account_info:
            logger.error("Unable to get account information")
            return
        
        executed_trades = 0
        
        for signal in signals:
            try:
                # Final risk check
                risk_checks = self.risk_manager.check_trade_limits(signal, account_info)
                
                if not risk_checks.get('approved', False):
                    failed_checks = [k for k, v in risk_checks.items() if not v and k != 'approved']
                    logger.warning(f"Trade rejected for {signal.get('symbol')}: {failed_checks}")
                    continue
                
                # Adjust position size for risk
                adjusted_signal = self.risk_manager.adjust_position_size_for_risk(
                    signal, account_info
                )
                
                # Get current price
                current_price = self.alpaca_client.get_current_price(signal['symbol'])
                if not current_price:
                    logger.warning(f"Unable to get current price for {signal['symbol']}")
                    continue
                
                # Calculate position size in shares
                portfolio_value = account_info.get('portfolio_value', 0)
                position_value = adjusted_signal['position_size'] * portfolio_value
                shares = int(position_value / current_price)
                
                if shares < 1:
                    logger.warning(f"Position size too small for {signal['symbol']}")
                    continue
                
                # Place the order
                order_result = self.alpaca_client.place_order(
                    symbol=signal['symbol'],
                    quantity=shares,
                    side=signal['action'].lower(),
                    order_type='market'
                )
                
                if order_result:
                    # Record the trade
                    trade_record = Trade(
                        ticker=signal['symbol'],
                        action=signal['action'],
                        quantity=shares,
                        price=current_price,
                        order_id=order_result.get('id'),
                        stop_loss_price=signal.get('stop_loss'),
                        take_profit_price=signal.get('target_price'),
                        trade_reason='; '.join(signal.get('reasoning', [])),
                        confidence_score=signal.get('confidence', 0),
                        company_id=self._get_company_id_by_ticker(signal['symbol'])
                    )
                    
                    self.db_session.add(trade_record)
                    
                    # Update risk manager
                    self.risk_manager.record_trade({
                        'symbol': signal['symbol'],
                        'action': signal['action'],
                        'quantity': shares,
                        'price': current_price,
                        'position_size': adjusted_signal['position_size']
                    })
                    
                    executed_trades += 1
                    logger.info(f"Executed trade: {signal['action']} {shares} shares of {signal['symbol']}")
                
            except Exception as e:
                logger.error(f"Error executing trade for {signal.get('symbol')}: {e}")
                continue
        
        try:
            self.db_session.commit()
            logger.info(f"Successfully executed {executed_trades} trades")
        except Exception as e:
            logger.error(f"Error committing trades: {e}")
            self.db_session.rollback()
    
    def _is_scraping_time(self) -> bool:
        """Check if it's time to scrape news"""
        now = datetime.now().time()
        return config.SCRAPE_START_TIME <= now <= config.SCRAPE_END_TIME
    
    def _is_trading_time(self) -> bool:
        """Check if it's time to trade"""
        if not self.alpaca_client.is_connected():
            return False
        
        market_status = self.alpaca_client.get_market_status()
        return market_status.get('is_open', False)
    
    def _log_scraping_result(self, source: str, articles_found: int, articles_new: int,
                           start_time: datetime, end_time: datetime, duration: float,
                           status: str = "success", error_message: str = None):
        """Log scraping results to database"""
        try:
            scraping_log = ScrapingLog(
                source=source,
                articles_found=articles_found,
                articles_new=articles_new,
                status=status,
                error_message=error_message,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration
            )
            
            self.db_session.add(scraping_log)
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error logging scraping result: {e}")
            self.db_session.rollback()
    
    def _find_or_create_company(self, ticker: str, name: str, extracted_info: Dict[str, Any]) -> Company:
        """Find existing company or create new one"""
        try:
            # Look for existing company
            company = self.db_session.query(Company).filter(
                Company.ticker == ticker
            ).first()
            
            if not company:
                # Create new company
                company = Company(
                    name=name or f"Company {ticker}",
                    ticker=ticker,
                    market_cap=extracted_info.get('market_cap'),
                    employee_count=extracted_info.get('employee_count'),
                    sector=extracted_info.get('sector', 'Healthcare'),
                    industry=extracted_info.get('industry', 'Biotechnology')
                )
                
                self.db_session.add(company)
                self.db_session.commit()
            
            return company
            
        except Exception as e:
            logger.error(f"Error finding/creating company {ticker}: {e}")
            self.db_session.rollback()
            return None
    
    def _combine_articles(self, articles: List[Article]) -> Dict[str, Any]:
        """Combine multiple articles for the same company"""
        if not articles:
            return {}
        
        # Use the most recent article as base
        base_article = max(articles, key=lambda a: a.published_date)
        
        combined = {
            'id': base_article.id,
            'title': base_article.title,
            'summary': base_article.summary,
            'full_text': base_article.full_text or '',
            'company_name': base_article.company_name,
            'company_ticker': base_article.company_ticker,
            'sentiment_score': base_article.sentiment_score or 0,
            'sentiment_label': base_article.sentiment_label or 'neutral',
            'p_value': base_article.p_value,
            'approval_status': base_article.approval_status,
            'trial_phase': base_article.trial_phase
        }
        
        # Aggregate sentiment from all articles
        sentiments = [a.sentiment_score for a in articles if a.sentiment_score is not None]
        if sentiments:
            combined['sentiment_score'] = sum(sentiments) / len(sentiments)
        
        # Take the most significant p-value
        p_values = [a.p_value for a in articles if a.p_value is not None]
        if p_values:
            combined['p_value'] = min(p_values)
        
        return combined
    
    def _store_trading_signals(self, signals: List[Dict[str, Any]]):
        """Store trading signals (placeholder - would typically go to a signals table)"""
        # For now, just log the signals
        for signal in signals:
            logger.info(f"Signal: {signal['action']} {signal['symbol']} "
                       f"(confidence: {signal['confidence']:.3f}, "
                       f"size: {signal['position_size']:.3f})")
    
    def _get_pending_signals(self) -> List[Dict[str, Any]]:
        """Get pending trading signals (placeholder)"""
        # This would typically query a signals table
        # For now, return empty list
        return []
    
    def _get_company_id_by_ticker(self, ticker: str) -> int:
        """Get company ID by ticker"""
        try:
            company = self.db_session.query(Company).filter(
                Company.ticker == ticker
            ).first()
            return company.id if company else None
        except:
            return None
    
    def _daily_health_check(self):
        """Perform daily system health check"""
        logger.info("Performing daily health check...")
        
        # Check database connection
        try:
            self.db_session.execute("SELECT 1")
            logger.info("Database connection: OK")
        except Exception as e:
            logger.error(f"Database connection: FAILED - {e}")
        
        # Check Alpaca connection
        if self.alpaca_client.is_connected():
            account_info = self.alpaca_client.get_account_info()
            logger.info(f"Alpaca connection: OK - Portfolio value: ${account_info.get('portfolio_value', 0):,.2f}")
        else:
            logger.error("Alpaca connection: FAILED")
        
        # Check recent scraping activity
        recent_logs = self.db_session.query(ScrapingLog).filter(
            ScrapingLog.start_time >= datetime.now() - timedelta(days=1)
        ).count()
        
        logger.info(f"Recent scraping activity: {recent_logs} scraping runs in last 24 hours")
        
        # Risk summary
        risk_summary = self.risk_manager.get_risk_summary()
        logger.info(f"Risk summary: {risk_summary}")
    
    def _check_portfolio_rebalancing(self):
        """Check if portfolio needs rebalancing"""
        if not self.alpaca_client.is_connected():
            return
        
        positions = self.alpaca_client.get_positions()
        if not positions:
            return
        
        # Calculate current allocation
        total_value = sum(pos['market_value'] for pos in positions)
        
        for position in positions:
            allocation = position['market_value'] / total_value
            
            # If any single position exceeds maximum allocation, log warning
            if allocation > config.MAX_POSITION_SIZE:
                logger.warning(f"Position {position['symbol']} exceeds max allocation: "
                             f"{allocation:.1%} > {config.MAX_POSITION_SIZE:.1%}")

def main():
    """Main entry point"""
    # Setup logging
    logger.add(
        config.LOG_FILE,
        level=config.LOG_LEVEL,
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    
    logger.info("=" * 50)
    logger.info("BIOTECH TRADING SYSTEM STARTING")
    logger.info("=" * 50)
    
    # Create and start the system
    system = BiotechTradingSystem()
    
    try:
        system.start_system()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        system.stop_system()
        logger.info("System shutdown complete")

if __name__ == "__main__":
    main()