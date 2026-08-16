#!/usr/bin/env python3
"""Test script to verify document extraction fix."""

import os
import json
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup

SEC_CIK_BY_SYMBOL = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "TSLA": "0001318605",
    "NVDA": "0001045810",
    "NFLX": "0001065280",
    "INTC": "0000050863",
    "AMD": "0000002488",
    "QCOM": "0000804328",
}

def _extract_item_section(text: str, item_numbers: list) -> str:
    """Extract a specific item section from 10-K text."""
    for item_num in item_numbers:
        item_patterns = [
            f'item {item_num}[a-z]?\\.',
            f'item {item_num}[a-z]? ',
            f'item {item_num}',
        ]

        for pattern in item_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                pos_start = match.start()
                pos_end = match.end()

                next_item_match = re.search(r'item\s+\d+', text[pos_end:], re.IGNORECASE)
                if next_item_match:
                    section_end = pos_end + next_item_match.start()
                else:
                    section_end = len(text)

                section = text[pos_start:section_end].strip()

                has_substantive_content = any(keyword in section.lower() for keyword in
                    ['risk', 'factor', 'market', 'business', 'operation', 'financial', 'competition',
                     'following', 'could', 'may', 'material', 'adverse'])
                sufficient_length = len(section) > 700

                if has_substantive_content and sufficient_length:
                    return section[:5000]

    return ""

def fetch_latest_risk_section(symbol: str, as_of_date: str = None):
    """Fetch and extract real text from SEC EDGAR 10-K document (Item 1A: Risk Factors or Item 7: MD&A)."""
    cik = SEC_CIK_BY_SYMBOL.get(symbol.upper())
    if not cik:
        return {
            "source": "none",
            "symbol": symbol.upper(),
            "text": "No SEC CIK mapping available for this symbol.",
            "available": False,
        }

    headers = {
        "User-Agent": "FinaAgentBot/1.0 (contact@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }

    base_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        response = requests.get(base_url, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        recent = payload.get('filings', {}).get('recent', {})
        forms = recent.get('form') or []
        accession_numbers = recent.get('accessionNumber') or []
        filing_dates = recent.get('filingDate') or []
        primary_documents = recent.get('primaryDocument') or []

        cutoff = None
        if as_of_date:
            cutoff = pd.Timestamp(as_of_date)

        candidate_idx = None
        for idx, form in enumerate(forms):
            if str(form).upper() == '10-K':
                filing_date = filing_dates[idx] if idx < len(filing_dates) else None
                if cutoff and filing_date:
                    if pd.Timestamp(filing_date) >= cutoff:
                        continue
                candidate_idx = idx
                break

        if candidate_idx is None or candidate_idx >= len(accession_numbers):
            return {
                "source": "sec-edgar",
                "symbol": symbol.upper(),
                "text": "No 10-K filing accession could be resolved from the SEC submissions API.",
                "available": False,
            }

        accession = accession_numbers[candidate_idx]
        primary_doc = primary_documents[candidate_idx] if candidate_idx < len(primary_documents) else None
        filing_date = filing_dates[candidate_idx] if candidate_idx < len(filing_dates) else None

        if not primary_doc:
            return {
                "source": "sec-edgar",
                "symbol": symbol.upper(),
                "text": "No primary document found for this 10-K filing.",
                "available": False,
            }

        footer = accession.replace('-', '')
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{footer}/{primary_doc}"

        doc_response = requests.get(doc_url, headers=headers, timeout=30)
        if doc_response.status_code != 200:
            return {
                "source": "sec-edgar",
                "symbol": symbol.upper(),
                "text": f"Failed to fetch document (HTTP {doc_response.status_code}).",
                "available": False,
            }

        soup = BeautifulSoup(doc_response.text, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text)

        section_text = _extract_item_section(text, ['1a', '1A'])
        if not section_text:
            section_text = _extract_item_section(text, ['7', '7a', '7A'])

        if not section_text:
            section_text = text[:3000]

        return {
            "source": "sec-edgar",
            "symbol": symbol.upper(),
            "text": section_text,
            "available": True,
            "form": forms[candidate_idx] if candidate_idx < len(forms) else "10-K",
            "filing_date": filing_date,
            "document_url": doc_url,
        }
    except Exception as e:
        return {
            "source": "sec-edgar",
            "symbol": symbol.upper(),
            "text": f"SEC lookup failed: {type(e).__name__}: {e}",
            "available": False,
        }

def test_document_extraction():
    """Test that we're now extracting real document text instead of keywords."""

    print("=" * 80)
    print("DOCUMENT EXTRACTION FIX TEST")
    print("=" * 80)
    print()

    symbol = "AAPL"

    print(f"Fetching and extracting real 10-K text for {symbol}...")
    print()

    result = fetch_latest_risk_section(symbol)

    print(f"Result Status: {result.get('available')}")
    print(f"Source: {result.get('source')}")
    print(f"Form: {result.get('form')}")
    print(f"Filing Date: {result.get('filing_date')}")
    if result.get('document_url'):
        print(f"Document URL: {result.get('document_url')}")
    print()

    text = result.get('text', '')
    print(f"Extracted Text Length: {len(text)} characters")
    print()

    if result.get('available'):
        print("EXTRACTED TEXT (first 1500 chars):")
        print("-" * 80)
        print(text[:1500])
        print("...")
        print("-" * 80)
        print()

        # Show statistics about the extracted text
        words = text.split()
        sentences = text.split('.')
        print("TEXT STATISTICS:")
        print(f"  Word count: {len(words)}")
        print(f"  Sentence count (approx): {len(sentences)}")
        print(f"  Average words per sentence: {len(words) / max(len(sentences), 1):.1f}")
        print()

        # Check if it looks like real filing content
        if any(keyword in text.lower() for keyword in ['risk', 'factor', 'business', 'market', 'competition']):
            print("✓ Text appears to be REAL filing content (contains financial/business terminology)")
        else:
            print("✗ Text may not be real content (no business keywords found)")

        if len(text) > 500:
            print(f"✓ Extracted {len(text)} characters (sufficient for LLM analysis)")
        else:
            print(f"✗ Only {len(text)} characters extracted (may be insufficient)")
    else:
        print(f"✗ Failed to extract text: {text}")

    print()
    print("=" * 80)
    print("COMPARISON: OLD vs NEW APPROACH")
    print("=" * 80)
    print("""
OLD (Broken):
  - Fetched index.html page
  - Pattern-matched keywords: 'Risk Factors', 'business', 'uncertainty'
  - Returned: "Risk Factors business uncertainty" (basically useless)
  - Text length: ~30 chars

NEW (Fixed):
  - Fetches actual 10-K document (primaryDocument)
  - Uses BeautifulSoup to strip HTML tags
  - Searches for Item 1A (Risk Factors) or Item 7 (MD&A) sections
  - Extracts 3000-5000 chars of real prose
  - Passes full section text to LLM for analysis
  - Text length: ~3000-4000 chars (100x more content)
""")

    return result


if __name__ == "__main__":
    try:
        test_document_extraction()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
