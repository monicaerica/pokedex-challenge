import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_poke_client, get_translation_client
import httpx
from unittest.mock import patch
from app.clients.translation_client import TranslationClient

# Use the TestClient provided by FastAPI
client = TestClient(app)

# Mock data for external APIs
MOCK_POKEAPI_SUCCESS = {
    "name": "mewtwo",
    "is_legendary": True,
    "habitat": {"name": "cave"}, # Will trigger Yoda rule
    "flavor_text_entries": [
        {"flavor_text": "It was created by a scientist.", "language": {"name": "en"}}
    ]
}

MOCK_TRANSLATION_YODA = {
    "success": {"total": 1},
    "contents": {
        "translated": "Created by scientist, it was.",
        "text": "It was created by a scientist.",
        "translation": "yoda"
    }
}

MOCK_TRANSLATION_SHAKESPEARE = {
    "success": {"total": 1},
    "contents": {
        "translated": "Hark! It was created by a man of science.",
        "text": "It was created by a scientist.",
        "translation": "shakespeare"
    }
}

@pytest.mark.httpx_mock
def test_e2e_get_basic_info_success(httpx_mock):
    """
    E2E test for Endpoint 1: Verify the /pokemon/{name} endpoint.
    """
    
    # 1. Clear caches for test isolation
    poke_client = get_poke_client()
    translation_client = get_translation_client()
    poke_client.clear_cache()
    translation_client.clear_cache()

    # 2. Arrange Mocks
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        json=MOCK_POKEAPI_SUCCESS,
        status_code=200
    )

    # 3. Act (Hit the public API endpoint)
    response = client.get("/pokemon/mewtwo")

    # 4. Assert
    assert response.status_code == 200
    assert response.json()["name"] == "mewtwo"
    assert "scientist" in response.json()["description"] # Original English description
    assert response.json()["is_legendary"] is True


@pytest.mark.httpx_mock
def test_e2e_get_translated_info_yoda_rule(httpx_mock):
    """
    E2E test for Endpoint 2: Verify Yoda translation rule and response structure.
    """

    # 1. Clear caches for test isolation
    poke_client = get_poke_client()
    translation_client = get_translation_client()
    poke_client.clear_cache()
    translation_client.clear_cache()

    # 2. Arrange Mocks for two external calls
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        json=MOCK_POKEAPI_SUCCESS,
        status_code=200
    )
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/yoda",
        json=MOCK_TRANSLATION_YODA,
        status_code=200
    )

    # 3. Act (Hit the public API endpoint)
    response = client.get("/pokemon/mewtwo/translated")

    # 4. Assert
    assert response.status_code == 200
    assert response.json()["name"] == "mewtwo"
    assert "Created by scientist, it was." == response.json()["description"] # Translated text
    assert response.json()["habitat"] == "cave" # Habitat check for the rule


@pytest.mark.httpx_mock
def test_e2e_translation_rate_limit_error(httpx_mock):
    """
    E2E test: Verify that a 429 from the Translation API is mapped to a public 503.
    This tests the exception handling in app/main.py.
    """

    # 1. Clear caches for test isolation
    poke_client = get_poke_client()
    translation_client = get_translation_client()
    poke_client.clear_cache()
    translation_client.clear_cache()

    # 2. Arrange Mocks
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        json=MOCK_POKEAPI_SUCCESS,
        status_code=200
    )
    # The crucial part: Mock the translation call to fail with 429
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/yoda",
        status_code=429,
        json={"error": {"code": 429, "message": "Rate limit exceeded"}}
    )

    # 3. Act
    response = client.get("/pokemon/mewtwo/translated")

    # 4. Assert
    assert response.status_code == 503 # Must be 503 Service Unavailable
    assert "rate limit" in response.json()["detail"].lower()