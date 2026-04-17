# Theme-Trader Backend Setup Guide

This backend uses `uv`, an extremely fast Python package and project manager.

## Quick Start Guide for Group Members

### 1. Install `uv` (if you don't have it)
If you haven't installed `uv` globally on your machine, you can install it via curl (Mac/Linux) or pip:
```bash
pip install uv
```
*(Or check the official docs for Windows installation: https://docs.astral.sh/uv/getting-started/installation/)*

### 2. Sync the Environment
Navigate into the `backend/` directory. You do not need to create a virtual environment manually! Just run:
```bash
uv sync
```
This command reads the `uv.lock` file and perfectly recreates the environment, installing all dependencies like `fastapi`, `sqlalchemy`, `yfinance`, `openai`, and `tavily-python`. 

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in the required API keys (Alpaca, Tavily, Featherless/LM Studio).

### 4. Running the Server
To run the FastAPI server, use `uv run`. This automatically uses the isolated environment:
```bash
uv run uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

### 5. Utility Scripts (Testing & Seeding)
We have included some utility scripts to help with development and testing:

**Seed the Database**
To instantly populate the SQLite database with 50 fake users (with varied hobbies and risk tolerances):
```bash
uv run seed_db.py
```

**Run Integration Tests**
To verify the CRUD endpoints, the WebSocket connection, and the AI Assessment pipeline:
```bash
uv run test_endpoints.py
```
*(Test output will be logged to the console and to a local `test_run.log` file.)*

## Core Features Implemented
- **`/api/assess`**: The core generative pipeline. It selects a portfolio using `yfinance` data, fetches qualitative company news via the **Tavily API**, and synthesizes an investment pitch using the **Featherless LLM** (or local LM Studio).
- **Caching (`cache_service.py`)**: All LLM and Tavily API calls are cached in the SQLite database for 24 hours to prevent API rate limits and drastically improve speed during demonstrations.
- **`/ws/prices`**: Real-time market data streamed directly to the frontend via Alpaca WebSockets.
- **CRUD Operations**: Secure endpoints to manage users, portfolios, and AI-generated assets.

### Adding New Packages
If you need to add a new package (for example, `pandas`), do NOT use `pip install`. Instead, use:
```bash
uv add pandas
```
