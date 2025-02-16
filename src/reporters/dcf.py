import requests
import yfinance as yf
from requests import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Get API key from .env
FMP_API_KEY = os.getenv("FMP_API_KEY")

if not FMP_API_KEY:
    raise ValueError("FMP_API_KEY is missing. Add it to the .env file.")

# Function to fetch financial data from Yahoo Finance
def get_financials(ticker):
    stock = yf.Ticker(ticker)
    
    # Get financial statements
    income_stmt = stock.financials
    cashflow_stmt = stock.cashflow
    balance_sheet = stock.balance_sheet

    # Extract key financial metrics
    def safe_get(dataframe, keys):
        for key in keys:
            if key in dataframe.index:
                return dataframe.loc[key].iloc[0]
        return None

    revenue = safe_get(income_stmt, ["Total Revenue", "Revenue"])
    net_income = safe_get(income_stmt, ["Net Income"])
    operating_cash_flow = safe_get(cashflow_stmt, ["Total Cash From Operating Activities", "Operating Cash Flow"])
    capex = safe_get(cashflow_stmt, ["Capital Expenditures", "Capital Expenditure"])
    debt = safe_get(balance_sheet, ["Total Debt", "Long Term Debt"]) or 0
    cash = safe_get(balance_sheet, ["Cash And Cash Equivalents", "Cash"]) or 0

    # Get shares outstanding
    shares_outstanding = stock.info.get('sharesOutstanding', None)
    if shares_outstanding is None:
        raise ValueError(f"Shares outstanding data unavailable for {ticker}")

    return revenue, net_income, operating_cash_flow, capex, debt, cash, shares_outstanding

def get_fmp_data(ticker):
    """
    Calculate WACC, growth rate, and terminal value using FMP's free endpoints.
    Returns: dict with WACC, growth_rate, terminal_value
    """
    base_url = "https://financialmodelingprep.com/api/v3"
    results = {}
    
    # Get beta
    beta_data = requests.get(f"{base_url}/stock/beta?symbol={ticker}&apikey={FMP_API_KEY}").json()
    beta = beta_data[0]['beta'] if beta_data and 'beta' in beta_data[0] else 1.0  # Default to 1 if no beta
    
    # Get risk-free rate (10-year Treasury)
    treasury = requests.get(f"{base_url}/treasury?apikey={FMP_API_KEY}").json()
    risk_free = treasury[0]['year10'] / 100 if treasury else 0.0  # Default to 0 if no treasury data
    
    # Get market data
    quote = requests.get(f"{base_url}/quote/{ticker}?apikey={FMP_API_KEY}").json()
    market_cap = quote[0]['marketCap'] if quote else 0  # Default to 0 if no market data
    
    # Get financial statements
    income_stmt = requests.get(f"{base_url}/income-statement/{ticker}?apikey={FMP_API_KEY}&limit=1").json()
    balance_sheet = requests.get(f"{base_url}/balance-sheet-statement/{ticker}?apikey={FMP_API_KEY}&limit=1").json()
    
    if not income_stmt or not balance_sheet:
        raise ValueError(f"Financial statements not available for {ticker}")
    
    # Cost of equity (CAPM)
    market_return = 0.08  # Assumed 8% historical market return
    cost_equity = risk_free + beta * (market_return - risk_free)
    
    # Cost of debt
    interest_expense = income_stmt[0]['interestExpense'] if 'interestExpense' in income_stmt[0] else 0
    total_debt = balance_sheet[0]['totalDebt'] if 'totalDebt' in balance_sheet[0] else 0
    cost_debt = interest_expense / total_debt if total_debt else 0
    
    # WACC calculation
    tax_rate = income_stmt[0]['incomeTaxExpense'] / income_stmt[0]['incomeBeforeTax'] if income_stmt[0].get('incomeBeforeTax') else 0
    equity_weight = market_cap / (market_cap + total_debt) if market_cap else 0
    debt_weight = total_debt / (market_cap + total_debt) if market_cap else 0
    
    wacc = (equity_weight * cost_equity) + (debt_weight * cost_debt * (1 - tax_rate))
    results['wacc'] = wacc
    
    # Growth rate (FCF CAGR)
    cash_flows = requests.get(f"{base_url}/cash-flow-statement/{ticker}?apikey={FMP_API_KEY}&limit=5").json()
    fcf = [cf['freeCashFlow'] for cf in cash_flows if 'freeCashFlow' in cf]
    
    if len(fcf) >= 2:
        cagr = (fcf[0] / fcf[-1]) ** (1/(len(fcf)-1)) - 1
        results['growth_rate'] = cagr
    else:
        results['growth_rate'] = 0.02  # Fallback to 2% if FCF data is insufficient
    
    # Terminal value (Gordon Growth)
    try:
        last_fcf = fcf[0]
        g = results['growth_rate']
        terminal_value = (last_fcf * (1 + g)) / (wacc - g)
        results['terminal_value'] = terminal_value
    except ZeroDivisionError:
        results['terminal_value'] = None

    return results['wacc'], results['growth_rate'], results['terminal_value']


def format_financial_number(number):
    """Format financial numbers to appropriate scale (B, M, K)"""
    abs_num = abs(number)
    if abs_num >= 1e9:
        return f"${number/1e9:.2f}B"
    elif abs_num >= 1e6:
        return f"${number/1e6:.2f}M"
    elif abs_num >= 1e3:
        return f"${number/1e3:.2f}K"
    else:
        return f"${number:.2f}"

def calculate_dcf(fcf, debt, cash, shares_outstanding, growth_rate, discount_rate, terminal_value, revenue, net_income, operating_cash_flow, capex, years=5):
    projected_fcf = []
    current_fcf = operating_cash_flow + capex  # Calculate initial FCF correctly
    
    # Project future cash flows
    for i in range(1, years + 1):
        projected_fcf_value = current_fcf * (1 + growth_rate) ** i  # Compound growth
        discounted_fcf = projected_fcf_value / (1 + discount_rate) ** i  # Discount to present value
        projected_fcf.append(discounted_fcf)
    
    # Calculate terminal value using Gordon Growth model
    # Use a more conservative terminal growth rate (typically lower than initial growth rate)
    terminal_growth_rate = min(growth_rate, 0.03)  # Cap terminal growth at 3%
    terminal_year_fcf = current_fcf * (1 + growth_rate) ** years  # FCF in terminal year
    
    # Only calculate terminal value if discount rate > growth rate
    if discount_rate <= terminal_growth_rate:
        terminal_growth_rate = discount_rate - 0.01  # Ensure discount rate > growth rate
    
    terminal_value = terminal_year_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
    terminal_value_discounted = terminal_value / (1 + discount_rate) ** years
    
    # Enterprise Value Calculation
    enterprise_value = sum(projected_fcf) + terminal_value_discounted
    equity_value = enterprise_value - debt + cash
    intrinsic_value_per_share = equity_value / shares_outstanding

    # Detailed explanation with formatted numbers
    explanation = f"Explanation:\n"
    explanation += f"\nValuation Breakdown:"
    explanation += f"\n1. Current FCF: {format_financial_number(current_fcf)}"
    explanation += f"\n2. Projected FCFs (Present Value):"
    for i, fcf in enumerate(projected_fcf, 1):
        explanation += f"\n   Year {i}: {format_financial_number(fcf)}"
    explanation += f"\n   Total PV of FCFs: {format_financial_number(sum(projected_fcf))}"
    explanation += f"\n3. Terminal Value (PV): {format_financial_number(terminal_value_discounted)}"
    explanation += f"\n4. Enterprise Value: {format_financial_number(enterprise_value)}"
    explanation += f"\n5. Equity Value: {format_financial_number(equity_value)}"
    
    explanation += f"\n\nKey Financials:"
    explanation += f"\nRevenue: {format_financial_number(revenue)}"
    explanation += f"\nNet Income: {format_financial_number(net_income)}"
    explanation += f"\nOperating Cash Flow: {format_financial_number(operating_cash_flow)}"
    explanation += f"\nCapEx: {format_financial_number(capex)}"
    explanation += f"\nDebt: {format_financial_number(debt)}"
    explanation += f"\nCash: {format_financial_number(cash)}"
    explanation += f"\nWACC: {discount_rate:.2%}"
    explanation += f"\nGrowth Rate: {growth_rate:.2%}"
    explanation += f"\nTerminal Growth Rate: {terminal_growth_rate:.2%}"
    
    return intrinsic_value_per_share, explanation
# Main function to run DCF analysis
def run_dcf(ticker):
    try:
        # Fetch financial data
        revenue, net_income, operating_cash_flow, capex, debt, cash, shares_outstanding = get_financials(ticker)
        fcf = operating_cash_flow + capex  # Free Cash Flow

        # Fetch WACC and Growth Rate from FMP (and Terminal Value)
        wacc, growth_rate, terminal_value = get_fmp_data(ticker)
        if wacc is None:
            raise ValueError(f"Missing WACC for {ticker}")
        
        # Calculate DCF Valuation
        intrinsic_value, explanation = calculate_dcf(fcf, debt, cash, shares_outstanding, growth_rate, wacc, terminal_value, revenue, net_income, operating_cash_flow, capex)

        return {
            "intrinsic_value_per_share": intrinsic_value,
            "explanation": explanation
        }

    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}
