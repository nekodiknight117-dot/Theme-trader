import os
from tavily import TavilyClient

def get_company_research(ticker: str, category: str) -> str:
    """
    Uses the Tavily API to search for recent qualitative news, unique products,
    and business model advantages for a given stock ticker.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "your_tavily_api_key_here":
        return "Tavily API key not configured. Qualitative research skipped."

    client = TavilyClient(api_key=api_key)
    
    # Construct a targeted query based on the category
    query = f"Recent news, innovative products, and competitive business advantages for {ticker} stock."
    if category == "IPO":
        query = f"Recent IPO news, market reception, and future growth prospects for {ticker} stock."
    elif category == "Rising Star":
        query = f"Reasons for recent explosive growth, new market capture, and technological advantages for {ticker} stock."
        
    try:
        # We use the search method to get a concise summary or context
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=3,
            include_answer=True
        )
        # Tavily's 'answer' field usually contains a solid LLM-generated summary of the results
        if "answer" in response and response["answer"]:
            return response["answer"]
        
        # Fallback to combining snippets if no direct answer is provided
        snippets = [result.get("content", "") for result in response.get("results", [])]
        return " ".join(snippets)
        
    except Exception as e:
        print(f"Error fetching Tavily research for {ticker}: {e}")
        return "Could not fetch qualitative research at this time."
