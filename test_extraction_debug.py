#!/usr/bin/env python3
"""Debug script to see what text we're actually getting from AAPL 10-K."""

import re
import requests
from bs4 import BeautifulSoup

SEC_CIK_BY_SYMBOL = {"AAPL": "0000320193"}

def debug_extraction():
    cik = SEC_CIK_BY_SYMBOL["AAPL"]
    headers = {"User-Agent": "FinaAgentBot/1.0", "Accept-Encoding": "gzip, deflate"}

    # Get filing metadata
    response = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers, timeout=20)
    payload = response.json()
    recent = payload.get('filings', {}).get('recent', {})

    forms = recent.get('form') or []
    accession_numbers = recent.get('accessionNumber') or []
    primary_documents = recent.get('primaryDocument') or []

    # Get first 10-K
    for idx, form in enumerate(forms):
        if str(form).upper() == '10-K':
            accession = accession_numbers[idx]
            primary_doc = primary_documents[idx]
            break

    footer = accession.replace('-', '')
    doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{footer}/{primary_doc}"
    print(f"Fetching: {doc_url}\n")

    # Fetch and parse
    doc_response = requests.get(doc_url, headers=headers, timeout=30)
    soup = BeautifulSoup(doc_response.text, 'html.parser')
    text = soup.get_text()
    text = re.sub(r'\s+', ' ', text)

    print(f"Total text length: {len(text)} characters\n")

    # Find Item 1A using improved logic
    item_marker = 'item 1a'
    positions = [(m.start(), m.end()) for m in re.finditer(re.escape(item_marker), text, re.IGNORECASE)]

    print(f"Found {len(positions)} occurrences of 'Item 1A'\n")

    if positions:
        for idx, (pos_start, pos_end) in enumerate(positions):
            print(f"Occurrence {idx + 1} at position {pos_start}:")
            context = text[max(0, pos_start - 100):pos_end + 300]
            print(f"  Context: ...{context}...\n")

            # Find next item marker
            next_item_match = re.search(r'item\s+\d+', text[pos_end:], re.IGNORECASE)
            if next_item_match:
                section_end = pos_end + next_item_match.start()
            else:
                section_end = len(text)

            section = text[pos_start:section_end].strip()
            print(f"  Section length: {len(section)} characters")

            if len(section) > 1000:
                print(f"  ✓ This section is usable ({len(section)} chars)")
                print(f"\n  FIRST 1500 CHARS:")
                print("  " + "-" * 76)
                for line in section[:1500].split('\n'):
                    print(f"  {line}")
                print("  " + "-" * 76)
                break
            else:
                print(f"  ✗ Section too short ({len(section)} chars)\n")

    # Search for where "Item 1A" appears in the text
    item1a_pos = text.lower().find('item 1a')
    if item1a_pos >= 0:
        print(f"\n'Item 1A' found at position {item1a_pos}")
        print("\nCONTEXT AROUND 'ITEM 1A' (500 chars before and after):")
        print("-" * 80)
        start = max(0, item1a_pos - 500)
        end = min(len(text), item1a_pos + 2500)
        context = text[start:end]
        print(context)
        print("-" * 80)

        # Try to find next item marker
        next_item = re.search(r'item\s+\d+', text[item1a_pos + 10:].lower())
        if next_item:
            next_pos = item1a_pos + 10 + next_item.start()
            print(f"\nNext item marker found at position {next_pos}")
            section_length = next_pos - item1a_pos
            print(f"Section 1A would be approximately {section_length} characters")
    else:
        print("\n'Item 1A' not found in text at all")

if __name__ == "__main__":
    try:
        debug_extraction()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
