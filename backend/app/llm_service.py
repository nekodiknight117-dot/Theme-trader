import os
from openai import AsyncOpenAI

# Determine which LLM provider to use based on env variables
featherless_key = os.getenv("FEATHERLESS_API_KEY")
if featherless_key and featherless_key != "your_featherless_api_key_here":
    # Use Featherless
    base_url = "https://api.featherless.ai/v1"
    api_key = featherless_key
    # Featherless supports many models, let's use a solid default instruction-following model
    # Note: You can change this to a specific model hosted on Featherless like 'meta-llama/Meta-Llama-3-8B-Instruct'
    MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct" 
else:
    # Fallback to local LM Studio
    base_url = os.getenv("OPENAI_BASE_URL", "http://146.245.228.220:1234/v1")
    api_key = os.getenv("OPENAI_API_KEY", "lm-studio")
    MODEL_NAME = "local-model" # LM Studio typically ignores the model name parameter

client = AsyncOpenAI(
    base_url=base_url,
    api_key=api_key
)

async def generate_investment_rationale(ticker: str, category: str, quantitative_data: dict, qualitative_research: str, risk_tolerance: str) -> str:
    """
    Synthesizes financial data and qualitative research into a personalized pitch.
    """
    system_prompt = (
        "You are an expert financial advisor for Theme-Trader. Your job is to write a short, engaging, "
        "and personalized investment rationale (1-2 paragraphs) for a specific stock/asset. "
        "Combine the hard financial numbers with the qualitative research provided to pitch this to the user."
    )
    
    user_prompt = f"""
    Asset: {ticker} (Category: {category})
    User Risk Tolerance: {risk_tolerance}
    
    Quantitative Data (Recent 6-month metrics):
    - Projected CAGR / Return: {quantitative_data.get('projected_cagr', 'N/A')}
    - Volatility: {quantitative_data.get('volatility', 'N/A')}
    
    Qualitative Research (Recent News/Business Model):
    {qualitative_research}
    
    Write a compelling rationale on why the user should invest in this asset, tying together the financial metrics and the qualitative news/research.
    Keep it concise, professional, but exciting.
    """
    
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating LLM rationale for {ticker}: {e}")
        return "System was unable to generate a personalized rationale at this time."
