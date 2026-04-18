import os
import json
import httpx
from pathlib import Path

# Explicitly load the root-level .env — works regardless of where uvicorn is launched from
# Path: app/llm_service.py -> app/ -> backend/ -> project root
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
try:
    import dotenv
    dotenv.load_dotenv(dotenv_path=_ROOT_ENV, override=True)
except ImportError:
    pass

# --- Featherless Configuration (only LLM provider) ---
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1/chat/completions"
MODEL_NAME = "google/gemma-4-31B-it"
API_KEY = os.getenv("FEATHERLESS_API_KEY", "")

# Startup validation — fail loudly if the key is missing
if not API_KEY or API_KEY == "your_featherless_api_key_here":
    raise EnvironmentError(
        "\n[llm_service] FEATHERLESS_API_KEY is not set or is a placeholder.\n"
        "  1. Get a key at https://featherless.ai -> Dashboard -> API Keys\n"
        f"  2. Add it to your .env file at: {_ROOT_ENV}\n"
        "     FEATHERLESS_API_KEY=rc_your_key_here\n"
    )

print(f"[llm_service] Featherless ready -> {FEATHERLESS_BASE_URL} / {MODEL_NAME}")


def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


async def _post(payload: dict) -> dict:
    """Shared HTTP call to Featherless with descriptive error handling."""
    async with httpx.AsyncClient(timeout=45) as http:
        response = await http.post(FEATHERLESS_BASE_URL, json=payload, headers=_build_headers())
        if response.status_code == 403:
            raise PermissionError(
                "Featherless returned 403 Forbidden. "
                "Check that your FEATHERLESS_API_KEY is valid and the model is not gated. "
                f"Model in use: {MODEL_NAME}"
            )
        response.raise_for_status()
        return response.json()


async def generate_investment_rationale(
    ticker: str,
    category: str,
    quantitative_data: dict,
    qualitative_research: str,
    risk_tolerance: str,
    interests: str,
) -> str:
    """Synthesizes financial data and qualitative research into a personalized pitch."""
    system_prompt = (
        "You are an expert financial advisor for Theme-Trader. Your job is to write a short, engaging, "
        "and personalized investment rationale (1-2 paragraphs) for a specific stock/asset. "
        "Combine the hard financial numbers with the qualitative research provided to pitch this to the user."
    )

    user_prompt = (
        f"Asset: {ticker} (Category: {category})\n"
        f"User's Interests: {interests}\n"
        f"User Risk Tolerance: {risk_tolerance}\n\n"
        f"Quantitative Data (Recent 6-month metrics):\n"
        f"- Projected CAGR / Return: {quantitative_data.get('projected_cagr', 'N/A')}\n"
        f"- Volatility: {quantitative_data.get('volatility', 'N/A')}\n\n"
        f"Qualitative Research (Recent News/Business Model):\n{qualitative_research}\n\n"
        "Write a compelling rationale on why the user should invest in this asset, "
        "tying together the financial metrics and the qualitative news/research. "
        "Keep it concise, professional, but exciting."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        data = await _post(payload)
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[llm_service] Error generating rationale for {ticker}: {e}")
        return "Rationale generation is temporarily unavailable."


async def parse_user_interests(raw_text: str) -> dict:
    """
    Sends the user's free-text description to the LLM and extracts structured
    investment interests and an inferred goal category.
    Returns: { "interests": "...", "investment_goals": "..." }
    """
    system_prompt = (
        "You are a financial onboarding assistant. Extract structured investment information "
        "from the user's free-text description. "
        "Respond with ONLY a valid JSON object — no markdown, no explanation — containing exactly two keys:\n"
        '  "interests": a concise comma-separated list of investment themes (e.g. "AI, clean energy, healthcare")\n'
        '  "investment_goals": one of "Growth", "Income", or "Preservation" based on what the user describes.\n'
        "If the text is vague, make a reasonable inference."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": raw_text},
        ],
        "temperature": 0.3,
        "max_tokens": 120,
    }

    try:
        data = await _post(payload)
        content = data["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences if the model wraps the JSON
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        print(f"[llm_service] Error parsing user interests: {e}")
        # Graceful fallback: return the raw text as interests
        return {"interests": raw_text, "investment_goals": "Growth"}


async def generate_stock_universe(interests: str, risk_tolerance: str) -> dict:
    """
    Sends the user's inferred interests and risk tolerance to the LLM to generate
    a tailored universe of stock tickers.
    Returns: {
        "ETF": ["TICKER1", ...],
        "Blue Chip": [...],
        "IPO": [...],
        "Rising Star": [...]
    }
    """
    system_prompt = (
        "You are an expert financial analyst. Your task is to recommend a universe of US stock tickers "
        "tailored to the user's specific investment interests and risk tolerance. "
        "Return ONLY a valid JSON object mapping these exact keys to a list of string tickers (at least 5 per category, max 10):\n"
        '  "ETF", "Blue Chip", "IPO", "Rising Star"\n'
        "Do not include any explanation or markdown formatting."
    )

    user_prompt = f"User Interests: {interests}\nUser Risk Tolerance: {risk_tolerance}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 300,
    }

    try:
        data = await _post(payload)
        content = data["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences if the model wraps the JSON
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        print(f"[llm_service] Error generating stock universe: {e}")
        # Fallback to a sensible hardcoded universe if LLM fails
        return {
            "ETF":         ["SPY", "QQQ", "VTI", "VOO", "SCHD", "ARKK", "DIA", "IWM"],
            "Blue Chip":   ["AAPL", "MSFT", "JNJ", "PG", "JPM", "V", "WMT", "KO", "PEP", "MCD"],
            "IPO":         ["HOOD", "COIN", "RBLX", "RDDT", "ARM", "CART", "KVUE"],
            "Rising Star": ["NVDA", "AMD", "SMCI", "PLTR", "CRWD", "SNOW", "TSLA", "META"],
        }
