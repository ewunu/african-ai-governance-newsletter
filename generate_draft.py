#!/usr/bin/env python3
"""
African AI Governance Newsletter - Draft Generator
Generates a newsletter draft from selected articles in Google Sheets.
Run this locally after selecting articles for your newsletter.

Usage:
    export GOOGLE_SHEETS_CREDS='...'
    export SHEET_ID='...'
    python generate_draft.py
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sheets_handler import get_selected_articles, get_pending_articles, get_sheet_stats


def format_article_for_newsletter(article: Dict, include_commentary: bool = True) -> str:
    """Format a single article for the newsletter"""
    output = []
    
    # Title with link
    title = article.get('Title', 'Untitled')
    url = article.get('URL', '#')
    output.append(f"### [{title}]({url})")
    
    # Metadata line
    publication = article.get('Publication', 'Unknown')
    date = article.get('Date Published', '')
    category = article.get('Primary Category', '')
    geography = article.get('Geography', '')
    
    meta_parts = [publication]
    if date:
        meta_parts.append(date)
    if geography and geography != 'Global':
        meta_parts.append(f"📍 {geography}")
    if category:
        meta_parts.append(f"🏷️ {category}")
    
    output.append(f"*{' | '.join(meta_parts)}*")
    output.append("")
    
    # Your commentary
    commentary = article.get('Your Commentary', '').strip()
    if include_commentary and commentary:
        output.append(f"**My Take:** {commentary}")
        output.append("")
    
    return '\n'.join(output)


def group_articles_by_category(articles: List[Dict]) -> Dict[str, List[Dict]]:
    """Group articles by their primary category"""
    grouped = {}
    
    for article in articles:
        category = article.get('Primary Category', 'Other')
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(article)
    
    return grouped


def generate_newsletter_draft(articles: List[Dict], newsletter_date: str = None) -> str:
    """Generate a complete newsletter draft in Markdown format"""
    
    if not newsletter_date:
        newsletter_date = datetime.now().strftime('%B %d, %Y')
    
    # Newsletter header
    output = []
    output.append("# African AI Governance Weekly")
    output.append(f"## {newsletter_date}")
    output.append("")
    output.append("*Your weekly roundup of AI governance, ethics, and policy news from across Africa and beyond.*")
    output.append("")
    output.append("---")
    output.append("")
    
    # Introduction (customize this)
    output.append("## 👋 Hello!")
    output.append("")
    output.append("Welcome to this week's edition of the African AI Governance newsletter. Here's what caught my attention:")
    output.append("")
    
    # Group by category
    grouped = group_articles_by_category(articles)
    
    # Category order preference
    category_order = [
        'AI Governance',
        'AI Ethics', 
        'AI Audit & Assurance',
        'Responsible AI Use',
        'Other'
    ]
    
    category_emojis = {
        'AI Governance': '🏛️',
        'AI Ethics': '⚖️',
        'AI Audit & Assurance': '🔍',
        'Responsible AI Use': '✅',
        'Other': '📰'
    }
    
    # Generate sections
    for category in category_order:
        if category in grouped and grouped[category]:
            emoji = category_emojis.get(category, '📰')
            output.append(f"## {emoji} {category}")
            output.append("")
            
            for article in grouped[category]:
                output.append(format_article_for_newsletter(article))
                output.append("")
    
    # Footer
    output.append("---")
    output.append("")
    output.append("## 💭 Final Thoughts")
    output.append("")
    output.append("*[Add your weekly reflection here]*")
    output.append("")
    output.append("---")
    output.append("")
    output.append("**About this newsletter:** I curate and comment on the most important developments in AI governance, ethics, and responsible AI use, with a focus on Africa and emerging markets.")
    output.append("")
    output.append("*Questions or suggestions? Reply to this email!*")
    output.append("")
    output.append("---")
    output.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*")
    
    return '\n'.join(output)


def print_stats():
    """Print current database statistics"""
    print("\n" + "="*50)
    print("DATABASE STATISTICS")
    print("="*50)
    
    stats = get_sheet_stats()
    
    if stats:
        print(f"\nTotal Articles: {stats.get('total_articles', 0)}")
        print(f"Pending Review: {stats.get('pending', 0)}")
        print(f"Selected: {stats.get('selected', 0)}")
        print(f"Rejected: {stats.get('rejected', 0)}")
        print(f"Africa-Related: {stats.get('africa_related', 0)}")
        print(f"Average Relevance: {stats.get('avg_relevance', 0)}/10")
        
        print("\nBy Category:")
        for cat, count in stats.get('by_category', {}).items():
            print(f"  - {cat}: {count}")
    else:
        print("Could not fetch statistics")
    
    print("="*50 + "\n")


def main():
    """Main function to generate newsletter draft"""
    
    print("\n" + "="*50)
    print("AFRICAN AI GOVERNANCE NEWSLETTER")
    print("Draft Generator")
    print("="*50)
    
    # Check environment variables
    if not os.environ.get('GOOGLE_SHEETS_CREDS'):
        print("\n❌ Error: GOOGLE_SHEETS_CREDS not set")
        print("Set it with: export GOOGLE_SHEETS_CREDS='...'")
        return
    
    if not os.environ.get('SHEET_ID'):
        print("\n❌ Error: SHEET_ID not set")
        print("Set it with: export SHEET_ID='...'")
        return
    
    # Print stats
    print_stats()
    
    # Get selected articles
    print("Fetching selected articles...")
    selected = get_selected_articles()
    
    if not selected:
        print("\n⚠️ No articles marked as 'Selected' found.")
        print("\nTo create a newsletter:")
        print("1. Open your Google Sheet")
        print("2. Review pending articles")
        print("3. Change 'Review Status' to 'Selected' for articles to include")
        print("4. Add your commentary in 'Your Commentary' column")
        print("5. Run this script again")
        
        # Show pending articles as suggestion
        print("\n" + "-"*50)
        print("TOP PENDING ARTICLES (Relevance ≥ 7):")
        print("-"*50)
        
        pending = get_pending_articles(min_score=7)
        for i, article in enumerate(pending[:10], 1):
            title = article.get('Title', '')[:60]
            score = article.get('Relevance Score', 0)
            pub = article.get('Publication', '')
            print(f"{i}. [{score}/10] {title}... ({pub})")
        
        return
    
    print(f"✓ Found {len(selected)} selected articles")
    
    # Generate draft
    print("\nGenerating newsletter draft...")
    draft = generate_newsletter_draft(selected)
    
    # Save to file
    output_filename = f"newsletter_draft_{datetime.now().strftime('%Y%m%d')}.md"
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(draft)
    
    print(f"\n✅ Draft saved to: {output_filename}")
    print("\nNext steps:")
    print("1. Open the draft file and review")
    print("2. Add your 'Final Thoughts' section")
    print("3. Copy to Substack/LinkedIn/Email")
    print("4. Publish!")
    
    # Preview
    print("\n" + "="*50)
    print("DRAFT PREVIEW (first 50 lines):")
    print("="*50)
    for line in draft.split('\n')[:50]:
        print(line)
    print("\n... [truncated] ...")


if __name__ == "__main__":
    main()
