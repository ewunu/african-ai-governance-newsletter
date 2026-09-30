#!/usr/bin/env python3
"""
African AI Governance Newsletter - Google Sheets Handler
Handles reading and writing to Google Sheets database.
Uses service account authentication (free tier).
"""

import gspread
from google.oauth2.service_account import Credentials
import os
import json
from datetime import datetime
from typing import Dict, List, Set, Optional

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Cache for sheet connection
_sheet_cache = None


def get_credentials() -> Credentials:
    """Get Google service account credentials from environment variable"""
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDS')
    
    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDS environment variable not set")
    
    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in GOOGLE_SHEETS_CREDS: {e}")
    
    return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)


def get_sheet():
    """Get or create connection to Google Sheet"""
    global _sheet_cache
    
    if _sheet_cache is not None:
        return _sheet_cache
    
    sheet_id = os.environ.get('SHEET_ID')
    if not sheet_id:
        raise ValueError("SHEET_ID environment variable not set")
    
    try:
        creds = get_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)
        _sheet_cache = spreadsheet.sheet1
        return _sheet_cache
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Google Sheet: {e}")


def ensure_headers(sheet) -> None:
    """Ensure the sheet has proper headers"""
    expected_headers = [
        'Title',
        'URL', 
        'Publication',
        'Date Published',
        'Primary Category',
        'Sub-Category',
        'Geography',
        'Relevance Score',
        'Africa Related',
        'Date Scraped',
        'Review Status',
        'Your Commentary'
    ]
    
    # Check if first row has headers
    try:
        current_headers = sheet.row_values(1)
        if not current_headers or current_headers[0] != 'Title':
            # Add headers
            sheet.insert_row(expected_headers, 1)
            print("   Added headers to sheet")
    except Exception as e:
        print(f"   Warning: Could not verify headers: {e}")


def get_existing_urls() -> Set[str]:
    """Get set of URLs already in the sheet to avoid duplicates"""
    sheet = get_sheet()
    url_column = sheet.col_values(2)
    return set(url_column[1:]) if len(url_column) > 1 else set()


def add_to_sheet(article: Dict) -> bool:
    """
    Add a classified article to Google Sheet.
    
    Args:
        article: Dict containing article data and classification
    
    Returns:
        True if successful, False otherwise
    """
    try:
        sheet = get_sheet()
        
        # Ensure headers exist
        ensure_headers(sheet)
        
        # Prepare row data
        row = [
            article.get('title', '')[:500],  # Limit title length
            article.get('url', ''),
            article.get('publication', ''),
            article.get('date_published', ''),
            article.get('primary_category', 'Not Classified'),
            article.get('sub_category', ''),
            article.get('geography', ''),
            str(article.get('relevance_score', '')),
            'Yes' if article.get('is_africa_related', False) else 'No',
            datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
            'Pending',  # Review status - you'll update this manually
            ''  # Your commentary - you'll add this manually
        ]
        
        # Append row to sheet
        sheet.append_row(row, value_input_option='RAW')
        
        return True
        
    except Exception as e:
        print(f"   Error adding to sheet: {e}")
        return False


def add_multiple_to_sheet(articles: List[Dict]) -> Dict:
    """
    Add multiple articles to Google Sheet in batch.
    More efficient than adding one at a time.
    
    Args:
        articles: List of article dicts
    
    Returns:
        Dict with success/failure counts
    """
    results = {'success': 0, 'failed': 0}
    
    if not articles:
        return results
    
    try:
        sheet = get_sheet()
        ensure_headers(sheet)
        
        # Prepare all rows
        rows = []
        for article in articles:
            row = [
                article.get('title', '')[:500],
                article.get('url', ''),
                article.get('publication', ''),
                article.get('date_published', ''),
                article.get('primary_category', 'Not Classified'),
                article.get('sub_category', ''),
                article.get('geography', ''),
                str(article.get('relevance_score', '')),
                'Yes' if article.get('is_africa_related', False) else 'No',
                datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
                'Pending',
                ''
            ]
            rows.append(row)
        
        # Batch append (more efficient)
        sheet.append_rows(rows, value_input_option='RAW')
        results['success'] = len(rows)
        
    except Exception as e:
        print(f"   Batch add failed: {e}")
        results['failed'] = len(articles)
    
    return results


def get_pending_articles(min_score: int = 7) -> List[Dict]:
    """
    Get articles pending review with score >= min_score.
    Useful for generating newsletter draft.
    
    Args:
        min_score: Minimum relevance score to include
    
    Returns:
        List of article dicts
    """
    try:
        sheet = get_sheet()
        
        # Get all records
        records = sheet.get_all_records()
        
        # Filter for pending and high relevance
        pending = [
            r for r in records 
            if r.get('Review Status') == 'Pending' 
            and int(r.get('Relevance Score', 0) or 0) >= min_score
        ]
        
        # Sort by relevance score (descending)
        pending.sort(key=lambda x: int(x.get('Relevance Score', 0) or 0), reverse=True)
        
        return pending
        
    except Exception as e:
        print(f"   Error fetching pending articles: {e}")
        return []


def get_selected_articles(date_filter: Optional[str] = None) -> List[Dict]:
    """
    Get articles marked as 'Selected' for newsletter.
    
    Args:
        date_filter: Optional date string (YYYY-MM-DD) to filter by
    
    Returns:
        List of selected article dicts
    """
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        selected = [r for r in records if r.get('Review Status') == 'Selected']
        
        if date_filter:
            selected = [
                r for r in selected 
                if r.get('Date Published', '').startswith(date_filter)
            ]
        
        return selected
        
    except Exception as e:
        print(f"   Error fetching selected articles: {e}")
        return []


def update_article_status(url: str, status: str, commentary: str = '') -> bool:
    """
    Update an article's review status and commentary.
    
    Args:
        url: Article URL (unique identifier)
        status: New status ('Pending', 'Selected', 'Rejected')
        commentary: Optional commentary to add
    
    Returns:
        True if successful
    """
    try:
        sheet = get_sheet()
        
        # Find the row with this URL
        url_cell = sheet.find(url, in_column=2)
        
        if url_cell:
            row_num = url_cell.row
            
            # Update status (column K = 11)
            sheet.update_cell(row_num, 11, status)
            
            # Update commentary if provided (column L = 12)
            if commentary:
                sheet.update_cell(row_num, 12, commentary)
            
            return True
        
        return False
        
    except Exception as e:
        print(f"   Error updating article: {e}")
        return False


def get_sheet_stats() -> Dict:
    """Get statistics about the sheet contents"""
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        stats = {
            'total_articles': len(records),
            'pending': sum(1 for r in records if r.get('Review Status') == 'Pending'),
            'selected': sum(1 for r in records if r.get('Review Status') == 'Selected'),
            'rejected': sum(1 for r in records if r.get('Review Status') == 'Rejected'),
            'africa_related': sum(1 for r in records if r.get('Africa Related') == 'Yes'),
            'by_category': {},
            'avg_relevance': 0
        }
        
        # Count by category
        for record in records:
            cat = record.get('Primary Category', 'Unknown')
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
        
        # Calculate average relevance
        scores = [int(r.get('Relevance Score', 0) or 0) for r in records]
        if scores:
            stats['avg_relevance'] = round(sum(scores) / len(scores), 1)
        
        return stats
        
    except Exception as e:
        print(f"   Error getting stats: {e}")
        return {}


# Test function
if __name__ == "__main__":
    print("Testing Google Sheets connection...")
    
    try:
        sheet = get_sheet()
        print(f"✓ Connected to sheet: {sheet.title}")
        
        urls = get_existing_urls()
        print(f"✓ Found {len(urls)} existing URLs")
        
        stats = get_sheet_stats()
        print(f"✓ Stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nCheck that:")
        print("  1. GOOGLE_SHEETS_CREDS is set with valid JSON")
        print("  2. SHEET_ID is set with your spreadsheet ID")
        print("  3. Sheet is shared with service account email")
