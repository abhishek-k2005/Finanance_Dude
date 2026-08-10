import json
import os
import re
import math
from datetime import datetime

import requests
import yfinance as yf
from openai import OpenAI


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

    def fetch_latest_risk_section(self, symbol: str):
        """Fetch a body of SEC EDGAR risk language for a symbol if available."""
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
            "Accept": "application/json",
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

            # Discover the most recent 10-K filing accessions.
            candidate = None
            for idx, form in enumerate(forms):
                if str(form).upper() == '10-K':
                    candidate = {
                        'form': form,
                        'accession': accession_numbers[idx] if idx < len(accession_numbers) else None,
                        'date': filing_dates[idx] if idx < len(filing_dates) else None,
                    }
                    break

            if not candidate or not candidate.get('accession'):
                return {
                    "source": "sec-edgar",
                    "symbol": symbol.upper(),
                    "text": "No 10-K filing accession could be resolved from the SEC submissions API.",
                    "available": False,
                }

            footer = candidate['accession'].replace('-', '')
            # Index report URL pattern: SEC filing archive HTML under /Archives/edgar/data/<cik>/<accession>/index.html
            # The accession number is normalized by stripping dashes and keeping the file stem.
            # We target the most recent index page for the filing and then extract explicit risk content from the html if present.
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{footer}/{candidate['accession']}-index.html"
            filing_response = requests.get(filing_url, headers=headers, timeout=30)
            if filing_response.status_code != 200:
                return {
                    "source": "sec-edgar",
                    "symbol": symbol.upper(),
                    "text": "SEC EDGAR filing index response was not reachable or not parseable.",
                    "available": False,
                }

            # Pull brief text heuristics from the HTML-to-text body if present.
            html = filing_response.text
            risk_hits = []
            for phrase in [
                'Risk Factors', 'risk factors', 'business', 'uncertainty', 'regulation', 'cybersecurity'
            ]:
                if phrase.lower() in html.lower():
                    risk_hits.append(phrase)

            text_snippet = ' '.join(risk_hits) or 'Risk factors and management language were not resolvable through the EDGAR response.'
            return {
                "source": "sec-edgar",
                "symbol": symbol.upper(),
                "text": text_snippet[:3000],
                "available": True,
                "form": candidate.get('form'),
                "filing_date": candidate.get('date'),
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
