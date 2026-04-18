import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv('../.env')

async def test():
    async with httpx.AsyncClient() as c:
        r = await c.post('https://api.featherless.ai/v1/chat/completions', headers={'Authorization': 'Bearer ' + os.getenv('FEATHERLESS_API_KEY', '')}, json={'model': 'google/gemma-4-31B-it', 'messages': [{'role': 'system', 'content': 'You are helpful'}, {'role': 'user', 'content': 'hi'}]})
        print(r.status_code, r.text)

asyncio.run(test())
