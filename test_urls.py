#!/usr/bin/env python3
"""
Real-time URL testing and validation script
Tests all news source URLs and validates biotech content
"""

import sys
import time
import requests
from datetime import datetime
from config import config
from scraper import StockTitanScraper, PRNewswireScraper, BusinessWireScraper, YahooScraper

def test_url_accessibility():
    """Test basic URL accessibility"""
    print(f"\n{'='*60}")
    print(f"URL ACCESSIBILITY TEST - {datetime.now()}")
    print(f"{'='*60}")
    
    test_results = {}
    
    for source_name, source_config in config.NEWS_SOURCES.items():
        if not source_config.get('enabled', True):
            continue
            
        print(f"\n🔍 Testing {source_name.upper()}:")
        
        urls_to_test = []
        if 'biotech_url' in source_config:
            urls_to_test.append(('Biotech URL', source_config['biotech_url']))
        if 'rss_url' in source_config:
            urls_to_test.append(('RSS URL', source_config['rss_url']))
        if 'clinical_trials_url' in source_config:
            urls_to_test.append(('Clinical Trials URL', source_config['clinical_trials_url']))
        
        source_results = {}
        
        for url_type, url in urls_to_test:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                status = response.status_code
                size = len(response.content)
                
                if status == 200:
                    print(f"  ✅ {url_type}: {status} | Size: {size:,} bytes")
                    source_results[url_type] = 'SUCCESS'
                else:
                    print(f"  ❌ {url_type}: {status} | Size: {size:,} bytes")
                    source_results[url_type] = f'ERROR_{status}'
                    
            except Exception as e:
                print(f"  ❌ {url_type}: ERROR | {str(e)[:50]}...")
                source_results[url_type] = f'EXCEPTION'
        
        test_results[source_name] = source_results
        time.sleep(1)  # Be respectful
    
    return test_results

def test_scraper_functionality():
    """Test actual article scraping functionality"""
    print(f"\n{'='*60}")
    print(f"SCRAPER FUNCTIONALITY TEST - {datetime.now()}")
    print(f"{'='*60}")
    
    scrapers = {
        'stocktitan': StockTitanScraper(),
        'prnewswire': PRNewswireScraper(),
        'businesswire': BusinessWireScraper(),
        'yahoo': YahooScraper()
    }
    
    scraping_results = {}
    
    for scraper_name, scraper in scrapers.items():
        print(f"\n🔍 Testing {scraper_name.upper()} scraper:")
        
        try:
            start_time = time.time()
            articles = scraper.scrape_articles()
            end_time = time.time()
            
            duration = end_time - start_time
            article_count = len(articles)
            
            if article_count > 0:
                print(f"  ✅ Scraped {article_count} articles in {duration:.2f}s")
                
                # Test a sample article for biotech relevance
                sample_article = articles[0] if articles else None
                if sample_article:
                    print(f"  📰 Sample: {sample_article.get('title', 'No title')[:60]}...")
                    print(f"  🔗 URL: {sample_article.get('url', 'No URL')}")
                    print(f"  🧬 Biotech relevant: {sample_article.get('is_biotech_relevant', False)}")
                
                scraping_results[scraper_name] = {
                    'status': 'SUCCESS',
                    'articles': article_count,
                    'duration': duration,
                    'sample_title': sample_article.get('title', '') if sample_article else ''
                }
            else:
                print(f"  ⚠️  No articles found (this might be normal during off-hours)")
                scraping_results[scraper_name] = {
                    'status': 'NO_ARTICLES',
                    'articles': 0,
                    'duration': duration
                }
                
        except Exception as e:
            print(f"  ❌ Scraping failed: {str(e)[:100]}...")
            scraping_results[scraper_name] = {
                'status': 'ERROR',
                'error': str(e)[:100]
            }
        
        time.sleep(2)  # Be respectful between scraper tests
    
    return scraping_results

def test_biotech_content_detection():
    """Test biotech content detection in scraped articles"""
    print(f"\n{'='*60}")
    print(f"BIOTECH CONTENT DETECTION TEST - {datetime.now()}")
    print(f"{'='*60}")
    
    # Test with sample biotech content
    test_articles = [
        {
            'title': 'FDA Approves New Cancer Immunotherapy Drug',
            'summary': 'Phase III clinical trial shows significant p-value of 0.001 for new biotech treatment',
            'content': 'biotechnology pharmaceutical clinical trial FDA approval cancer treatment'
        },
        {
            'title': 'Tech Company Launches New App',
            'summary': 'Mobile application for food delivery service',
            'content': 'technology mobile app food delivery startup'
        },
        {
            'title': 'Breakthrough Gene Therapy Shows Promise',
            'summary': 'CRISPR-based treatment for genetic disorders passes Phase II trial',
            'content': 'gene therapy CRISPR biotech pharmaceutical trial'
        }
    ]
    
    biotech_detection_results = []
    
    # Use StockTitan scraper for biotech detection
    scraper = StockTitanScraper()
    
    for i, article in enumerate(test_articles, 1):
        is_biotech = scraper.is_biotech_relevant(article['title'], article['summary'])
        expected_biotech = i != 2  # Second article should not be biotech
        
        print(f"  📰 Article {i}: {article['title'][:50]}...")
        print(f"     🧬 Detected as biotech: {is_biotech}")
        print(f"     ✅ Correct detection: {is_biotech == expected_biotech}")
        
        biotech_detection_results.append({
            'title': article['title'],
            'detected': is_biotech,
            'expected': expected_biotech,
            'correct': is_biotech == expected_biotech
        })
    
    accuracy = sum(1 for r in biotech_detection_results if r['correct']) / len(biotech_detection_results)
    print(f"\n  🎯 Biotech detection accuracy: {accuracy:.1%}")
    
    return biotech_detection_results

def main():
    """Run comprehensive URL and scraping tests"""
    print("🚀 BIOTECH TRADING SYSTEM - URL & SCRAPING VALIDATION")
    print("=" * 60)
    
    # Test 1: URL accessibility
    url_results = test_url_accessibility()
    
    # Test 2: Scraper functionality  
    scraper_results = test_scraper_functionality()
    
    # Test 3: Biotech content detection
    biotech_results = test_biotech_content_detection()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY REPORT - {datetime.now()}")
    print(f"{'='*60}")
    
    print("\n📊 URL ACCESSIBILITY:")
    for source, results in url_results.items():
        success_count = sum(1 for r in results.values() if r == 'SUCCESS')
        total_count = len(results)
        print(f"  {source}: {success_count}/{total_count} URLs working")
    
    print("\n📊 SCRAPER FUNCTIONALITY:")
    for source, results in scraper_results.items():
        status = results.get('status', 'UNKNOWN')
        article_count = results.get('articles', 0)
        print(f"  {source}: {status} ({article_count} articles)")
    
    print("\n📊 BIOTECH DETECTION:")
    accuracy = sum(1 for r in biotech_results if r['correct']) / len(biotech_results)
    print(f"  Accuracy: {accuracy:.1%}")
    
    # Overall health check
    working_urls = sum(
        sum(1 for r in results.values() if r == 'SUCCESS')
        for results in url_results.values()
    )
    total_urls = sum(len(results) for results in url_results.values())
    
    working_scrapers = sum(
        1 for results in scraper_results.values()
        if results.get('status') in ['SUCCESS', 'NO_ARTICLES']
    )
    total_scrapers = len(scraper_results)
    
    print(f"\n🎯 OVERALL SYSTEM HEALTH:")
    print(f"  URLs working: {working_urls}/{total_urls} ({working_urls/total_urls:.1%})")
    print(f"  Scrapers working: {working_scrapers}/{total_scrapers} ({working_scrapers/total_scrapers:.1%})")
    print(f"  Biotech detection: {accuracy:.1%}")
    
    if working_urls >= total_urls * 0.75 and working_scrapers >= total_scrapers * 0.75:
        print("\n✅ SYSTEM READY FOR PRODUCTION!")
    else:
        print("\n⚠️  SYSTEM NEEDS ATTENTION - Some components failing")
    
    return {
        'url_results': url_results,
        'scraper_results': scraper_results,
        'biotech_results': biotech_results
    }

if __name__ == "__main__":
    try:
        results = main()
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        sys.exit(1)