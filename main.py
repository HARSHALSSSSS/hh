#!/usr/bin/env python3
"""
Biotech News Trading System
A comprehensive system that scrapes biotech news, analyzes sentiment,
extracts key information, and makes automated trading decisions.
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta, time as dt_time, timezone
from typing import List, Dict, Any
from loguru import logger
from sqlalchemy.orm import sessionmaker
import random
from sqlalchemy import and_
import os
import sys
import pytz

# Import our modules
from config import config
from database import init_database, SessionLocal, Article, Company, Trade, ScrapingLog
from scraper import StockTitanScraper, PRNewswireScraper, BusinessWireScraper, YahooScraper
from nlp import SentimentAnalyzer, BiotechExtractor
from trading import AlpacaClient, TradingStrategy, RiskManager
from notifications import email_notifier

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
        """Schedule all periodic tasks with smart 15-minute intervals and time window buffering"""
        logger.info("Setting up job scheduling with smart time window system...")
        
        # Main scraping every 15 minutes with small random offset
        def smart_scraping():
            if self._is_scraping_time():
                # Small random offset to avoid exact timing conflicts
                offset = random.randint(0, config.SCRAPE_OFFSET_SECONDS)
                if offset > 0:
                    time.sleep(offset)
                self._run_news_scraping()
        
        # Remove interval-based scheduling and replace with fixed quarter-hour marks
        # Schedule scraping at exact quarter-hour marks (:00, :15, :30, :45)
        fixed_quarter_marks = [":00", ":15", ":30", ":45"]

        for mark in fixed_quarter_marks:
            schedule.every().hour.at(mark).do(smart_scraping)
        
        # Enhanced processing schedule - every 5 minutes to process any articles we found
        schedule.every(5).minutes.do(
            lambda: self._process_unprocessed_articles() if self._is_scraping_time() else None
        )
        
        # Signal generation every 3 minutes during trading hours  
        schedule.every(3).minutes.do(
            lambda: self._generate_trading_signals() if self._is_trading_time() else None
        )
        
        # Trade execution every 2 minutes during trading hours
        schedule.every(2).minutes.do(
            lambda: self._execute_trades() if self._is_trading_time() else None
        )
        
        # Health check twice daily
        schedule.every(12).hours.do(self._daily_health_check)
        
        # Portfolio rebalancing check every hour during trading
        schedule.every().hour.do(
            lambda: self._check_portfolio_rebalancing() if self._is_trading_time() else None
        )
        
        logger.info(f"✅ Scheduled: {config.SCRAPE_INTERVAL_MINUTES}-minute intervals with smart time buffering")
        logger.info(f"⏰ Time window: ±{config.ARTICLE_TIME_BUFFER_MINUTES} minutes from scraping time")
    
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
        """Save scraped articles to database with smart time window filtering"""
        new_articles_count = 0
        current_time = datetime.now()
        new_articles_for_email = []  # Track articles for email notification
        
        logger.info(f"🔍 Processing {len(articles)} articles from {source} with smart time filtering...")
        
        for article_data in articles:
            try:
                # Parse article published time with timezone handling
                published_date = article_data.get('published_date', current_time)
                if isinstance(published_date, str):
                    try:
                        published_date = datetime.strptime(published_date, "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            published_date = datetime.strptime(published_date, "%Y-%m-%d")
                        except:
                            published_date = current_time
                
                # Ensure both datetimes are timezone-naive for comparison
                if published_date.tzinfo is not None:
                    published_date = published_date.replace(tzinfo=None)
                if current_time.tzinfo is not None:
                    current_time = current_time.replace(tzinfo=None)
                
                # Check if article is within our smart time window
                if not self._is_article_in_time_window(published_date, current_time):
                    continue  # Skip articles outside time window
                
                # Check article age (don't process very old articles)
                age_hours = (current_time - published_date).total_seconds() / 3600
                if age_hours > config.MAX_ARTICLE_AGE_HOURS:
                    continue  # Skip old articles
                
                # Calculate relevance score and filter by threshold
                relevance_score = self._calculate_article_relevance_score(article_data)
                if relevance_score < config.ARTICLE_RELEVANCE_SCORE_THRESHOLD:
                    continue  # Skip low-relevance articles
                
                # Enhanced duplicate check within time window
                cutoff_time = current_time - timedelta(hours=config.DUPLICATE_CHECK_HOURS)
                existing = self.db_session.query(Article).filter(
                    and_(
                        Article.url == article_data.get('url'),
                        Article.published_date >= cutoff_time
                    )
                ).first()
                
                if existing:
                    continue  # Skip duplicates
                
                # Create new article with relevance score
                article = Article(
                    title=article_data.get('title', ''),
                    summary=article_data.get('summary', ''),
                    url=article_data.get('url', ''),
                    source=source,
                    published_date=published_date,
                    is_biotech_relevant=True  # Set to True for all articles now that filtering is disabled
                )
                
                # Store relevance score in the article (if your Article model supports it)
                if hasattr(article, 'relevance_score'):
                    article.relevance_score = relevance_score
                
                self.db_session.add(article)
                new_articles_count += 1
                
                # Add to email notification list with relevance score
                article_data['relevance_score'] = relevance_score
                new_articles_for_email.append(article_data)
                
                # Log high-relevance articles
                if relevance_score >= 0.8:
                    logger.info(f"🎯 High-relevance article: {article_data.get('title', '')[:50]}... (score: {relevance_score:.2f})")
                    
                    # Send immediate high-relevance alert
                    try:
                        email_notifier.send_high_relevance_alert(article_data)
                    except Exception as e:
                        logger.error(f"Failed to send high-relevance email alert: {e}")
                
            except Exception as e:
                logger.error(f"Error processing article: {e}")
                continue
        
        try:
            self.db_session.commit()
            logger.info(f"💾 Saved {new_articles_count} relevant articles from {source} (time window: ±{config.ARTICLE_TIME_BUFFER_MINUTES}min)")
            
            # Send email notification for new articles (if any)
            if new_articles_for_email:
                try:
                    email_notifier.send_new_articles_alert(
                        new_articles_for_email, source, new_articles_count
                    )
                    logger.info(f"📧 Email alert sent for {new_articles_count} new articles from {source}")
                except Exception as e:
                    logger.error(f"Failed to send new articles email alert: {e}")
                    
        except Exception as e:
            logger.error(f"Error committing articles: {e}")
            self.db_session.rollback()
            return 0
        
        return new_articles_count
    
    def _process_unprocessed_articles(self):
        """Process articles that haven't been analyzed yet"""
        logger.info("Processing unprocessed articles...")
        
        # Get unprocessed articles (removed biotech filter for broader processing)
        unprocessed_articles = self.db_session.query(Article).filter(
            Article.is_processed == False
            # Removed is_biotech_relevant filter to process all articles
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
            # Removed is_biotech_relevant check for broader signal generation
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
            
            # Send email alerts for trading signals
            for signal in filtered_signals:
                try:
                    email_notifier.send_trading_signal_alert(signal)
                    logger.info(f"📧 Trading signal email sent for {signal.get('symbol')}")
                except Exception as e:
                    logger.error(f"Failed to send trading signal email alert: {e}")
            
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
                    
                    # Send email alert for executed trade
                    try:
                        trade_data = {
                            'symbol': signal['symbol'],
                            'action': signal['action'],
                            'quantity': shares,
                            'price': current_price,
                            'order_id': order_result.get('id'),
                            'stop_loss_price': signal.get('stop_loss'),
                            'take_profit_price': signal.get('target_price'),
                            'trade_reason': '; '.join(signal.get('reasoning', [])),
                            'confidence_score': signal.get('confidence', 0)
                        }
                        email_notifier.send_trade_execution_alert(trade_data)
                        logger.info(f"📧 Trade execution email sent for {signal['symbol']}")
                    except Exception as e:
                        logger.error(f"Failed to send trade execution email alert: {e}")
                    
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

    def _is_article_in_time_window(self, article_time: datetime, scrape_time: datetime) -> bool:
        """Check if article was published within the smart time window"""
        if not config.ENABLE_SMART_TIME_FILTERING:
            return True
        
        # Calculate time difference
        time_diff = abs((article_time - scrape_time).total_seconds() / 60)  # in minutes
        
        # Article is valid if published within our lookback window
        return time_diff <= config.ARTICLE_LOOKBACK_WINDOW_MINUTES

    def _calculate_article_relevance_score(self, article: Dict[str, Any]) -> float:
        """Calculate relevance score for biotech articles with keyword matching"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        content = article.get('content', '').lower()
        
        combined_text = f"{title} {summary} {content}"
        
        # High-priority biotech keywords (higher weight)
        high_priority_keywords = [
            'fda approval', 'clinical trial', 'phase iii', 'phase 3', 'breakthrough therapy',
            'drug approval', 'biotech', 'pharmaceutical', 'p-value', 'significant result',
            'gene therapy', 'immunotherapy', 'cancer treatment', 'orphan drug',
            'fast track', 'priority review', 'biologics', 'vaccine', 'antibody'
        ]
        
        # Medium-priority keywords
        medium_priority_keywords = [
            'phase ii', 'phase 2', 'phase i', 'phase 1', 'clinical study',
            'therapeutic', 'treatment', 'medical device', 'diagnostic',
            'oncology', 'cardiology', 'neurology', 'rare disease'
        ]
        
        # Company and regulatory keywords
        regulatory_keywords = [
            'fda', 'ema', 'regulatory', 'approval', 'clearance', 'designation',
            'pipeline', 'clinical development', 'trial results', 'endpoint'
        ]
        
        score = 0.0
        
        # Count high-priority keywords (weight: 0.3 each)
        for keyword in high_priority_keywords:
            if keyword in combined_text:
                score += 0.3
        
        # Count medium-priority keywords (weight: 0.2 each)
        for keyword in medium_priority_keywords:
            if keyword in combined_text:
                score += 0.2
        
        # Count regulatory keywords (weight: 0.15 each)
        for keyword in regulatory_keywords:
            if keyword in combined_text:
                score += 0.15
        
        # Boost score if multiple biotech terms appear
        biotech_terms_count = sum(1 for kw in ['biotech', 'pharmaceutical', 'clinical', 'drug', 'therapy'] 
                                 if kw in combined_text)
        if biotech_terms_count >= 2:
            score += 0.2
        
        # Cap score at 1.0
        return min(score, 1.0)

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