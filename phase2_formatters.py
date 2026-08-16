"""Display formatters for financial data. Unit-tested for accuracy."""


def format_dividend_yield(yield_value: float) -> str:
    """Format dividend yield as percentage. Example: 0.025 -> '2.50%'"""
    if yield_value is None or (isinstance(yield_value, str) and yield_value == 'N/A'):
        return 'N/A'
    try:
        percent = float(yield_value) * 100
        return f"{percent:.2f}%"
    except (ValueError, TypeError):
        return 'N/A'


def format_market_cap(market_cap_value: float) -> str:
    """Format market cap with B/M suffix. Example: 1250000000 -> '$1.25B'"""
    if market_cap_value is None or (isinstance(market_cap_value, str) and market_cap_value == 'N/A'):
        return 'N/A'
    try:
        value = float(market_cap_value)
        if value >= 1e9:
            return f"${value / 1e9:.2f}B"
        elif value >= 1e6:
            return f"${value / 1e6:.2f}M"
        elif value >= 1e3:
            return f"${value / 1e3:.2f}K"
        else:
            return f"${value:.2f}"
    except (ValueError, TypeError):
        return 'N/A'


def format_currency(currency_value: float) -> str:
    """Format currency with commas. Example: 1250.5 -> '$1,250.50'"""
    if currency_value is None or (isinstance(currency_value, str) and currency_value == 'N/A'):
        return 'N/A'
    try:
        value = float(currency_value)
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return 'N/A'


def format_pe_ratio(pe_value: float) -> str:
    """Format P/E ratio. Example: 25.5 -> '25.50'"""
    if pe_value is None or (isinstance(pe_value, str) and pe_value == 'N/A'):
        return 'N/A'
    try:
        value = float(pe_value)
        return f"{value:.2f}"
    except (ValueError, TypeError):
        return 'N/A'


def format_percent_change(percent_value: float) -> str:
    """Format percentage change with sign. Example: 0.025 -> '+2.50%', -0.015 -> '-1.50%'"""
    if percent_value is None or (isinstance(percent_value, str) and percent_value == 'N/A'):
        return 'N/A'
    try:
        value = float(percent_value) * 100
        sign = '+' if value >= 0 else ''
        return f"{sign}{value:.2f}%"
    except (ValueError, TypeError):
        return 'N/A'
