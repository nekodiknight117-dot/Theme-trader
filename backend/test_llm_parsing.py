"""
Focused tests that verify LLM text parsing works correctly with the API endpoints.
All tests mock the LLM client and stock-selector so no external services are needed.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ── Helpers ──────────────────────────────────────────────────────────────────

def _featherless_json(content: str) -> dict:
    """Minimal Featherless / OpenAI-compatible chat completion JSON."""
    return {"choices": [{"message": {"content": content}}]}


def _make_async_llm(content: str):
    """Mock ``llm_service._post`` returning a successful completion body."""
    return AsyncMock(return_value=_featherless_json(content))


def _make_error_llm(message: str = "LLM offline"):
    """Mock ``llm_service._post`` raising (simulates network / API failure)."""
    return AsyncMock(side_effect=Exception(message))


# Fake portfolio from stock selector — avoids every yfinance network call
FAKE_PORTFOLIO = [
    {"ticker": "NVDA", "category": "Rising Star", "projected_cagr": 0.9,  "volatility": 0.35},
    {"ticker": "COIN", "category": "IPO",         "projected_cagr": 0.6,  "volatility": 0.50},
    {"ticker": "AAPL", "category": "Blue Chip",   "projected_cagr": 0.2,  "volatility": 0.15},
]


def _fresh_db():
    """
    Create a brand-new in-memory SQLite engine + session factory for one test.
    StaticPool forces all sessions to reuse the same connection so the tables
    created by create_all() stay visible to every subsequent query.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def _make_test_client(llm_mock, engine, SessionLocal):
    """Wire up a TestClient with overridden DB and mocked LLM/Tavily/selector."""
    from app import models
    from app.database import get_db
    from app.main import app

    models.Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app, override_get_db


def _seed_user(client, risk_tolerance="high"):
    import time
    username = f"llm_test_{int(time.time() * 1_000_000)}"
    resp = client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "secret12",
            "risk_tolerance": risk_tolerance,
            "interests": "AI, tech",
        },
    )
    assert resp.status_code == 200, f"User seed failed: {resp.text}"
    data = resp.json()
    return data["user"]["id"], data["access_token"]


# ── Unit tests: llm_service.generate_investment_rationale ────────────────────

class TestLLMTextParsing:
    """Verify that generate_investment_rationale parses LLM output correctly."""

    def _call(self, coro):
        return asyncio.run(coro)

    def _invoke(self, llm_mock, **kwargs):
        from app.llm_service import generate_investment_rationale
        defaults = dict(
            ticker="NVDA",
            category="Rising Star",
            quantitative_data={"projected_cagr": 0.45, "volatility": 0.30},
            qualitative_research="NVDA leads in AI GPUs.",
            risk_tolerance="high",
            interests="AI, GPUs",
        )
        defaults.update(kwargs)
        with patch("app.llm_service._post", llm_mock):
            return self._call(generate_investment_rationale(**defaults))

    def test_returns_stripped_text(self):
        """Leading/trailing whitespace from the LLM response is stripped."""
        raw = "  \n  NVDA is a powerhouse in AI chips.  \n  "
        result = self._invoke(_make_async_llm(raw))
        assert result == raw.strip(), f"Got: {repr(result)}"
        print(f"[PASS] stripped text -> {repr(result[:60])}")

    def test_multi_paragraph_response_preserved(self):
        """Multi-paragraph LLM output is returned intact (newlines kept)."""
        raw = (
            "NVDA continues to dominate AI workloads.\n\n"
            "With Blackwell GPU shipments accelerating, the outlook is bullish."
        )
        result = self._invoke(_make_async_llm(raw))
        assert "\n\n" in result, "Paragraph separation should be preserved"
        assert result == raw.strip()
        print(f"[PASS] multi-paragraph preserved ({len(result)} chars)")

    def test_fallback_on_exception(self):
        """When the LLM call raises, the fallback string is returned."""
        result = self._invoke(_make_error_llm("Connection refused"),
                              ticker="AAPL", category="Blue Chip",
                              risk_tolerance="low")
        assert result == "Rationale generation is temporarily unavailable."
        print(f"[PASS] fallback returned correctly on exception")

    def test_empty_string_response_handled(self):
        """An empty LLM response does not crash and returns a string."""
        result = self._invoke(_make_async_llm(""),
                              ticker="SPY", category="ETF", risk_tolerance="low")
        assert isinstance(result, str)
        print(f"[PASS] empty LLM response handled gracefully: {repr(result)}")

    def test_unicode_and_special_chars_preserved(self):
        """Special characters and unicode in LLM output pass through unchanged."""
        raw = "NVDA's Q4 earnings beat by 20% — a 'once-in-a-decade' opportunity. 🚀"
        result = self._invoke(_make_async_llm(raw))
        assert result == raw
        print(f"[PASS] unicode/special chars preserved: {repr(result[:60])}")

    def test_long_response_returned_in_full(self):
        """A response longer than typical max_tokens is still returned untruncated."""
        raw = "NVDA. " * 200  # ~1200 chars
        result = self._invoke(_make_async_llm(raw))
        assert result == raw.strip()
        print(f"[PASS] long response ({len(result)} chars) returned in full")


# ── Integration tests: /api/assess endpoint with mocked LLM ──────────────────

class TestAssessEndpointLLMParsing:
    """
    Verify that /api/assess correctly pipes LLM text into the portfolio response.
    Each test gets its own isolated in-memory database so there is no cache bleed.
    """

    def _run_assess(self, llm_mock, risk_tolerance="high"):
        engine, SessionLocal = _fresh_db()
        app, _ = _make_test_client(llm_mock, engine, SessionLocal)
        with patch("app.llm_service._post", llm_mock), \
             patch("app.tavily_research.get_company_research",
                   return_value="Mocked qualitative research."), \
             patch("app.main.get_algorithmic_portfolio",
                   return_value=FAKE_PORTFOLIO), \
             TestClient(app) as client:
            _user_id, token = _seed_user(client, risk_tolerance)
            return client.post(
                "/api/assess",
                headers={"Authorization": f"Bearer {token}"},
            )

    def test_llm_rationale_appears_in_portfolio_assets(self):
        """Rationale text from the mocked LLM should appear in every asset."""
        RATIONALE = (
            "NVDA is perfectly positioned for the AI revolution. "
            "Strong buy for high-risk investors."
        )
        resp = self._run_assess(_make_async_llm(RATIONALE))

        assert resp.status_code == 200, f"Assess failed: {resp.text}"
        portfolio = resp.json()
        assert len(portfolio["assets"]) == len(FAKE_PORTFOLIO)

        for asset in portfolio["assets"]:
            assert asset["rationale"] == RATIONALE, (
                f"Ticker {asset['ticker']}: got {repr(asset['rationale'])}"
            )
            print(f"[PASS] {asset['ticker']} ({asset['category']}): rationale parsed correctly")

    def test_whitespace_stripped_rationale_stored_in_db(self):
        """Whitespace stripped by generate_investment_rationale flows into the API response."""
        RAW      = "\n  Buy AAPL. It's a safe long-term hold.  \n"
        STRIPPED = RAW.strip()

        resp = self._run_assess(_make_async_llm(RAW), risk_tolerance="low")

        assert resp.status_code == 200
        for asset in resp.json()["assets"]:
            assert asset["rationale"] == STRIPPED, (
                f"Expected stripped rationale for {asset['ticker']}, "
                f"got: {repr(asset['rationale'])}"
            )
        print(f"[PASS] whitespace stripping reflected end-to-end")

    def test_fallback_rationale_on_llm_error(self):
        """When LLM errors, the fallback string appears in every API response asset."""
        FALLBACK = "Rationale generation is temporarily unavailable."

        resp = self._run_assess(_make_error_llm("LLM offline"))

        assert resp.status_code == 200
        for asset in resp.json()["assets"]:
            assert asset["rationale"] == FALLBACK, (
                f"Ticker {asset['ticker']}: got {repr(asset['rationale'])}"
            )
        print(f"[PASS] fallback rationale stored and returned via API on LLM error")

    def test_portfolio_structure_intact_with_llm_content(self):
        """The full portfolio schema (id, user_id, name, assets) is returned correctly."""
        resp = self._run_assess(_make_async_llm("A solid buy."))

        assert resp.status_code == 200
        p = resp.json()
        assert "id" in p and "user_id" in p and "name" in p and "assets" in p
        assert isinstance(p["assets"], list)
        for asset in p["assets"]:
            assert "ticker" in asset
            assert "category" in asset
            assert "rationale" in asset
            assert asset["rationale"] == "A solid buy."
        print(f"[PASS] portfolio schema intact with LLM content "
              f"({len(p['assets'])} assets)")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback

    unit_suite        = TestLLMTextParsing()
    integration_suite = TestAssessEndpointLLMParsing()

    unit_tests = [
        unit_suite.test_returns_stripped_text,
        unit_suite.test_multi_paragraph_response_preserved,
        unit_suite.test_fallback_on_exception,
        unit_suite.test_empty_string_response_handled,
        unit_suite.test_unicode_and_special_chars_preserved,
        unit_suite.test_long_response_returned_in_full,
    ]

    integration_tests = [
        integration_suite.test_llm_rationale_appears_in_portfolio_assets,
        integration_suite.test_whitespace_stripped_rationale_stored_in_db,
        integration_suite.test_fallback_rationale_on_llm_error,
        integration_suite.test_portfolio_structure_intact_with_llm_content,
    ]

    passed = failed = 0

    print("\n" + "=" * 60)
    print("UNIT TESTS — LLM Text Parsing (llm_service.py)")
    print("=" * 60)
    for test in unit_tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print("INTEGRATION TESTS — /api/assess endpoint with mocked LLM")
    print("=" * 60)
    for test in integration_tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
