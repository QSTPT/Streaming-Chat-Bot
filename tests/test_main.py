from fastapi.testclient import TestClient
from app.main import app

# Create a test client wrapping your FastAPI app
client = TestClient(app)

def test_app_imports_and_loads():
    assert app is not None

def test_signup_endpoint_structure():
    response = client.post("/sign_up", json={})
    assert response.status_code in [400, 422]