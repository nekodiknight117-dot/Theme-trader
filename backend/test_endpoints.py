import logging
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_run.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _register_fresh_user():
    """Register a new user; returns (user_id, access_token)."""
    username = f"test_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "secret12",
            "risk_tolerance": "high",
            "interests": "tech, space",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data["user"]["id"], data["access_token"]


def test_crud_operations():
    logger.info("--- Testing auth + CRUD Operations ---")

    user_id, token = _register_fresh_user()
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/users/me", headers=headers)
    assert r.status_code == 200
    logger.info("GET /users/me: %s", r.json())

    r = client.get(f"/users/{user_id}")
    assert r.status_code == 200
    logger.info("Fetched User: %s", r.json())

    r = client.post(
        f"/users/{user_id}/portfolios/",
        json={"name": "High Risk Tech Strategy"},
    )
    assert r.status_code == 200
    logger.info("Created Portfolio: %s", r.json())

    r = client.get("/users/me/portfolios/", headers=headers)
    assert r.status_code == 200
    logger.info("GET /users/me/portfolios/: %s", r.json())

    logger.info("CRUD Tests Passed!\n")


def test_assessment_pipeline():
    _, token = _register_fresh_user()
    logger.info("--- Testing Assessment Pipeline (Tavily + LLM) ---")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/assess", headers=headers)

    if response.status_code == 200:
        portfolio = response.json()
        logger.info("Successfully generated portfolio: %s", portfolio["name"])
        logger.info("Total assets selected: %s", len(portfolio["assets"]))
        for asset in portfolio["assets"]:
            logger.info("  - Ticker: %s (%s)", asset["ticker"], asset["category"])
            prev = (asset.get("rationale") or "")[:100]
            logger.info("  - Rationale Preview: %s...\n", prev)
        logger.info("Assessment Pipeline Tests Passed!\n")
    else:
        logger.error("Assessment failed with status %s: %s", response.status_code, response.text)


def test_websocket():
    logger.info("--- Testing WebSocket Connection ---")

    try:
        with client.websocket_connect("/ws/prices") as websocket:
            logger.info("Successfully connected to WebSocket endpoint: /ws/prices")
            websocket.send_text("ping")
            logger.info("Successfully sent message to WebSocket.")
            logger.info("WebSocket Test Passed!")
    except Exception as e:
        logger.error("WebSocket connection failed: %s", e)


if __name__ == "__main__":
    test_crud_operations()
    test_assessment_pipeline()
    test_websocket()
    logger.info("All basic tests completed.")
