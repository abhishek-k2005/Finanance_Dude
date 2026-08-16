"""Unit tests for financial display formatters."""

import pytest
from phase2_formatters import (
    format_dividend_yield,
    format_market_cap,
    format_currency,
    format_pe_ratio,
    format_percent_change
)


class TestDividendYieldFormatter:
    """Test dividend_yield formatter catches percentage conversion bugs."""

    def test_format_dividend_yield_basic(self):
        """Test basic dividend yield formatting."""
        assert format_dividend_yield(0.025) == "2.50%"

    def test_format_dividend_yield_small(self):
        """Test small dividend yield."""
        assert format_dividend_yield(0.0005) == "0.05%"

    def test_format_dividend_yield_zero(self):
        """Test zero dividend."""
        assert format_dividend_yield(0.0) == "0.00%"

    def test_format_dividend_yield_large(self):
        """Test large dividend yield."""
        assert format_dividend_yield(0.15) == "15.00%"

    def test_format_dividend_yield_na(self):
        """Test N/A handling."""
        assert format_dividend_yield(None) == 'N/A'
        assert format_dividend_yield('N/A') == 'N/A'

    def test_format_dividend_yield_invalid(self):
        """Test invalid input."""
        assert format_dividend_yield("invalid") == 'N/A'


class TestMarketCapFormatter:
    """Test market_cap formatter handles B/M/K suffixes."""

    def test_format_market_cap_billions(self):
        """Test market cap in billions."""
        assert format_market_cap(1_250_000_000) == "$1.25B"

    def test_format_market_cap_millions(self):
        """Test market cap in millions."""
        assert format_market_cap(500_000_000) == "$500.00M"

    def test_format_market_cap_thousands(self):
        """Test market cap in thousands."""
        assert format_market_cap(750_000) == "$750.00K"

    def test_format_market_cap_small(self):
        """Test small market cap."""
        assert format_market_cap(999) == "$999.00"

    def test_format_market_cap_very_large(self):
        """Test very large market cap."""
        assert format_market_cap(3_500_000_000_000) == "$3500.00B"

    def test_format_market_cap_na(self):
        """Test N/A handling."""
        assert format_market_cap(None) == 'N/A'
        assert format_market_cap('N/A') == 'N/A'


class TestCurrencyFormatter:
    """Test currency formatter with comma thousands separator."""

    def test_format_currency_basic(self):
        """Test basic currency formatting."""
        assert format_currency(1250.5) == "$1,250.50"

    def test_format_currency_no_decimals(self):
        """Test currency with no decimal part."""
        assert format_currency(1000.0) == "$1,000.00"

    def test_format_currency_large(self):
        """Test large currency value."""
        assert format_currency(1_234_567.89) == "$1,234,567.89"

    def test_format_currency_small(self):
        """Test small currency value."""
        assert format_currency(12.34) == "$12.34"

    def test_format_currency_na(self):
        """Test N/A handling."""
        assert format_currency(None) == 'N/A'
        assert format_currency('N/A') == 'N/A'


class TestPERatioFormatter:
    """Test P/E ratio formatter."""

    def test_format_pe_ratio_basic(self):
        """Test basic P/E ratio."""
        assert format_pe_ratio(25.5) == "25.50"

    def test_format_pe_ratio_whole_number(self):
        """Test whole number P/E ratio."""
        assert format_pe_ratio(20.0) == "20.00"

    def test_format_pe_ratio_na(self):
        """Test N/A handling."""
        assert format_pe_ratio(None) == 'N/A'
        assert format_pe_ratio('N/A') == 'N/A'


class TestPercentChangeFormatter:
    """Test percent change formatter with +/- sign."""

    def test_format_percent_change_positive(self):
        """Test positive percent change."""
        assert format_percent_change(0.025) == "+2.50%"

    def test_format_percent_change_negative(self):
        """Test negative percent change."""
        assert format_percent_change(-0.015) == "-1.50%"

    def test_format_percent_change_zero(self):
        """Test zero percent change."""
        assert format_percent_change(0.0) == "+0.00%"

    def test_format_percent_change_large_positive(self):
        """Test large positive percent change."""
        assert format_percent_change(0.35) == "+35.00%"

    def test_format_percent_change_na(self):
        """Test N/A handling."""
        assert format_percent_change(None) == 'N/A'
        assert format_percent_change('N/A') == 'N/A'
