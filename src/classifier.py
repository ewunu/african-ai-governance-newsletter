#!/usr/bin/env python3
"""
African AI Governance Newsletter - AI Classifier
Uses Google Gemini API (free tier) to classify articles.
Updated with rate limiting and better error handling.
"""

import google.generativeai as genai
import os
import json
import re
import time
from typing import Dict, Optional

# Configure Gemini API
api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

# Rate limiting: 3 requests per minute (safety buffer from 5/min limit)
REQUESTS_PER_MINUTE = 3
REQUEST_INTERVAL = 60 / REQUESTS_PER_MINUTE  # 20 seconds between requests

# Track last request time
_last_request_time = 0

# Classification prompt template - kept concise for reliable JSON output
CLASSIFICATION_PROMPT = """Classify this article for African AI governance relevance.

Title: {title}
Snippet: {snippet}

Return ONLY this JSON (no other text, no markdown):
{{"primary_category":"<AI Governance|AI Ethics|AI Audit & Assurance|Responsible AI Use|Not Relevant>","sub_category":"<specific type>","geography":"<country or Global>","relevance_score":<1-10>,"is_africa_related":<true|false>}}

Scoring: 9-10=directly about AI governance in Africa, 7-8=AI governance relevant to Africa, 5-6=general AI governance, 1-4=not relevant.
"""


def wait_for_rate_limit():
    """Enforce rate limiting between API calls"""
    global _last_request_time
    
    now = time.time()
    elapsed = now - _last_request_time
    
    if elapsed < REQUEST_INTERVAL:
        wait_time = REQUEST_INTERVAL - elapsed
        print(f"    ⏳ Rate limiting: waiting {wait_time:.1f}s...")
        time.sleep(wait_time)
    
    _last_request_time = time.time()


def parse_json_response(response_text: str) -> Optional[Dict]:
    """Parse JSON from Gemini response, handling various formats"""
    if not response_text:
        return None
    
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]
    
    text = text.strip()
    
    # Try to find JSON object in the text
    json_match = re.search(r'\{[^{}]*\}', text)
    if json_match:
        text = json_match.group()
    
    # Fix common JSON issues
    text = text.replace('\n', ' ')
    text = re.sub(r',\s*}', '}', text)  # Remove trailing commas
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        print(f"    Response was: {text[:100]}...")
        return None


def validate_classification(classification: Dict) -> Dict:
    """Validate and clean up classification result"""
    defaults = {
        'primary_category': 'Not Relevant',
        'sub_category': 'Unknown',
        'geography': 'Global',
        'relevance_score': 1,
        'is_africa_related': False,
    }
    
    result = {**defaults, **classification}
    
    # Validate primary_category
    valid_categories = [
        'AI Governance', 
        'AI Ethics', 
        'AI Audit & Assurance', 
        'Responsible AI Use', 
        'Not Relevant'
    ]
    if result['primary_category'] not in valid_categories:
        result['primary_category'] = 'Not Relevant'
    
    # Validate relevance_score
    try:
        score = int(result['relevance_score'])
        result['relevance_score'] = max(1, min(10, score))
    except (ValueError, TypeError):
        result['relevance_score'] = 1
    
    # Validate is_africa_related
    result['is_africa_related'] = bool(result.get('is_africa_related', False))
    
    return result


def classify_article(title: str, snippet: str, max_retries: int = 2) -> Optional[Dict]:
    """
    Classify an article using Google Gemini API with rate limiting.
    
    Args:
        title: Article title
        snippet: Article summary/snippet (max ~200 chars)
        max_retries: Number of retries on rate limit errors
    
    Returns:
        Classification dict or None if failed
    """
    if not api_key:
        print("    ⚠ GEMINI_API_KEY not set")
        return None
    
    if not title:
        print("    ⚠ No title provided")
        return None
    
    # Clean inputs
    title = title[:200]  # Limit title length
    snippet = (snippet or "")[:200]  # Limit snippet length
    
    for attempt in range(max_retries + 1):
        try:
            # Enforce rate limiting
            wait_for_rate_limit()
            
            # Initialize model - using gemini-2.0-flash-lite for free tier
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            
            # Format prompt
            prompt = CLASSIFICATION_PROMPT.format(
                title=title,
                snippet=snippet
            )
            
            # Generate classification with safety settings relaxed
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=200,  # Keep response short
                )
            )
            
            # Check if response has content
            if not response or not response.parts:
                print(f"    ⚠ Empty response from Gemini")
                return None
            
            # Get text from response
            response_text = response.text if hasattr(response, 'text') else None
            
            if response_text:
                classification = parse_json_response(response_text)
                
                if classification:
                    return validate_classification(classification)
            
            return None
            
        except Exception as e:
            error_str = str(e)
            
            # Handle rate limit errors
            if '429' in error_str or 'quota' in error_str.lower():
                if attempt < max_retries:
                    wait_time = 15 * (attempt + 1)  # 15s, 30s, etc.
                    print(f"    ⚠ Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    ⚠ Rate limit exceeded after {max_retries + 1} attempts")
                    return None
            
            # Handle content blocked
            if 'finish_reason' in error_str or 'blocked' in error_str.lower():
                print(f"    ⚠ Content blocked by Gemini safety filters")
                return None
            
            print(f"    ⚠ Gemini API error: {error_str[:100]}")
            return None
    
    return None


# Fallback keyword-based classification
def classify_article_fallback(title: str, snippet: str) -> Dict:
    """
    Fallback keyword-based classification when API is unavailable.
    """
    text = (title + ' ' + (snippet or '')).lower()
    
    africa_keywords = [
        'africa', 'african', 'nigeria', 'kenya', 'south africa', 'egypt',
        'ghana', 'rwanda', 'ethiopia', 'morocco', 'tanzania', 'uganda'
    ]
    
    ai_gov_keywords = [
        'ai governance', 'ai regulation', 'ai policy', 'ai ethics',
        'responsible ai', 'ai audit', 'ai framework', 'ai strategy'
    ]
    
    africa_match = any(kw in text for kw in africa_keywords)
    ai_gov_match = any(kw in text for kw in ai_gov_keywords)
    
    if ai_gov_match and africa_match:
        score = 8
        category = 'AI Governance'
    elif ai_gov_match:
        score = 5
        category = 'AI Governance'
    elif africa_match and 'ai' in text:
        score = 4
        category = 'Responsible AI Use'
    else:
        score = 2
        category = 'Not Relevant'
    
    return {
        'primary_category': category,
        'sub_category': 'Auto-classified (fallback)',
        'geography': 'Africa' if africa_match else 'Global',
        'relevance_score': score,
        'is_africa_related': africa_match,
    }
