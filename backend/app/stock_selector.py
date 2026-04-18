import asyncio
import yfinance as yf
import pandas as pd
from typing import List, Dict

# Hardcoded fallback universe — only used when the LLM call fails
STOCK_UNIVERSE = {
    "ETF":         ["SPY", "QQQ", "VTI", "VOO", "SCHD", "ARKK", "DIA", "IWM"],
    "Blue Chip":   ["AAPL", "MSFT", "JNJ", "PG", "JPM", "V", "WMT", "KO", "PEP", "MCD"],
    "IPO":         ["HOOD", "COIN", "RBLX", "RDDT", "ARM", "CART", "KVUE"],
    "Rising Star": ["NVDA", "AMD", "SMCI", "PLTR", "CRWD", "SNOW", "TSLA", "META"],
}

def _flatten_tickers(tickers) -> List[str]:
    """Ensure tickers is a flat list of strings, handling any nested lists the LLM may return."""
    flat = []
    for t in tickers:
        if isinstance(t, list):
            flat.extend(str(x).strip().upper() for x in t if x)
        elif isinstance(t, str) and t.strip():
            flat.append(t.strip().upper())
    return flat


def fetch_metrics(tickers: List[str]) -> pd.DataFrame:
    """
    Fetches 6-month historical data for a list of tickers and calculates:
    - 6-month return
    - Volatility (Standard deviation of daily returns)
    """
    tickers = _flatten_tickers(tickers)
    if not tickers:
        return pd.DataFrame()

    # Pass as space-separated string — yfinance 0.2.x handles lists inconsistently
    tickers_str = " ".join(tickers) if len(tickers) > 1 else tickers[0]
    data = yf.download(tickers_str, period="6mo", group_by="ticker", auto_adjust=True, threads=True)
    
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

async def get_algorithmic_portfolio(risk_tolerance: str, interests: str = "") -> List[Dict]:
    """
    Selects stocks algorithmically based on risk tolerance.
    When user interests are provided, first asks the LLM to generate a
    personalised universe of tickers, then ranks them by return/volatility.

    Low Risk:    Favours ETFs and Blue Chips (low volatility).
    Medium Risk: Balanced mix.
    High Risk:   Favours Rising Stars and IPOs (high return potential).
    """
    # --- Step 1: Build the candidate universe ---
    universe = STOCK_UNIVERSE  # default fallback

    if interests:
        try:
            from .llm_service import generate_stock_universe
            llm_universe = await generate_stock_universe(interests, risk_tolerance)
            # Validate that we got all four expected keys with non-empty lists
            if all(llm_universe.get(k) for k in ["ETF", "Blue Chip", "IPO", "Rising Star"]):
                universe = llm_universe
                print(f"[stock_selector] Using LLM-generated universe for interests: {interests!r}")
            else:
                print("[stock_selector] LLM universe incomplete — falling back to default.")
        except Exception as e:
            print(f"[stock_selector] LLM universe generation failed: {e} — using default.")

    risk = risk_tolerance.lower()

    # --- Step 2: Define allocation by risk profile ---
    allocation = {
        "low":    {"ETF": 3, "Blue Chip": 2, "IPO": 0, "Rising Star": 0},
        "medium": {"ETF": 1, "Blue Chip": 2, "IPO": 1, "Rising Star": 1},
        "high":   {"ETF": 0, "Blue Chip": 1, "IPO": 2, "Rising Star": 2},
    }.get(risk, {"ETF": 1, "Blue Chip": 2, "IPO": 1, "Rising Star": 1})

    portfolio = []

    for category, count in allocation.items():
        if count == 0:
            continue

        tickers = universe.get(category, STOCK_UNIVERSE[category])
        metrics_df = fetch_metrics(tickers)

        if metrics_df.empty:
            continue

        # Sorting logic:
        # For Low/Medium risk, prefer lower volatility (ETFs/Blue Chips)
        # For High risk, prefer absolute highest 6-month return
        if risk == "low" or category in ["ETF", "Blue Chip"]:
            selected = metrics_df.sort_values(by="volatility", ascending=True).head(count)
        else:
            selected = metrics_df.sort_values(by="return_6m", ascending=False).head(count)

        for _, row in selected.iterrows():
            portfolio.append({
                "ticker":         row["ticker"],
                "category":       category,
                "projected_cagr": row["return_6m"] * 2,  # rough annualised projection
                "volatility":     row["volatility"],
            })

    return portfolio


# Example usage if run directly
if __name__ == "__main__":
    print("Testing Medium Risk Portfolio:")
    print(asyncio.run(get_algorithmic_portfolio("medium", "AI, clean energy")))
