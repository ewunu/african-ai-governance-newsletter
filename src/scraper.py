#!/usr/bin/env python3
"""
African AI Governance Newsletter - Main Scraper
Scrapes RSS feeds for AI governance news with Africa relevance.
Extracts: Title, URL, Publication, Date (metadata only - no full text)

Optimized for free tier: aggressive pre-filtering to reduce API calls.
"""

import feedparser
import requests
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import time
import re

# Import local modules
from classifier import classify_article, classify_article_fallback
from sheets_handler import add_to_sheet, get_existing_urls

# Constants
MAX_ENTRIES_PER_FEED = 10  # Reduced from 20
REQUEST_DELAY = 0.5
MAX_ARTICLES_TO_CLASSIFY = 50  # Hard limit for free tier

# Sources that are highly relevant (prioritize these)
PRIORITY_SOURCES = [
    'techcabal', 'disrupt', 'itnewsafrica', 'techpoint',
    'unesco', 'oecd', 'brookings', 'algorithm watch'
]


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
    clean = re.sub(r'<[^>]+>', '', text)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<')
    clean = clean.replace('&gt;', '>').replace('&quot;', '"')
    clean = clean.replace('&#39;', "'").replace('&nbsp;', ' ')
    clean = ' '.join(clean.split())
    return clean[:300]


def extract_date(entry: Dict) -> str:
    """Extract and format publication date from feed entry"""
    date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
    
    for field in date_fields:
        if entry.get(field):
            try:
                return datetime(*entry[field][:6]).strftime('%Y-%m-%d')
            except (TypeError, ValueError):
                continue
    
    return datetime.now().strftime('%Y-%m-%d')


def is_recent(date_str: str, days: int = 7) -> bool:
    """Check if article is from the last N days"""
    try:
        article_date = datetime.strptime(date_str, '%Y-%m-%d')
        cutoff = datetime.now() - timedelta(days=days)
        return article_date >= cutoff
    except:
        return True  # If we can't parse, assume it's recent


def calculate_keyword_score(title: str, snippet: str, sources: Dict) -> Tuple[int, bool, bool]:
    """
    Calculate keyword relevance score.
    Returns: (score, is_ai_related, is_africa_related)
    
    Score:
    - 0: No relevant keywords
    - 1-2: Weak match (1 keyword)
    - 3-4: Moderate match (AI or Africa keywords)
    - 5+: Strong match (AI + Africa keywords)
    """
    text = (title + ' ' + snippet).lower()
    
    # AI/Governance keywords
    ai_keywords = [
        'ai governance', 'ai regulation', 'ai policy', 'ai ethics',
        'artificial intelligence', 'responsible ai', 'ai audit',
        'algorithmic', 'machine learning regulation', 'ai framework',
        'ai strategy', 'ai law', 'data protection', 'ai bias',
        'ai fairness', 'ai safety', 'ai risk', 'ai standard'
    ]
    
    # Africa keywords
    africa_keywords = [
        'africa', 'african', 'nigeria', 'nigerian', 'kenya', 'kenyan',
        'south africa', 'egypt', 'egyptian', 'ghana', 'ghanaian',
        'rwanda', 'ethiopia', 'morocco', 'tanzania', 'uganda',
        'senegal', 'cameroon', 'african union', 'ecowas', 'sadc'
    ]
    
    keywords = sources.get('keywords_filter', {})
    ai_keywords = list(set(ai_keywords + keywords.get('primary_keywords', [])))
    africa_keywords = list(set(africa_keywords + keywords.get('africa_keywords', [])))
    matches = lambda kw: re.search(r'(?<!\w)' + re.escape(kw.lower()) + r'(?!\w)', text) is not None

    # Count matches
    ai_matches = sum(1 for kw in ai_keywords if matches(kw))
    africa_matches = sum(1 for kw in africa_keywords if matches(kw))
    
    is_ai_related = ai_matches > 0
    is_africa_related = africa_matches > 0
    
    # Calculate score
    if ai_matches >= 2 and africa_matches >= 1:
        score = 6  # Strong: Multiple AI keywords + Africa
    elif ai_matches >= 1 and africa_matches >= 1:
        score = 5  # Good: AI + Africa
    elif ai_matches >= 2:
        score = 4  # Moderate: Strong AI focus
    elif africa_matches >= 1 and ('tech' in text or 'digital' in text):
        score = 3  # Moderate: Africa + tech context
    elif ai_matches >= 1:
        score = 2  # Weak: Single AI keyword
    else:
        score = 0  # No match
    
    return score, is_ai_related, is_africa_related


def should_skip_article(title: str) -> bool:
    """
    Quick check to skip obviously irrelevant articles.
    Returns True if article should be skipped.
    """
    title_lower = title.lower()
    
    # Skip patterns (newsletters, promotions, etc.)
    skip_patterns = [
        'daily digest', 'weekly roundup', 'newsletter',
        'sponsored', 'advertisement', 'partner content',
        'podcast:', 'video:', '[video]', '[podcast]',
        'job:', 'hiring:', 'careers',
        'price:', 'discount', 'sale', 'promo',
        'horoscope', 'weather', 'sports score',
        'recipe', 'lifestyle', 'fashion week',
        'celebrity', 'entertainment news'
    ]
    
    for pattern in skip_patterns:
        if pattern in title_lower:
            return True
    
    # Skip if title is too short (likely not a real article)
    if len(title) < 20:
        return True
    
    # Skip emoji-heavy titles (often newsletters)
    emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', title))
    if emoji_count >= 3:
        return True
    
    return False


def fetch_feed(url: str):
    response = requests.get(
        url, timeout=(5, 15),
        headers={'User-Agent': 'AfricanAIGovernanceNewsletter/1.0 (RSS reader)'},
    )
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if not parsed.get('version') and not parsed.entries:
        raise ValueError('Response is not a valid RSS/Atom feed')
    return parsed


def parse_single_feed(feed_config: Dict, sources: Dict, existing_urls: Set[str]) -> List[Dict]:
    """Parse a single RSS feed and return relevant articles"""
    articles = []
    feed_url = feed_config.get('url', '')
    feed_name = feed_config.get('name', 'Unknown')
    
    # Check if this is a priority source
    is_priority = any(p in feed_name.lower() for p in PRIORITY_SOURCES)
    
    print(f"  {'⭐' if is_priority else '○'} Parsing: {feed_name}...")
    
    try:
        parsed = fetch_feed(feed_url)
        feed_config['_fetch_ok'] = True
        
        if parsed.bozo and not parsed.entries:
            print(f"    ⚠ Feed error: {str(parsed.bozo_exception)[:50]}")
            return articles
        
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
                
                # Skip obviously irrelevant articles
                if should_skip_article(title):
                    continue
                
                # Get snippet
                snippet = clean_html(
                    entry.get('summary', '') or 
                    entry.get('description', '') or ''
                )
                
                # Extract date and check recency
                pub_date = extract_date(entry)
                if not is_recent(pub_date, days=7):
                    continue
                
                # Calculate keyword score
                score, is_ai, is_africa = calculate_keyword_score(title, snippet, sources)
                
                # Filter based on score
                # Priority sources: accept score >= 2
                # Other sources: accept score >= 4 (need both AI + Africa signals)
                min_score = 2 if is_priority else 4
                
                if score >= min_score:
                    articles.append({
                        'title': title,
                        'url': url,
                        'publication': feed_name,
                        'date_published': pub_date,
                        'snippet': snippet[:200],
                        'region': feed_config.get('region', 'Unknown'),
                        'keyword_score': score,
                        'is_ai_related': is_ai,
                        'is_africa_related': is_africa,
                        'is_priority_source': is_priority
                    })
                    
            except Exception as e:
                continue
        
        if articles:
            print(f"    ✓ Found {len(articles)} candidates")
        
    except Exception as e:
        print(f"    ✗ Failed: {str(e)[:50]}")
    
    return articles


def parse_all_feeds(sources: Dict, existing_urls: Set[str]) -> List[Dict]:
    """Parse all RSS feeds and return combined articles list"""
    all_articles = []
    feeds = sources.get('rss_feeds', [])
    
    print(f"\n{'='*60}")
    print(f"SCRAPING {len(feeds)} RSS FEEDS")
    print(f"{'='*60}\n")
    
    # Bound network waits and fetch independent feeds concurrently.
    for feed in feeds:
        feed['_fetch_ok'] = False
    with ThreadPoolExecutor(max_workers=8) as pool:
        for articles in pool.map(lambda feed: parse_single_feed(feed, sources, existing_urls), feeds):
            all_articles.extend(articles)
    successful = sum(feed.get('_fetch_ok', False) for feed in feeds)
    print(f'Feed health: {successful}/{len(feeds)} feeds fetched successfully')
    if not successful:
        raise RuntimeError('All RSS feeds failed; refusing to report a successful empty scrape')
    
    # Deduplicate by URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article['url'] not in seen_urls:
            seen_urls.add(article['url'])
            unique_articles.append(article)
    
    # Sort by keyword score (highest first), then by priority source
    unique_articles.sort(
        key=lambda x: (x.get('keyword_score', 0), x.get('is_priority_source', False)),
        reverse=True
    )
    
    # Limit to MAX_ARTICLES_TO_CLASSIFY
    if len(unique_articles) > MAX_ARTICLES_TO_CLASSIFY:
        print(f"\n⚠ Found {len(unique_articles)} articles, limiting to top {MAX_ARTICLES_TO_CLASSIFY}")
        unique_articles = unique_articles[:MAX_ARTICLES_TO_CLASSIFY]
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(unique_articles)} articles to classify")
    print(f"{'='*60}\n")
    
    return unique_articles


def process_and_save_articles(articles: List[Dict], min_score: int = 5) -> Dict:
    """Classify articles and save qualifying ones to Google Sheets"""
    stats = {
        'processed': 0,
        'classified': 0,
        'saved': 0,
        'errors': 0,
        'below_threshold': 0,
        'skipped_fallback': 0
    }
    
    print(f"\n{'='*60}")
    print(f"CLASSIFYING {len(articles)} ARTICLES")
    print(f"(This will take ~{len(articles) * 13 // 60} minutes due to rate limits)")
    print(f"{'='*60}\n")
    
    for i, article in enumerate(articles, 1):
        stats['processed'] += 1
        
        try:
            title_preview = article['title'][:50]
            kw_score = article.get('keyword_score', 0)
            
            print(f"[{i}/{len(articles)}] [KW:{kw_score}] {title_preview}...")
            
            # For very high keyword scores from priority sources, use fallback
            # to save API calls
            if kw_score >= 5 and article.get('is_priority_source'):
                classification = classify_article_fallback(
                    article['title'], 
                    article.get('snippet', '')
                )
                stats['skipped_fallback'] += 1
                print(f"    ⚡ Fast-tracked (Score: {classification['relevance_score']}/10)")
            else:
                # Use AI classification
                classification = classify_article(
                    article['title'], 
                    article.get('snippet', '')
                )
            
            if classification:
                stats['classified'] += 1
                relevance_score = classification.get('relevance_score', 0)
                
                if relevance_score >= min_score:
                    article.update(classification)
                    success = add_to_sheet(article)
                    
                    if success:
                        stats['saved'] += 1
                        print(f"    ✓ Saved (Score: {relevance_score}/10)")
                    else:
                        stats['errors'] += 1
                        print(f"    ✗ Failed to save")
                else:
                    stats['below_threshold'] += 1
                    print(f"    ○ Below threshold (Score: {relevance_score}/10)")
            else:
                stats['errors'] += 1
                print(f"    ✗ Classification failed")
            
        except Exception as e:
            stats['errors'] += 1
            print(f"    ✗ Error: {str(e)[:50]}")
    
    return stats


def main():
    """Main execution function"""
    start_time = time.time()
    
    print("\n" + "="*60)
    print("AFRICAN AI GOVERNANCE NEWSLETTER - SCRAPER")
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*60)
    
    # Load sources
    print("\n📚 Loading sources...")
    sources = load_sources()
    print(f"   Loaded {len(sources.get('rss_feeds', []))} RSS feeds")
    
    # Get existing URLs
    print("\n📋 Checking existing entries...")
    existing_urls = get_existing_urls()
    print(f'   Found {len(existing_urls)} existing entries')

    # Parse feeds
    articles = parse_all_feeds(sources, existing_urls)
    
    if not articles:
        print("\n✓ No new relevant articles found. Exiting.")
        return
    
    # Classify and save
    min_score = sources.get('relevance_scoring', {}).get('minimum_score_to_save', 5)
    stats = process_and_save_articles(articles, min_score)
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Articles processed:     {stats['processed']}")
    print(f"  Successfully classified: {stats['classified']}")
    print(f"  Fast-tracked (no API):  {stats['skipped_fallback']}")
    print(f"  Saved to sheet:         {stats['saved']}")
    print(f"  Below threshold:        {stats['below_threshold']}")
    print(f"  Errors:                 {stats['errors']}")
    print(f"  Total time:             {elapsed/60:.1f} minutes")
    print("="*60 + "\n")
    if stats['errors']:
        raise RuntimeError(f"Scrape incomplete: {stats['errors']} classification/save errors")


if __name__ == "__main__":
    main()
