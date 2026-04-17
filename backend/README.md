# Theme-Trader Backend Setup Guide

This backend uses `uv`, an extremely fast Python package and project manager.

## Why `uv`?
It is significantly faster than `pip` and handles virtual environments, python versions, and dependencies all in one tool seamlessly. 

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
This command reads the `uv.lock` file and perfectly recreates the environment, installing all dependencies like `fastapi`, `sqlalchemy`, and `yfinance`. 

### 3. Running the Server
To run the FastAPI server, you prefix your command with `uv run`. This automatically uses the isolated environment without you needing to manually "activate" it:
```bash
uv run uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

### 4. Adding New Packages
If you need to add a new package (for example, `pandas`), do NOT use `pip install`. Instead, use:
```bash
uv add pandas
```
This updates the `pyproject.toml` and `uv.lock` files automatically so the rest of the team gets it next time they run `uv sync`.

### 5. Running Scripts
To run any python script inside the environment:
```bash
uv run test_endpoints.py
```
