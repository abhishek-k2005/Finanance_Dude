import json
import os
import re
import math
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf
from openai import OpenAI
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

HEDGE_WORDS = {
    "maybe", "possibly", "perhaps", "likely", "could", "may", "might", "depends",
    "subject", "uncertain", "unclear", "expect", "anticipate", "estimate", "believe",
    "plans", "intend", "seek", "should", "would", "potential", "risk", "balance",
    "ongoing", "ongoing basis", "if", "when", "future", "pending", "sometimes"
}


class AISignalAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.model = "llama-3.3-70b-versatile"

    def _get_sec_cik(self, symbol: str):
        symbol = symbol.upper()
        return SEC_CIK_BY_SYMBOL.get(symbol)

    def _extract_item_section(self, text: str, item_numbers: list) -> str:
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

    def fetch_latest_risk_section(self, symbol: str, as_of_date: str = None):
        """Fetch and extract real text from SEC EDGAR 10-K document (Item 1A: Risk Factors or Item 7: MD&A).
        If as_of_date is provided, return the most recent 10-K filed before that date (point-in-time)."""
        cik = self._get_sec_cik(symbol)
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

            section_text = self._extract_item_section(text, ['1a', '1A'])
            if not section_text:
                section_text = self._extract_item_section(text, ['7', '7a', '7A'])

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

    def extract_ai_signal(self, symbol: str):
        """LLM-driven AI signal extraction from the latest available risk/facts text."""
        risk_payload = self.fetch_latest_risk_section(symbol)
        text = risk_payload.get('text') or ""

        if not risk_payload.get('available', False):
            # Use an empty grounded JSON-but-structured fallback so the backend still replies with defaults.
            return {
                "symbol": symbol.upper(),
                "source": risk_payload.get('source') or 'none',
                "management_tone_confidence": 0.5,
                "hedging_language_density": 0.0,
                "guidance_sentiment": 'neutral',
                "semantic_drift": 0.0,
                "transcript_available": False,
                "raw_excerpt": text[:2000],
            }

        prompt = f"""
You are a financial language analyst. Read only the company text provided below.
Return a strict JSON object and nothing else.

JSON contract:
{{
  "management_tone_confidence": float between 0 and 1,
  "hedging_language_density": float counting hedge words per 100 words,
  "guidance_sentiment": "positive" | "neutral" | "negative",
  "semantic_drift": float between 0 and 1,
  "supporting_rationale": "short string"
}}

Source text:
{text}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a text-analysis specialist for financial filings and earnings transcripts. Respond only with strict JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        return {
            "symbol": symbol.upper(),
            "source": risk_payload.get('source'),
            "management_tone_confidence": float(parsed.get('management_tone_confidence', 0.5)),
            "hedging_language_density": float(parsed.get('hedging_language_density', 0.0)),
            "guidance_sentiment": str(parsed.get('guidance_sentiment', 'neutral')).lower(),
            "semantic_drift": float(parsed.get('semantic_drift', 0.0)),
            "transcript_available": bool(risk_payload.get('available')),
            "raw_excerpt": text[:2000],
        }


# FastAPI-compatible callable kept outside the class signature.
def extract_ai_signal(symbol: str):
    analyzer = AISignalAnalyzer()
    return analyzer.extract_ai_signal(symbol)


# ---------------------------------------------------------------------------
# News-sentiment analysis — completely separate from guidance_sentiment above.
# ---------------------------------------------------------------------------

def analyze_news_sentiment(symbol: str, as_of_date=None) -> dict:
    """
    Fetch recent headlines for *symbol* and return LLM-derived sentiment.

    Returns a dict with exactly two keys:
        news_sentiment : "positive" | "neutral" | "negative"
        key_theme      : short descriptive string

    Never raises — always returns the fallback dict on any failure.
    """
    _FALLBACK = {"news_sentiment": "neutral", "key_theme": "No recent news"}

    try:
        from news_fetcher import fetch_recent_news

        articles = fetch_recent_news(symbol, as_of_date=as_of_date)
        if not articles:
            return _FALLBACK

        # Build a single compact prompt from headlines + summaries.
        news_text_parts = []
        for i, art in enumerate(articles, start=1):
            headline = art.get("headline", "").strip()
            summary = art.get("summary", "").strip()
            line = f"{i}. {headline}"
            if summary:
                # Limit summary to keep the prompt tight.
                line += f" — {summary[:200]}"
            news_text_parts.append(line)

        news_text = "\n".join(news_text_parts)

        prompt = f"""You are a financial news analyst.
Read the following recent news headlines and summaries for {symbol.upper()}.
Return ONLY a strict JSON object and nothing else.

JSON contract:
{{
  "news_sentiment": "positive" | "neutral" | "negative",
  "key_theme": "short string describing the dominant news theme"
}}

News:
{news_text}
"""

        client = __import__("openai").OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial news sentiment specialist. "
                        "Respond only with strict JSON matching the requested contract."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content.strip()
        # Strip potential markdown fences.
        if content.startswith("```"):
            content = re.sub(r"^```[a-z]*\n?", "", content)
            content = content.rstrip("` \n")

        parsed = json.loads(content)
        sentiment = str(parsed.get("news_sentiment", "neutral")).lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"

        return {
            "news_sentiment": sentiment,
            "key_theme": str(parsed.get("key_theme", "N/A")),
        }

    except Exception:
        return _FALLBACK
