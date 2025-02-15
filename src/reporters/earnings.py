import yfinance as yf
import pandas as pd
import numpy as np

def safe_float(value):
    """Convert value to float if possible, otherwise return None."""
    try:
        val = float(value)
        return val if not np.isnan(val) else None  # Ensure NaN values are handled
    except (ValueError, TypeError):
        return None

def get_earnings_yfinance(ticker):
    stock = yf.Ticker(ticker)

    # Fetch **quarterly** income statement (Revenue & Net Income)
    income_stmt = stock.quarterly_income_stmt
    financials = stock.quarterly_financials  # Use quarterly data for EPS

    earnings_data = []

    if income_stmt is not None and not income_stmt.empty:
        # Extract last 4 quarters of revenue & net income
        revenue = income_stmt.loc["Total Revenue"].head(4)
        net_income = income_stmt.loc["Net Income"].head(4)

        # Extract last 4 quarters of EPS
        eps = financials.loc["Diluted EPS"].head(4) if financials is not None else None

        # Prepare clean data
        for date in revenue.index:
            rev = safe_float(revenue[date]) / 1e9 if safe_float(revenue[date]) is not None else None
            net_inc = safe_float(net_income[date]) / 1e9 if safe_float(net_income[date]) is not None else None
            eps_value = safe_float(eps[date]) if eps is not None and date in eps and safe_float(eps[date]) is not None else None

            # Only add rows where all values are valid
            if rev is not None and net_inc is not None and eps_value is not None:
                earnings_data.append({
                    "date": date.date().strftime("%Y-%m-%d"),
                    "revenue": f"${rev:.2f}B",
                    "net_income": f"${net_inc:.2f}B",
                    "eps": f"{eps_value:.2f}"
                })

    # Fetch upcoming earnings date and format it properly
    try:
        upcoming_earnings = stock.calendar.get("Earnings Date", "N/A")
        if upcoming_earnings != "N/A":
            upcoming_earnings = pd.to_datetime(upcoming_earnings)
            if isinstance(upcoming_earnings, pd.Index):
                upcoming_earnings = upcoming_earnings[0].strftime("%Y-%m-%d")
            else:
                upcoming_earnings = upcoming_earnings.strftime("%Y-%m-%d")
        else:
            upcoming_earnings = "N/A"
    except (AttributeError, KeyError, TypeError, IndexError):
        upcoming_earnings = "N/A"

    return {
        "earnings_data": earnings_data,
        "upcoming_earnings": upcoming_earnings
    }
