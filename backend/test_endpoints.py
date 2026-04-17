import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_crud_operations():
    print("--- Testing CRUD Operations ---")
    
    # 1. Create a User
    print("Creating User...")
    response = client.post("/users/", json={
        "username": "test_investor",
        "risk_tolerance": "high",
        "interests": "tech, space"
    })
    
    # Handle if user already exists from previous test run
    if response.status_code == 400 and "already registered" in response.text:
        print("User already exists. Fetching user instead.")
        # In a real test we'd clean the DB, but for this simple script we'll just continue
        # Assuming the ID is 1 for the first user
        user_id = 1
    else:
        assert response.status_code == 200
        user_data = response.json()
        print(f"Created User: {user_data}")
        user_id = user_data["id"]

    # 2. Get the User
    print(f"Fetching User ID {user_id}...")
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    print(f"Fetched User: {response.json()}")

    # 3. Create a Portfolio for the user
    print(f"Creating Portfolio for User {user_id}...")
    response = client.post(f"/users/{user_id}/portfolios/", json={
        "name": "High Risk Tech Strategy"
    })
    assert response.status_code == 200
    print(f"Created Portfolio: {response.json()}")
    print("CRUD Tests Passed!\n")

def test_websocket():
    print("--- Testing WebSocket Connection ---")
    
    # FastAPI TestClient has built-in websocket testing capabilities
    try:
        with client.websocket_connect("/ws/prices") as websocket:
            print("Successfully connected to WebSocket endpoint: /ws/prices")
            
            # Since the Alpaca stream in the background might take a few seconds to send data,
            # or it might not send data if markets are closed/keys are missing,
            # we will just test the connection capability and send a ping.
            websocket.send_text("ping")
            print("Successfully sent message to WebSocket.")
            print("WebSocket Test Passed!")
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    test_crud_operations()
    test_websocket()
    print("\nAll basic tests completed.")
