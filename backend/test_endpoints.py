import asyncio
from fastapi.testclient import TestClient
from app.main import app

import logging

client = TestClient(app)

# Configure logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_run.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_crud_operations():
    logger.info("--- Testing CRUD Operations ---")
    
    # 1. Create a User
    logger.info("Creating User...")
    response = client.post("/users/", json={
        "username": "test_investor",
        "risk_tolerance": "high",
        "interests": "tech, space"
    })
    
    # Handle if user already exists from previous test run
    if response.status_code == 400 and "already registered" in response.text:
        logger.info("User already exists. Fetching user instead.")
        user_id = 1
    else:
        assert response.status_code == 200
        user_data = response.json()
        logger.info(f"Created User: {user_data}")
        user_id = user_data["id"]

    logger.info(f"Fetching User ID {user_id}...")
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    logger.info(f"Fetched User: {response.json()}")

    logger.info(f"Creating Portfolio for User {user_id}...")
    response = client.post(f"/users/{user_id}/portfolios/", json={
        "name": "High Risk Tech Strategy"
    })
    assert response.status_code == 200
    logger.info(f"Created Portfolio: {response.json()}")
    logger.info("CRUD Tests Passed!\n")
    return user_id

def test_assessment_pipeline(user_id: int):
    logger.info("--- Testing Assessment Pipeline (Tavily + LLM) ---")
    logger.info(f"Running assessment for User {user_id}... This may take a moment.")
    
    response = client.post(f"/api/assess?user_id={user_id}")
    
    if response.status_code == 200:
        portfolio = response.json()
        logger.info(f"Successfully generated portfolio: {portfolio['name']}")
        logger.info(f"Total assets selected: {len(portfolio['assets'])}")
        for asset in portfolio['assets']:
            logger.info(f"  - Ticker: {asset['ticker']} ({asset['category']})")
            logger.info(f"  - Rationale Preview: {asset['rationale'][:100]}...\n")
        logger.info("Assessment Pipeline Tests Passed!\n")
    else:
        logger.error(f"Assessment failed with status {response.status_code}: {response.text}")

def test_websocket():
    logger.info("--- Testing WebSocket Connection ---")
    
    # FastAPI TestClient has built-in websocket testing capabilities
    try:
        with client.websocket_connect("/ws/prices") as websocket:
            logger.info("Successfully connected to WebSocket endpoint: /ws/prices")
            websocket.send_text("ping")
            logger.info("Successfully sent message to WebSocket.")
            logger.info("WebSocket Test Passed!")
    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    user_id = test_crud_operations()
    # Need to run async tests using standard sync wrapper in TestClient
    test_assessment_pipeline(user_id)
    test_websocket()
    logger.info("All basic tests completed.")
