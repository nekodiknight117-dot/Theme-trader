import yfinance as yf
import pandas as pd
from typing import List, Dict

# Hardcoded universe as a fallback to LLM selection
STOCK_UNIVERSE = {
    "ETF": ["SPY", "QQQ", "VTI", "VOO", "SCHD", "ARKK", "DIA", "IWM"],
    "Blue Chip": ["AAPL", "MSFT", "JNJ", "PG", "JPM", "V", "WMT", "KO", "PEP", "MCD"],
    "IPO": ["HOOD", "COIN", "RBLX", "RDDT", "ARM", "CART", "KVUE"], # Recent-ish IPOs
    "Rising Star": ["NVDA", "AMD", "SMCI", "PLTR", "CRWD", "SNOW", "TSLA", "META"]
}

def fetch_metrics(tickers: List[str]) -> pd.DataFrame:
    """
    Fetches 6-month historical data for a list of tickers and calculates:
    - 6-month return
    - Volatility (Standard deviation of daily returns)
    """
    # Fetch data as a single batch for speed
    data = yf.download(tickers, period="6mo", group_by="ticker", auto_adjust=True, threads=True)
    
    metrics = []
    
    # Handle single ticker case vs multiple tickers
    if len(tickers) == 1:
        ticker = tickers[0]
        df = data
        if not df.empty and len(df) > 1:
            start_price = df['Close'].iloc[0]
            end_price = df['Close'].iloc[-1]
            ret = (end_price - start_price) / start_price
            volatility = df['Close'].pct_change().std() * (252 ** 0.5) # Annualized volatility
            metrics.append({"ticker": ticker, "return_6m": ret, "volatility": volatility})
    else:
        for ticker in tickers:
            # yfinance returns a multi-index column dataframe when querying multiple tickers
            df = data[ticker] if ticker in data else pd.DataFrame()
            if not df.empty and len(df['Close'].dropna()) > 1:
                # Drop NAs to handle stocks that might not have full 6mo history (like fresh IPOs)
                close_prices = df['Close'].dropna()
                if len(close_prices) > 0:
                    start_price = close_prices.iloc[0]
                    end_price = close_prices.iloc[-1]
                    # Convert items to python floats to avoid numpy type issues later
                    ret = float((end_price - start_price) / start_price)
                    volatility = float(close_prices.pct_change().std() * (252 ** 0.5))
                    metrics.append({"ticker": ticker, "return_6m": ret, "volatility": volatility})
                
    return pd.DataFrame(metrics)

def get_algorithmic_portfolio(risk_tolerance: str) -> List[Dict]:
    """
    Selects stocks algorithmically based on risk tolerance.
    Low Risk: Heavily favors ETFs and Blue Chips (low volatility).
    Medium Risk: Balanced mix.
    High Risk: Heavily favors Rising Stars and IPOs (high return potential, ignores high volatility).
    """
    risk = risk_tolerance.lower()
    
    # Define how many of each category to pick based on risk
    allocation = {
        "low": {"ETF": 3, "Blue Chip": 2, "IPO": 0, "Rising Star": 0},
        "medium": {"ETF": 1, "Blue Chip": 2, "IPO": 1, "Rising Star": 1},
        "high": {"ETF": 0, "Blue Chip": 1, "IPO": 2, "Rising Star": 2}
    }.get(risk, {"ETF": 1, "Blue Chip": 2, "IPO": 1, "Rising Star": 1}) # Default to medium
    
    portfolio = []
    
    for category, count in allocation.items():
        if count == 0:
            continue
            
        tickers = STOCK_UNIVERSE[category]
        metrics_df = fetch_metrics(tickers)
        
        if metrics_df.empty:
            continue
            
        # Sorting logic:
        # For Low/Medium risk, we prefer lower volatility for ETFs/Blue chips
        # For High risk, we prefer absolute highest 6m return regardless of volatility
        if risk == "low" or category in ["ETF", "Blue Chip"]:
            # Sort by volatility ascending (safest first)
            selected = metrics_df.sort_values(by="volatility", ascending=True).head(count)
        else:
            # Sort by return ascending (highest gainers first)
            selected = metrics_df.sort_values(by="return_6m", ascending=False).head(count)
            
        for _, row in selected.iterrows():
            portfolio.append({
                "ticker": row['ticker'],
                "category": category,
                "projected_cagr": row['return_6m'] * 2, # Rough projection assuming trend continues
                "volatility": row['volatility']
            })
            
    return portfolio

# Example usage if run directly
if __name__ == "__main__":
    print("Testing Medium Risk Portfolio:")
    print(get_algorithmic_portfolio("medium"))
