#!/usr/bin/env python3
"""
African AI Governance Newsletter - AI Classifier
Uses Google Gemini API (free tier) to classify articles.
"""

import google.generativeai as genai
import os
import json
import re
from typing import Dict, Optional

# Configure Gemini API
api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

# Classification prompt template
CLASSIFICATION_PROMPT = """You are an AI governance content classifier specializing in African contexts.

Given an article's TITLE and SNIPPET, classify it for relevance to African AI governance.

INPUT:
Title: {title}
Snippet: {snippet}

OUTPUT REQUIREMENTS:
Return ONLY valid JSON with no markdown formatting, no code blocks, no extra text.
The JSON must have exactly these fields:

{{
  "primary_category": "<one of: AI Governance | AI Ethics | AI Audit & Assurance | Responsible AI Use | Not Relevant>",
  "sub_category": "<specific sub-category>",
  "geography": "<country, region, or 'Global'>",
  "relevance_score": <integer 1-10>,
  "is_africa_related": <true or false>,
  "key_themes": ["<theme1>", "<theme2>"]
}}

CLASSIFICATION RULES:

PRIMARY CATEGORIES:
- "AI Governance": National AI strategies, regulatory frameworks, policy proposals, international agreements
- "AI Ethics": Bias & fairness, privacy & data protection, algorithmic accountability, human rights
- "AI Audit & Assurance": Standards & certifications (ISO 42001), risk assessment, compliance, third-party audits
- "Responsible AI Use": Sector applications, best practices, case studies, implementation guides
- "Not Relevant": Articles that don't relate to AI governance, ethics, audit, or responsible use

RELEVANCE SCORING:
- 9-10: Directly about AI governance/ethics/audit in Africa (mentions specific African country, AU, African org)
- 7-8: AI governance/ethics topic with clear implications for Africa or developing nations
- 5-6: Global AI governance that could be relevant to African context
- 3-4: General AI news with minimal governance angle
- 1-2: Not relevant to AI governance or Africa

AFRICA RELATED - Set to true if:
- Article mentions any African country by name
- Article mentions African regional bodies (AU, ECOWAS, SADC, EAC)
- Article is from an African publication
- Article discusses developing nations, Global South, or emerging markets in AI context

SUB-CATEGORIES by Primary:
AI Governance: National AI Strategies, Regulatory Frameworks, Policy Proposals, International Agreements, Government Initiatives
AI Ethics: Bias & Fairness, Privacy & Data Protection, Algorithmic Accountability, Human Rights, Consent & Transparency
AI Audit & Assurance: Standards & Certifications, Risk Assessment, Compliance Requirements, Impact Assessments
Responsible AI Use: Sector Applications, Best Practices, Case Studies, Failures & Lessons, Implementation Guides

Remember: Return ONLY the JSON object, nothing else."""


def parse_json_response(response_text: str) -> Optional[Dict]:
    """Parse JSON from Gemini response, handling various formats"""
    if not response_text:
        return None
    
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    
    if text.endswith('```'):
        text = text[:-3]
    
    text = text.strip()
    
    # Try to find JSON object in the text
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        text = json_match.group()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        print(f"    Response was: {text[:200]}...")
        return None


def validate_classification(classification: Dict) -> Dict:
    """Validate and clean up classification result"""
    # Required fields with defaults
    defaults = {
        'primary_category': 'Not Relevant',
        'sub_category': 'Unknown',
        'geography': 'Global',
        'relevance_score': 1,
        'is_africa_related': False,
        'key_themes': []
    }
    
    # Merge with defaults
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
    
    # Ensure key_themes is a list
    if not isinstance(result.get('key_themes'), list):
        result['key_themes'] = []
    
    return result


def classify_article(title: str, snippet: str) -> Optional[Dict]:
    """
    Classify an article using Google Gemini API.
    
    Args:
        title: Article title
        snippet: Article summary/snippet (max ~200 chars)
    
    Returns:
        Classification dict or None if failed
    """
    if not api_key:
        print("    ⚠ GEMINI_API_KEY not set")
        return None
    
    if not title:
        print("    ⚠ No title provided")
        return None
    
    try:
        # Initialize model
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Format prompt
        prompt = CLASSIFICATION_PROMPT.format(
            title=title,
            snippet=snippet or "No snippet available"
        )
        
        # Generate classification
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Low temperature for consistent classification
                max_output_tokens=500
            )
        )
        
        # Parse response
        if response and response.text:
            classification = parse_json_response(response.text)
            
            if classification:
                return validate_classification(classification)
        
        return None
        
    except Exception as e:
        print(f"    ⚠ Gemini API error: {e}")
        return None


def classify_article_fallback(title: str, snippet: str, sources_config: Dict) -> Dict:
    """
    Fallback keyword-based classification when API is unavailable.
    Uses rules from sources.json for basic scoring.
    """
    text = (title + ' ' + (snippet or '')).lower()
    
    keywords = sources_config.get('keywords_filter', {})
    primary_kw = keywords.get('primary_keywords', [])
    africa_kw = keywords.get('africa_keywords', [])
    
    # Count keyword matches
    primary_matches = sum(1 for kw in primary_kw if kw.lower() in text)
    africa_matches = sum(1 for kw in africa_kw if kw.lower() in text)
    
    # Calculate score
    if primary_matches > 0 and africa_matches > 0:
        score = min(9, 5 + primary_matches + africa_matches)
    elif primary_matches > 0:
        score = min(6, 3 + primary_matches)
    else:
        score = 2
    
    # Determine category based on keywords in title
    category = 'Not Relevant'
    if any(kw in text for kw in ['governance', 'regulation', 'policy', 'strategy', 'framework']):
        category = 'AI Governance'
    elif any(kw in text for kw in ['ethics', 'bias', 'fairness', 'privacy', 'rights']):
        category = 'AI Ethics'
    elif any(kw in text for kw in ['audit', 'assurance', 'standard', 'compliance', 'iso']):
        category = 'AI Audit & Assurance'
    elif any(kw in text for kw in ['responsible', 'implementation', 'use case', 'application']):
        category = 'Responsible AI Use'
    elif primary_matches > 0:
        category = 'AI Governance'  # Default for AI-related content
    
    return {
        'primary_category': category,
        'sub_category': 'Auto-classified',
        'geography': 'Africa' if africa_matches > 0 else 'Global',
        'relevance_score': score,
        'is_africa_related': africa_matches > 0,
        'key_themes': []
    }


# Test function
if __name__ == "__main__":
    # Test classification
    test_title = "Kenya launches national AI strategy focusing on ethical deployment"
    test_snippet = "The Kenyan government unveiled its comprehensive AI strategy, emphasizing responsible use and data protection."
    
    print("Testing classifier...")
    result = classify_article(test_title, test_snippet)
    
    if result:
        print("\nClassification Result:")
        print(json.dumps(result, indent=2))
    else:
        print("\nClassification failed - check API key")
