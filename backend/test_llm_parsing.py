"""
Focused tests that verify LLM text parsing works correctly with the API endpoints.
All tests mock the LLM client and stock-selector so no external services are needed.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

# Allow importing llm_service without a real Featherless key (CI / dev without .env)
_featherless = os.getenv("FEATHERLESS_API_KEY", "")
if not _featherless or _featherless == "your_featherless_api_key_here":
    os.environ["FEATHERLESS_API_KEY"] = "test-featherless-key-for-pytest"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _featherless_json(content: str) -> dict:
    """Minimal Featherless / OpenAI-compatible chat completion JSON."""
    return {"choices": [{"message": {"content": content}}]}


def _make_async_llm(content: str):
    """Mock ``llm_service._post`` returning a successful completion body."""
    return AsyncMock(return_value=_featherless_json(content))


def _make_error_llm(message: str = "LLM offline"):
    """Mock ``llm_service._post`` raising (simulates network / API failure)."""
    return AsyncMock(side_effect=Exception(message))


FAKE_PORTFOLIO = [
    {"ticker": "NVDA", "category": "Rising Star", "projected_cagr": 0.9, "volatility": 0.35, "company_name": "NVIDIA"},
    {"ticker": "COIN", "category": "IPO", "projected_cagr": 0.6, "volatility": 0.50, "company_name": "Coinbase"},
    {"ticker": "AAPL", "category": "Blue Chip", "projected_cagr": 0.2, "volatility": 0.15, "company_name": "Apple"},
]


def _fresh_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def _make_test_client(llm_mock, engine, SessionLocal):
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


def _assess_llm_responses():
    """Two LLM completions per asset: financial, then theme."""
    out = []
    for a in FAKE_PORTFOLIO:
        t = a["ticker"]
        out.append(_featherless_json(f"fin-{t}"))
        out.append(_featherless_json(f"theme-{t}"))
    return out


class TestLLMTextParsing:
    """Verify that generate_financial_rationale parses LLM output correctly."""

    def _call(self, coro):
        return asyncio.run(coro)

    def _invoke(self, llm_mock, **kwargs):
        from app.llm_service import generate_financial_rationale
        defaults = dict(
            ticker="NVDA",
            category="Rising Star",
            quantitative_data={"projected_cagr": 0.45, "volatility": 0.30},
            qualitative_research="NVDA leads in AI GPUs.",
            risk_tolerance="high",
        )
        defaults.update(kwargs)
        with patch("app.llm_service._post", llm_mock):
            return self._call(generate_financial_rationale(**defaults))

    def test_returns_stripped_text(self):
        raw = "  \n  NVDA is a powerhouse in AI chips.  \n  "
        result = self._invoke(_make_async_llm(raw))
        assert result == raw.strip(), f"Got: {repr(result)}"

    def test_multi_paragraph_response_preserved(self):
        raw = (
            "NVDA continues to dominate AI workloads.\n\n"
            "With Blackwell GPU shipments accelerating, the outlook is bullish."
        )
        result = self._invoke(_make_async_llm(raw))
        assert "\n\n" in result
        assert result == raw.strip()

    def test_fallback_on_exception(self):
        from app.llm_service import FINANCIAL_UNAVAILABLE
        result = self._invoke(
            _make_error_llm("Connection refused"),
            ticker="AAPL",
            category="Blue Chip",
            risk_tolerance="low",
        )
        assert result == FINANCIAL_UNAVAILABLE

    def test_empty_string_response_handled(self):
        result = self._invoke(_make_async_llm(""), ticker="SPY", category="ETF", risk_tolerance="low")
        assert isinstance(result, str)

    def test_unicode_and_special_chars_preserved(self):
        raw = "NVDA's Q4 earnings beat by 20% — a 'once-in-a-decade' opportunity. 🚀"
        result = self._invoke(_make_async_llm(raw))
        assert result == raw

    def test_long_response_returned_in_full(self):
        raw = "NVDA. " * 200
        result = self._invoke(_make_async_llm(raw))
        assert result == raw.strip()


class TestAssessEndpointLLMParsing:
    def _run_assess(self, llm_mock, risk_tolerance="high"):
        engine, SessionLocal = _fresh_db()
        app, _ = _make_test_client(llm_mock, engine, SessionLocal)
        mock_portfolio = AsyncMock(return_value=FAKE_PORTFOLIO)
        with patch("app.llm_service._post", llm_mock), \
             patch("app.tavily_research.get_company_research",
                   return_value="Mocked qualitative research."), \
             patch("app.main.get_algorithmic_portfolio", mock_portfolio), \
             TestClient(app) as client:
            _user_id, token = _seed_user(client, risk_tolerance)
            return client.post(
                "/api/assess",
                headers={"Authorization": f"Bearer {token}"},
            )

    def test_llm_rationale_appears_in_portfolio_assets(self):
        llm_mock = AsyncMock(side_effect=_assess_llm_responses())
        resp = self._run_assess(llm_mock)

        assert resp.status_code == 200, f"Assess failed: {resp.text}"
        portfolio = resp.json()
        assert len(portfolio["assets"]) == len(FAKE_PORTFOLIO)

        by_ticker = {a["ticker"]: a for a in portfolio["assets"]}
        for fp in FAKE_PORTFOLIO:
            t = fp["ticker"]
            asset = by_ticker[t]
            assert asset["financial_rationale"] == f"fin-{t}", asset
            assert asset["theme_rationale"] == f"theme-{t}", asset

    def test_whitespace_stripped_rationale_stored_in_db(self):
        RAW = "\n  Buy AAPL. It's a safe long-term hold.  \n"
        STRIPPED = RAW.strip()
        responses = [_featherless_json(RAW), _featherless_json(RAW)] * len(FAKE_PORTFOLIO)
        llm_mock = AsyncMock(side_effect=responses)

        resp = self._run_assess(llm_mock, risk_tolerance="low")
        assert resp.status_code == 200
        for asset in resp.json()["assets"]:
            assert asset["financial_rationale"] == STRIPPED
            assert asset["theme_rationale"] == STRIPPED

    def test_fallback_rationale_on_llm_error(self):
        from app.llm_service import FINANCIAL_UNAVAILABLE, THEME_UNAVAILABLE
        llm_mock = _make_error_llm("LLM offline")
        resp = self._run_assess(llm_mock)
        assert resp.status_code == 200
        for asset in resp.json()["assets"]:
            assert asset["financial_rationale"] == FINANCIAL_UNAVAILABLE
            assert asset["theme_rationale"] == THEME_UNAVAILABLE
            assert "temporarily unavailable" in (asset.get("rationale") or "").lower()

    def test_portfolio_structure_intact_with_llm_content(self):
        responses = [_featherless_json("A solid buy.")] * (len(FAKE_PORTFOLIO) * 2)
        llm_mock = AsyncMock(side_effect=responses)
        resp = self._run_assess(llm_mock)
        assert resp.status_code == 200
        p = resp.json()
        assert "id" in p and "user_id" in p and "name" in p and "assets" in p
        for asset in p["assets"]:
            assert asset["financial_rationale"] == "A solid buy."
            assert asset["theme_rationale"] == "A solid buy."


if __name__ == "__main__":
    import traceback
    unit_suite = TestLLMTextParsing()
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
    print("UNIT TESTS — LLM (generate_financial_rationale)")
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
    print("INTEGRATION TESTS — /api/assess")
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
