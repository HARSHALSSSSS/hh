#!/usr/bin/env python3
"""
Email Notification System
Sends real-time email alerts for biotech news articles and trading signals
"""

import smtplib
import ssl
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger
from config import config

class EmailNotifier:
    """Email notification system for biotech trading alerts"""
    
    def __init__(self):
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.email_user = config.EMAIL_USER
        self.email_password = config.EMAIL_PASSWORD
        self.notification_emails = config.NOTIFICATION_EMAILS
        
        # Email templates
        self.templates = {
            'new_articles': 'New Biotech Articles Alert',
            'high_relevance': 'High-Relevance Biotech News',
            'trading_signal': 'Trading Signal Generated',
            'trade_executed': 'Trade Executed',
            'risk_alert': 'Risk Management Alert',
            'system_health': 'System Health Report'
        }
    
    def is_configured(self) -> bool:
        """Check if email notifications are properly configured"""
        return bool(
            self.email_user and 
            self.email_password and 
            self.notification_emails
        )
    
    def send_email(self, subject: str, body: str, html_body: str = None, 
                   priority: str = "normal") -> bool:
        """Send email notification"""
        if not self.is_configured():
            logger.warning("Email notifications not configured - skipping email")
            return False
        
        try:
            # Create message
            msg = MimeMultipart('alternative')
            msg['From'] = self.email_user
            msg['To'] = ', '.join(self.notification_emails)
            msg['Subject'] = f"[Biotech Trader] {subject}"
            
            # Set priority
            if priority == "high":
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            elif priority == "low":
                msg['X-Priority'] = '5'
                msg['X-MSMail-Priority'] = 'Low'
            
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S EST")
            body = f"Alert Time: {timestamp}\n\n{body}"
            
            # Attach text version
            text_part = MimeText(body, 'plain')
            msg.attach(text_part)
            
            # Attach HTML version if provided
            if html_body:
                html_part = MimeText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_new_articles_alert(self, articles: List[Dict[str, Any]], 
                               source: str, total_new: int) -> bool:
        """Send alert for newly fetched articles"""
        if not articles:
            return False
        
        subject = f"🔔 {total_new} New Biotech Articles from {source.title()}"
        
        # Create text body
        body_lines = [
            f"📰 NEW BIOTECH ARTICLES DETECTED",
            f"Source: {source.title()}",
            f"Total New Articles: {total_new}",
            f"High-Relevance Articles: {len([a for a in articles if a.get('relevance_score', 0) >= 0.8])}",
            "",
            "📋 ARTICLE SUMMARIES:",
            "=" * 60
        ]
        
        for i, article in enumerate(articles[:5], 1):  # Show top 5
            relevance = article.get('relevance_score', 0)
            body_lines.extend([
                f"{i}. {article.get('title', 'No title')[:80]}...",
                f"   📊 Relevance Score: {relevance:.2f}",
                f"   📅 Published: {article.get('published_date', 'Unknown')}",
                f"   🔗 URL: {article.get('url', 'No URL')[:100]}",
                ""
            ])
        
        if len(articles) > 5:
            body_lines.append(f"... and {len(articles) - 5} more articles")
        
        body = "\n".join(body_lines)
        
        # Create HTML body
        html_body = self._create_articles_html(articles, source, total_new)
        
        return self.send_email(subject, body, html_body, priority="normal")
    
    def send_high_relevance_alert(self, article: Dict[str, Any]) -> bool:
        """Send alert for high-relevance biotech articles"""
        relevance_score = article.get('relevance_score', 0)
        
        if relevance_score < 0.8:
            return False
        
        subject = f"🎯 High-Relevance Biotech News: {article.get('title', 'Unknown')[:50]}..."
        
        # Create detailed body
        body_lines = [
            f"🚨 HIGH-RELEVANCE BIOTECH ARTICLE DETECTED",
            f"Relevance Score: {relevance_score:.2f}/1.00",
            "",
            f"📰 Title: {article.get('title', 'No title')}",
            f"📝 Summary: {article.get('summary', 'No summary')[:300]}...",
            f"📅 Published: {article.get('published_date', 'Unknown')}",
            f"📍 Source: {article.get('source', 'Unknown').title()}",
            f"🔗 URL: {article.get('url', 'No URL')}",
            "",
            "🔍 EXTRACTED INFORMATION:",
            f"• Company: {article.get('company_name', 'Not detected')}",
            f"• Ticker: {article.get('company_ticker', 'Not detected')}",
            f"• P-Value: {article.get('p_value', 'Not detected')}",
            f"• Trial Phase: {article.get('trial_phase', 'Not detected')}",
            f"• Approval Status: {article.get('approval_status', 'Not detected')}",
            "",
            "📈 SENTIMENT ANALYSIS:",
            f"• Sentiment Score: {article.get('sentiment_score', 'Not analyzed')}",
            f"• Sentiment Label: {article.get('sentiment_label', 'Not analyzed')}",
        ]
        
        body = "\n".join(body_lines)
        
        return self.send_email(subject, body, priority="high")
    
    def send_trading_signal_alert(self, signal: Dict[str, Any]) -> bool:
        """Send alert for generated trading signals"""
        subject = f"📊 Trading Signal: {signal.get('action', 'UNKNOWN')} {signal.get('symbol', 'UNKNOWN')}"
        
        body_lines = [
            f"🚀 TRADING SIGNAL GENERATED",
            "",
            f"📊 Signal Details:",
            f"• Symbol: {signal.get('symbol', 'Unknown')}",
            f"• Action: {signal.get('action', 'Unknown')}",
            f"• Confidence: {signal.get('confidence', 0):.2%}",
            f"• Position Size: {signal.get('position_size', 0):.2%} of portfolio",
            f"• Target Price: ${signal.get('target_price', 0):.2f}",
            f"• Stop Loss: ${signal.get('stop_loss', 0):.2f}",
            "",
            f"📰 Based on Article: {signal.get('article_title', 'Unknown')[:100]}...",
            "",
            f"🎯 Reasoning:",
        ]
        
        reasoning = signal.get('reasoning', [])
        for reason in reasoning[:5]:
            body_lines.append(f"• {reason}")
        
        body_lines.extend([
            "",
            f"⚠️ Risk Assessment:",
            f"• Risk Score: {signal.get('risk_score', 0):.2f}/10",
            f"• Market Cap: ${signal.get('market_cap', 0):,.0f}",
            f"• Volatility: {signal.get('volatility', 0):.2%}",
        ])
        
        body = "\n".join(body_lines)
        
        return self.send_email(subject, body, priority="high")
    
    def send_trade_execution_alert(self, trade: Dict[str, Any]) -> bool:
        """Send alert for executed trades"""
        subject = f"✅ Trade Executed: {trade.get('action', 'UNKNOWN')} {trade.get('symbol', 'UNKNOWN')}"
        
        body_lines = [
            f"✅ TRADE EXECUTED SUCCESSFULLY",
            "",
            f"📊 Trade Details:",
            f"• Symbol: {trade.get('symbol', 'Unknown')}",
            f"• Action: {trade.get('action', 'Unknown')}",
            f"• Quantity: {trade.get('quantity', 0):,} shares",
            f"• Price: ${trade.get('price', 0):.2f}",
            f"• Total Value: ${trade.get('quantity', 0) * trade.get('price', 0):,.2f}",
            f"• Order ID: {trade.get('order_id', 'Unknown')}",
            "",
            f"🎯 Trade Setup:",
            f"• Stop Loss: ${trade.get('stop_loss_price', 0):.2f}",
            f"• Take Profit: ${trade.get('take_profit_price', 0):.2f}",
            f"• Confidence: {trade.get('confidence_score', 0):.2%}",
            "",
            f"📰 Trade Reason: {trade.get('trade_reason', 'Not specified')[:200]}...",
        ]
        
        body = "\n".join(body_lines)
        
        return self.send_email(subject, body, priority="high")
    
    def send_risk_alert(self, risk_data: Dict[str, Any]) -> bool:
        """Send alert for risk management issues"""
        subject = f"⚠️ Risk Alert: {risk_data.get('alert_type', 'Unknown Risk')}"
        
        body_lines = [
            f"⚠️ RISK MANAGEMENT ALERT",
            "",
            f"Alert Type: {risk_data.get('alert_type', 'Unknown')}",
            f"Severity: {risk_data.get('severity', 'Unknown')}",
            f"Description: {risk_data.get('description', 'No description')}",
            "",
            f"📊 Current Risk Metrics:",
            f"• Portfolio Risk Score: {risk_data.get('portfolio_risk_score', 0):.2f}/10",
            f"• Daily Loss: {risk_data.get('daily_loss_pct', 0):.2%}",
            f"• Position Concentration: {risk_data.get('max_position_pct', 0):.2%}",
            f"• Trading Allowed: {'Yes' if risk_data.get('trading_allowed', False) else 'No'}",
            "",
            f"🛠️ Recommended Action: {risk_data.get('recommended_action', 'Review portfolio')}",
        ]
        
        body = "\n".join(body_lines)
        
        return self.send_email(subject, body, priority="high")
    
    def send_system_health_report(self, health_data: Dict[str, Any]) -> bool:
        """Send daily system health report"""
        subject = f"📈 Daily System Health Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        body_lines = [
            f"📈 BIOTECH TRADING SYSTEM - DAILY HEALTH REPORT",
            f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"📰 News Scraping Summary:",
            f"• Articles Scraped Today: {health_data.get('articles_scraped', 0):,}",
            f"• High-Relevance Articles: {health_data.get('high_relevance_articles', 0):,}",
            f"• Successful Scrapes: {health_data.get('successful_scrapes', 0):,}",
            f"• Failed Scrapes: {health_data.get('failed_scrapes', 0):,}",
            "",
            f"💰 Trading Summary:",
            f"• Signals Generated: {health_data.get('signals_generated', 0):,}",
            f"• Trades Executed: {health_data.get('trades_executed', 0):,}",
            f"• Daily P&L: ${health_data.get('daily_pnl', 0):,.2f}",
            f"• Portfolio Value: ${health_data.get('portfolio_value', 0):,.2f}",
            "",
            f"⚡ System Performance:",
            f"• Uptime: {health_data.get('uptime_hours', 0):.1f} hours",
            f"• Error Rate: {health_data.get('error_rate', 0):.2%}",
            f"• Average Response Time: {health_data.get('avg_response_time', 0):.2f}s",
            f"• System Status: {health_data.get('system_status', 'Unknown')}",
        ]
        
        body = "\n".join(body_lines)
        
        return self.send_email(subject, body, priority="low")
    
    def _create_articles_html(self, articles: List[Dict[str, Any]], 
                             source: str, total_new: int) -> str:
        """Create HTML formatted email for articles"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h2 style="color: #2c3e50;">🔔 New Biotech Articles from {source.title()}</h2>
            <p><strong>Total New Articles:</strong> {total_new}</p>
            <p><strong>High-Relevance Articles:</strong> {len([a for a in articles if a.get('relevance_score', 0) >= 0.8])}</p>
            
            <hr style="border: 1px solid #bdc3c7;">
            
            <h3 style="color: #34495e;">📋 Article Details:</h3>
        """
        
        for i, article in enumerate(articles[:5], 1):
            relevance = article.get('relevance_score', 0)
            color = "#27ae60" if relevance >= 0.8 else "#f39c12" if relevance >= 0.6 else "#95a5a6"
            
            html += f"""
            <div style="border: 1px solid #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <h4 style="color: #2c3e50; margin: 0 0 10px 0;">{i}. {article.get('title', 'No title')}</h4>
                <p style="color: #7f8c8d; margin: 5px 0;"><strong>Relevance Score:</strong> 
                   <span style="color: {color}; font-weight: bold;">{relevance:.2f}</span></p>
                <p style="color: #7f8c8d; margin: 5px 0;"><strong>Published:</strong> {article.get('published_date', 'Unknown')}</p>
                <p style="margin: 10px 0;">{article.get('summary', 'No summary available')[:200]}...</p>
                <a href="{article.get('url', '#')}" style="color: #3498db; text-decoration: none;">Read Full Article →</a>
            </div>
            """
        
        if len(articles) > 5:
            html += f"<p style='color: #7f8c8d; font-style: italic;'>... and {len(articles) - 5} more articles</p>"
        
        html += """
            <hr style="border: 1px solid #bdc3c7; margin: 20px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                This is an automated alert from your Biotech Trading System.<br>
                Configure notification settings in config.py
            </p>
        </body>
        </html>
        """
        
        return html

    # ------------------------------------------------------------------
    # NEW: DETAILED ARTICLE EMAIL (one e-mail per processed article)
    # ------------------------------------------------------------------
    def send_article_details_alert(self, article: Dict[str, Any]):
        """Send a single e-mail containing all extracted details for one article."""
        if not config.ENABLE_EMAIL_NOTIFICATIONS or not config.SEND_NEW_ARTICLES_ALERTS:
            return

        title   = article.get('title', 'No title')
        url     = article.get('url', '')
        pubdate = article.get('published_date')
        pubdate = pubdate.strftime("%Y-%m-%d %H:%M") if pubdate else "N/A"

        subject = f"[Biotech Trader] 📰 Article Details: {title[:60]}"

        body_lines = [
            f"📰  TITLE: {title}",
            f"📅  Published: {pubdate}",
            f"🔗  URL: {url}",
            "",
            "------ EXTRACTED INFORMATION ------",
            f"🏢 Company Name : {article.get('company_name', 'N/A')}",
            f"💲 Ticker       : {article.get('company_ticker', 'N/A')}",
            f"📊 Sentiment    : {article.get('sentiment_label', 'neutral')} (score {article.get('sentiment_score', 0):.2f})",
            f"📈 P-Value      : {article.get('p_value', 'N/A')}",
            f"🧪 Trial Phase  : {article.get('trial_phase', 'N/A')}",
            f"✅ Approval     : {article.get('approval_status', 'N/A')}",
            "",
            "------ SUMMARY ------",
            article.get('summary', 'No summary provided')[:1000]  # cap length
        ]

        body = "\n".join(body_lines)
        self.send_email(subject, body)

# Global instance
email_notifier = EmailNotifier()