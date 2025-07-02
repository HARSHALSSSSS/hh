from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import config

Base = declarative_base()

class Article(Base):
    """News article model"""
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    full_text = Column(Text)
    url = Column(String(1000), unique=True, nullable=False)
    source = Column(String(100), nullable=False)  # stocktitan, prnewswire, etc.
    published_date = Column(DateTime, nullable=False)
    scraped_date = Column(DateTime, default=datetime.utcnow)
    
    # Extracted data
    company_name = Column(String(200))
    company_ticker = Column(String(10))
    p_value = Column(Float)
    approval_status = Column(String(50))  # approved, rejected, pending, etc.
    trial_phase = Column(String(20))  # phase_1, phase_2, phase_3
    
    # Sentiment analysis
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_label = Column(String(20))  # positive, negative, neutral
    
    # Processing flags
    is_processed = Column(Boolean, default=False)
    is_biotech_relevant = Column(Boolean, default=False)
    
    # Relationships
    company_id = Column(Integer, ForeignKey('companies.id'))
    company = relationship("Company", back_populates="articles")
    trades = relationship("Trade", back_populates="article")

class Company(Base):
    """Company information model"""
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    ticker = Column(String(10), unique=True, nullable=False)
    market_cap = Column(Float)
    employee_count = Column(Integer)
    sector = Column(String(100))
    industry = Column(String(100))
    
    # Company metrics
    pipeline_count = Column(Integer, default=0)
    clinical_trials_count = Column(Integer, default=0)
    
    # Risk assessment
    risk_score = Column(Float)  # 0-100
    volatility = Column(Float)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    articles = relationship("Article", back_populates="company")
    trades = relationship("Trade", back_populates="company")

class Trade(Base):
    """Trading activity model"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    
    # Trade details
    ticker = Column(String(10), nullable=False)
    action = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    # Order details
    order_id = Column(String(100))  # Alpaca order ID
    order_type = Column(String(20), default="market")  # market, limit, stop
    status = Column(String(20), default="pending")  # pending, filled, cancelled
    
    # Risk management
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    
    # Trade rationale
    trade_reason = Column(String(500))
    confidence_score = Column(Float)  # 0-1
    
    # Timing
    created_date = Column(DateTime, default=datetime.utcnow)
    executed_date = Column(DateTime)
    
    # P&L tracking
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Relationships
    article_id = Column(Integer, ForeignKey('articles.id'))
    article = relationship("Article", back_populates="trades")
    company_id = Column(Integer, ForeignKey('companies.id'))
    company = relationship("Company", back_populates="trades")

class TradingSession(Base):
    """Daily trading session tracking"""
    __tablename__ = 'trading_sessions'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    
    # Session metrics
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    failed_trades = Column(Integer, default=0)
    
    # P&L
    daily_pnl = Column(Float, default=0.0)
    portfolio_value_start = Column(Float)
    portfolio_value_end = Column(Float)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    
    created_date = Column(DateTime, default=datetime.utcnow)

class ScrapingLog(Base):
    """Scraping activity log"""
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True)
    source = Column(String(100), nullable=False)
    url = Column(String(1000))
    
    # Results
    articles_found = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    articles_processed = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="success")  # success, error, timeout
    error_message = Column(Text)
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)

# Database setup
engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database with tables and seed data"""
    create_tables()
    
    # Add some seed companies if database is empty
    db = SessionLocal()
    try:
        if db.query(Company).count() == 0:
            seed_companies = [
                Company(name="Moderna Inc", ticker="MRNA", sector="Healthcare", industry="Biotechnology"),
                Company(name="Pfizer Inc", ticker="PFE", sector="Healthcare", industry="Pharmaceuticals"),
                Company(name="BioNTech SE", ticker="BNTX", sector="Healthcare", industry="Biotechnology"),
                Company(name="Gilead Sciences Inc", ticker="GILD", sector="Healthcare", industry="Biotechnology"),
                Company(name="Regeneron Pharmaceuticals Inc", ticker="REGN", sector="Healthcare", industry="Biotechnology"),
                Company(name="Biogen Inc", ticker="BIIB", sector="Healthcare", industry="Biotechnology"),
                Company(name="Amgen Inc", ticker="AMGN", sector="Healthcare", industry="Biotechnology"),
                Company(name="Vertex Pharmaceuticals Inc", ticker="VRTX", sector="Healthcare", industry="Biotechnology"),
            ]
            
            for company in seed_companies:
                db.add(company)
            
            db.commit()
            print(f"Added {len(seed_companies)} seed companies to database")
    
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!")