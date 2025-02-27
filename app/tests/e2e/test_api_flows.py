"""
@file: test_api_flows.py
@description:
This module implements end-to-end (e2e) tests for the BadBeats Backend API using Playwright.
These tests simulate real user or client interactions with the running FastAPI application
to ensure that the core workflows function as expected in a production-like environment.

@dependencies:
- pytest: For the test framework
- pytest-asyncio: For async test support, if needed
- playwright: For browser-based end-to-end testing (Python bindings)
- app.main: The main FastAPI application (the server must be running before testing)

@notes:
- These tests assume the server is running locally at http://localhost:8000.
- Adjust BASE_URL if your server runs at a different address or port.
- Before running, install dependencies:
    pip install playwright pytest-playwright
    playwright install

Tested flows:
1. Server Health Check
2. Authentication (login, token usage)
3. Predictions Access (list, create)
4. Negative tests (unauthorized access, invalid data)
"""

import os
import json
import pytest
from playwright.sync_api import Page, sync_playwright

# You may adjust this based on your local environment
BASE_URL = os.getenv("BADBEATS_BASE_URL", "http://localhost:8000")

@pytest.fixture(scope="session")
def playwright_browser():
    """
    A pytest fixture to manage the Playwright Browser lifecycle.
    Installs and launches the browser for the session, then closes it.
    """
    with sync_playwright() as pw:
        # Launch the browser (Chromium by default)
        browser = pw.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture()
def page_context(playwright_browser):
    """
    A pytest fixture providing a fresh browser context (incognito-like) for each test.
    This ensures tests are isolated.
    """
    context = playwright_browser.new_context()
    page = context.new_page()
    yield page
    context.close()

@pytest.mark.e2e
def test_server_health_check(page_context: Page):
    """
    End-to-end test:
    1. Validate that the server root (/) is reachable and returns a 200 status.
    2. Validate that /api/v1/health returns the expected JSON payload.
    """
    # 1. Check the root endpoint
    main_response = page_context.goto(f"{BASE_URL}/")
    # page.goto(...) returns a playwright.sync_api.Response or None
    assert main_response is not None, "Failed to navigate to root endpoint (/) - got None."
    assert main_response.ok, f"Root endpoint returned a non-OK status: {main_response.status}"

    # 2. Check the /api/v1/health endpoint
    # We'll do another goto() call. This endpoint presumably returns JSON.
    health_response = page_context.goto(f"{BASE_URL}/api/v1/health")
    assert health_response is not None, (
        "Failed to navigate to /api/v1/health - got None."
    )
    assert health_response.ok, (
        f"Health check endpoint returned a non-OK status: {health_response.status}"
    )

    # If the response is JSON, we can parse it (playwright's .json() method).
    health_data = health_response.json()
    # Typically we expect something like {"status": "OK", "message": "..."}
    assert health_data.get("status") == "OK", (
        "Health check JSON did not have status == 'OK'. "
        f"Response content: {health_data}"
    )



@pytest.mark.e2e
def test_login_and_access_protected_route(page_context: Page):
    """
    End-to-end test:
    1. Attempt to log in with valid credentials.
    2. Retrieve and parse the JWT access token from the response.
    3. Use the token to access /api/v1/predictions (protected route).
    4. Ensure the request is successful and data is returned.
    5. Try again with an invalid token to ensure it fails (401).
    """
    # 1. Attempt to log in
    login_url = f"{BASE_URL}/api/v1/auth/login"
    # We can do an XHR/fetch request using the page API.
    # However, we can also use page_context.request for simpler REST calls in Playwright.
    
    # In Playwright Python, we can do:
    login_response = page_context.request.post(
        login_url,
        form={
            "username": "user",
            "password": "userpassword"
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    assert login_response.status == 200, f"Login attempt failed: {login_response.status} {login_response.text()}"

    
    token_data = login_response.json()
    assert "access_token" in token_data, "No 'access_token' found in login response."
    access_token = token_data["access_token"]
    assert token_data["token_type"] == "bearer", "Token type is not 'bearer'."
    
    # 2. Use the token to access predictions
    predictions_url = f"{BASE_URL}/api/v1/predictions"
    predictions_resp = page_context.request.get(
        predictions_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert predictions_resp.status == 200, "Failed to access protected /api/v1/predictions route with valid token."
    predictions_data = predictions_resp.json()
    assert "picks" in predictions_data, "Expected 'picks' field in predictions response."

    # 3. Attempt the same request with an invalid token => should fail
    invalid_resp = page_context.request.get(
        predictions_url,
        headers={"Authorization": "Bearer invalid_token_12345"}
    )
    assert invalid_resp.status == 401, "Invalid token request did not yield 401 Unauthorized."


@pytest.mark.e2e
def test_create_prediction_flow(page_context: Page):
    """
    End-to-end test:
    1. Log in and obtain a valid token.
    2. Create a new prediction using the /api/v1/predictions endpoint (POST).
    3. Validate that the response returns the newly created prediction.
    4. Retrieve the list again to ensure it includes the new prediction.
    5. Edge case: Attempt to create with invalid confidence => expect validation error (422).
    """
    login_url = f"{BASE_URL}/api/v1/auth/login"
    create_url = f"{BASE_URL}/api/v1/predictions"
    
    # Log in
    login_response = page_context.request.post(
        login_url,
        form={
            "username": "user",
            "password": "userpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status == 200, f"Login attempt failed: {login_response.status} {login_response.text()}"

    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # 1. Valid create
    prediction_body = {
        "agent_id": "test-agent-e2e",
        "game_id": 99999,  # Arbitrary game ID for testing
        "pick": "TestTeam -6",
        "logic": "This is an automated e2e test pick.",
        "confidence": 0.7,
        "result": "pending"
    }

    create_response = page_context.request.post(
        create_url,
        data=json.dumps(prediction_body),  # Manually serialize to JSON
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    assert create_response.status == 201, (
        f"Creating a new prediction failed unexpectedly: "
        f"{create_response.status} {create_response.text()}"
    )
    created_data = create_response.json()
    assert created_data["game_id"] == 99999, "Game ID mismatch in created prediction."

    assert created_data["pick"] == "TestTeam -6", "Pick mismatch in created prediction."
    assert created_data["confidence"] == 0.7, "Confidence mismatch in created prediction."
    
    # 2. Verify by listing predictions
    predictions_url = f"{BASE_URL}/api/v1/predictions"
    list_response = page_context.request.get(
        predictions_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert list_response.status == 200, "Listing predictions failed unexpectedly."
    all_picks = list_response.json()["picks"]
    # We expect to find the new pick
    matching_picks = [p for p in all_picks if p["game_id"] == 99999 and p["pick"] == "TestTeam -6"]
    assert len(matching_picks) > 0, "Newly created prediction not found in predictions list."
    
    # 3. Edge case: invalid confidence
    invalid_body = dict(prediction_body)
    invalid_body["confidence"] = 1.5  # Out of valid range [0..1]
    invalid_create = page_context.request.post(
        create_url,
        data=json.dumps(invalid_body),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    assert invalid_create.status == 422, (
        "Creating a prediction with invalid confidence > 1.0 "
        "should yield 422 Unprocessable Entity."
    )


@pytest.mark.e2e
def test_unauthorized_flow(page_context: Page):
    """
    End-to-end test:
    1. Attempt to access predictions endpoint without any token => expect 401 Unauthorized.
    2. Attempt to create a prediction without any token => expect 401 Unauthorized.
    """
    predictions_url = f"{BASE_URL}/api/v1/predictions"
    
    # GET predictions without a token
    resp_no_token = page_context.request.get(predictions_url)
    assert resp_no_token.status == 401, (
        "Accessing /api/v1/predictions without token should yield 401 Unauthorized."
    )
    
    # POST create prediction without a token
    create_resp = page_context.request.post(
        predictions_url,
        data=json.dumps({
            "agent_id": "test-agent-unauthorized",
            "game_id": 100000,
            "pick": "UnauthorizedTeam +2",
            "logic": "Should not be created",
            "confidence": 0.6,
            "result": "pending"
        }),
        headers={
            "Content-Type": "application/json"
        }
    )
    assert create_resp.status == 401, (
        "Creating a prediction without token should yield 401 Unauthorized."
    )
