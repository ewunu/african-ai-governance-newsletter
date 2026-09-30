"""Read-only integration check: credentials, classification, and RSS availability."""
import os
from concurrent.futures import ThreadPoolExecutor
from classifier import classify_article, MODEL_NAME
from scraper import load_sources, fetch_feed
from sheets_handler import get_existing_urls


def main():
    missing = [name for name in ('GEMINI_API_KEY', 'GOOGLE_SHEETS_CREDS', 'SHEET_ID') if not os.environ.get(name)]
    if missing:
        raise RuntimeError('Missing required secrets: ' + ', '.join(missing))
    urls = get_existing_urls()
    print(f'Sheets read succeeded; {len(urls)} existing URLs. No rows written.')
    result = classify_article('Kenya proposes an artificial intelligence governance bill', 'Parliament considers oversight, accountability and AI safety rules in Kenya.')
    if not result or result['primary_category'] != 'AI Governance' or result['relevance_score'] < 5 or not result['is_africa_related']:
        raise RuntimeError(f'Gemini integration check failed for model {MODEL_NAME}')
    print(f'Gemini classification succeeded with {MODEL_NAME}.')
    def check(feed):
        try:
            parsed = fetch_feed(feed['url'])
            return bool(parsed.get('version') or parsed.entries)
        except Exception:
            return False
    feeds = load_sources()['rss_feeds']
    with ThreadPoolExecutor(max_workers=8) as pool:
        success = sum(pool.map(check, feeds))
    print(f'RSS check: {success}/{len(feeds)} feeds reachable.')
    if not success:
        raise RuntimeError('All RSS feeds failed')
    print('Read-only integration check passed.')

if __name__ == '__main__':
    main()
