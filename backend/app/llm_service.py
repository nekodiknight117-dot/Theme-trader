import os
import json
import httpx
from pathlib import Path

# Explicitly load the root-level .env (two levels up: app/ -> backend/ -> project root)
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
try:
    import dotenv
    dotenv.load_dotenv(dotenv_path=_ROOT_ENV, override=True)
except ImportError:
    pass

featherless_key = os.getenv("FEATHERLESS_API_KEY", "")

if featherless_key and featherless_key != "your_featherless_api_key_here":
    BASE_URL   = "https://api.featherless.ai/v1/chat/completions"
    API_KEY    = featherless_key
    MODEL_NAME = "google/gemma-4-31B-it"
else:
    BASE_URL   = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1") + "/chat/completions"
    API_KEY    = os.getenv("OPENAI_API_KEY", "lm-studio")
    MODEL_NAME = "local-model"

provider = "Featherless" if "featherless" in BASE_URL else "LM Studio"
print(f"[llm_service] Using {provider} -> {BASE_URL} / {MODEL_NAME}")


async def generate_investment_rationale(
    ticker: str,
    category: str,
    quantitative_data: dict,
    qualitative_research: str,
    risk_tolerance: str,
) -> str:
    """Synthesizes financial data and qualitative research into a personalized pitch."""
    system_prompt = (
        "You are an expert financial advisor for Theme-Trader. Your job is to write a short, engaging, "
        "and personalized investment rationale (1-2 paragraphs) for a specific stock/asset. "
        "Combine the hard financial numbers with the qualitative research provided to pitch this to the user."
    )

    user_prompt = (
        f"Asset: {ticker} (Category: {category})\n"
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
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error generating LLM rationale for {ticker}: {e}")
        return "System was unable to generate a personalized rationale at this time."


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
            {"role": "user", "content": raw_text},
        ],
        "temperature": 0.3,
        "max_tokens": 120,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if the model wraps the JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
    except Exception as e:
        print(f"Error parsing user interests: {e}")
        # Graceful fallback: return the raw text as interests
        return {"interests": raw_text, "investment_goals": "Growth"}
