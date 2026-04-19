import asyncio
from app.llm_service import generate_stock_universe, generate_investment_rationale

async def test():
    print("Testing stock universe generation...")
    universe = await generate_stock_universe("AI and green energy", "high")
    print(f"Universe: {universe}")
    
    print("\nTesting rationale generation for NVDA...")
    rationale = await generate_investment_rationale(
        "NVDA",
        "Rising Star",
        {"projected_cagr": 0.5, "volatility": 0.4},
        "Nvidia is leading the AI chip market.",
        "high",
        "AI, semiconductors",
    )
    print(f"Rationale: {rationale}")

if __name__ == "__main__":
    asyncio.run(test())
