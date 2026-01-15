#!/usr/bin/env python3
"""
African AI Governance Newsletter - Main Scraper
Scrapes RSS feeds for AI governance news with Africa relevance.
Extracts: Title, URL, Publication, Date (metadata only - no full text)
"""

import feedparser
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import time
import re

# Import local modules
from classifier import classify_article
from sheets_handler import add_to_sheet, get_existing_urls

# Constants
MAX_ENTRIES_PER_FEED = 20
REQUEST_DELAY = 0.5  # seconds between requests to be polite


def load_sources() -> Dict:
    """Load RSS feed sources and keywords from sources.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sources_path = os.path.join(script_dir, 'sources.json')
    
    with open(sources_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def clean_html(text: str) -> str:
    """Remove HTML tags from text"""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&#39;', "'")
    clean = clean.replace('&nbsp;', ' ')
    # Normalize whitespace
    clean = ' '.join(clean.split())
    return clean[:300]  # Limit snippet length


def extract_date(entry: Dict) -> str:
    """Extract and format publication date from feed entry"""
    # Try different date fields
    date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
    
    for field in date_fields:
        if entry.get(field):
            try:
                return datetime(*entry[field][:6]).strftime('%Y-%m-%d')
            except (TypeError, ValueError):
                continue
    
    # Fallback to today's date
    return datetime.now().strftime('%Y-%m-%d')


def is_potentially_relevant(title: str, snippet: str, sources: Dict) -> bool:
    """
    Quick keyword check to filter obviously irrelevant articles
    before sending to AI for classification.
    """
    keywords = sources.get('keywords_filter', {})
    
    # Combine all keyword lists
    all_keywords = (
        keywords.get('primary_keywords', []) +
        keywords.get('africa_keywords', []) +
        keywords.get('governance_bodies', []) +
        keywords.get('sector_keywords', [])
    )
    
    # Convert to lowercase for matching
    all_keywords_lower = [kw.lower() for kw in all_keywords]
    text_to_check = (title + ' ' + snippet).lower()
    
    # Check if any keyword is present
    for keyword in all_keywords_lower:
        if keyword in text_to_check:
            return True
    
    return False


def parse_single_feed(feed_config: Dict, sources: Dict, existing_urls: Set[str]) -> List[Dict]:
    """Parse a single RSS feed and return relevant articles"""
    articles = []
    feed_url = feed_config.get('url', '')
    feed_name = feed_config.get('name', 'Unknown')
    
    print(f"  Parsing: {feed_name}...")
    
    try:
        # Parse the feed
        parsed = feedparser.parse(feed_url)
        
        if parsed.bozo and not parsed.entries:
            print(f"    ⚠ Feed error for {feed_name}: {parsed.bozo_exception}")
            return articles
        
        # Process entries
        for entry in parsed.entries[:MAX_ENTRIES_PER_FEED]:
            try:
                title = clean_html(entry.get('title', ''))
                url = entry.get('link', '')
                
                # Skip if no title or URL
                if not title or not url:
                    continue
                
                # Skip if already in database
                if url in existing_urls:
                    continue
                
                # Get snippet from summary/description
                snippet = clean_html(
                    entry.get('summary', '') or 
                    entry.get('description', '') or 
                    entry.get('content', [{}])[0].get('value', '')
                )
                
                # Quick relevance check before AI classification
                if not is_potentially_relevant(title, snippet, sources):
                    continue
                
                # Extract publication date
                pub_date = extract_date(entry)
                
                articles.append({
                    'title': title,
                    'url': url,
                    'publication': feed_name,
                    'date_published': pub_date,
                    'snippet': snippet[:200],  # Limit snippet for classification
                    'region': feed_config.get('region', 'Unknown')
                })
                
            except Exception as e:
                print(f"    ⚠ Error processing entry: {e}")
                continue
        
        print(f"    ✓ Found {len(articles)} potentially relevant articles")
        
    except Exception as e:
        print(f"    ✗ Failed to parse {feed_name}: {e}")
    
    return articles


def parse_all_feeds(sources: Dict, existing_urls: Set[str]) -> List[Dict]:
    """Parse all RSS feeds and return combined articles list"""
    all_articles = []
    feeds = sources.get('rss_feeds', [])
    
    print(f"\n{'='*60}")
    print(f"SCRAPING {len(feeds)} RSS FEEDS")
    print(f"{'='*60}\n")
    
    for feed in feeds:
        articles = parse_single_feed(feed, sources, existing_urls)
        all_articles.extend(articles)
        
        # Be polite - don't hammer servers
        time.sleep(REQUEST_DELAY)
    
    # Deduplicate by URL (in case same article appears in multiple feeds)
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article['url'] not in seen_urls:
            seen_urls.add(article['url'])
            unique_articles.append(article)
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(unique_articles)} unique potentially relevant articles")
    print(f"{'='*60}\n")
    
    return unique_articles


def process_and_save_articles(articles: List[Dict], min_score: int = 5) -> Dict:
    """Classify articles and save qualifying ones to Google Sheets"""
    stats = {
        'processed': 0,
        'classified': 0,
        'saved': 0,
        'errors': 0,
        'below_threshold': 0
    }
    
    print(f"\n{'='*60}")
    print(f"CLASSIFYING {len(articles)} ARTICLES")
    print(f"{'='*60}\n")
    
    for i, article in enumerate(articles, 1):
        stats['processed'] += 1
        
        try:
            print(f"[{i}/{len(articles)}] Classifying: {article['title'][:50]}...")
            
            # Get AI classification
            classification = classify_article(
                article['title'], 
                article.get('snippet', '')
            )
            
            if classification:
                stats['classified'] += 1
                relevance_score = classification.get('relevance_score', 0)
                
                # Only save if meets minimum score threshold
                if relevance_score >= min_score:
                    # Merge classification into article
                    article.update(classification)
                    
                    # Save to Google Sheet
                    success = add_to_sheet(article)
                    
                    if success:
                        stats['saved'] += 1
                        print(f"    ✓ Saved (Score: {relevance_score}/10)")
                    else:
                        stats['errors'] += 1
                        print(f"    ✗ Failed to save to sheet")
                else:
                    stats['below_threshold'] += 1
                    print(f"    ○ Below threshold (Score: {relevance_score}/10)")
            else:
                stats['errors'] += 1
                print(f"    ✗ Classification failed")
            
            # Rate limiting for Gemini API
            time.sleep(0.5)
            
        except Exception as e:
            stats['errors'] += 1
            print(f"    ✗ Error: {e}")
    
    return stats


def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("AFRICAN AI GOVERNANCE NEWSLETTER - SCRAPER")
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*60)
    
    # Load sources configuration
    print("\n📚 Loading sources configuration...")
    sources = load_sources()
    print(f"   Loaded {len(sources.get('rss_feeds', []))} RSS feeds")
    
    # Get existing URLs to avoid duplicates
    print("\n📋 Fetching existing URLs from Google Sheet...")
    try:
        existing_urls = get_existing_urls()
        print(f"   Found {len(existing_urls)} existing entries")
    except Exception as e:
        print(f"   ⚠ Could not fetch existing URLs: {e}")
        print("   Proceeding without deduplication...")
        existing_urls = set()
    
    # Parse all RSS feeds
    articles = parse_all_feeds(sources, existing_urls)
    
    if not articles:
        print("\n✓ No new relevant articles found. Exiting.")
        return
    
    # Classify and save articles
    min_score = sources.get('relevance_scoring', {}).get('minimum_score_to_save', 5)
    stats = process_and_save_articles(articles, min_score)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Articles processed:    {stats['processed']}")
    print(f"  Successfully classified: {stats['classified']}")
    print(f"  Saved to sheet:        {stats['saved']}")
    print(f"  Below threshold:       {stats['below_threshold']}")
    print(f"  Errors:                {stats['errors']}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
