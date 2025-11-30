import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_poke_client, get_translation_client
from app.clients.pokeapi_client import PokeAPIClient
from app.clients.translation_client import TranslationClient
from fakeredis.aioredis import FakeRedis

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

# Create fake Redis clients that will be reused across tests
@pytest.fixture(scope="function")
def fake_redis():
    """Provides a fresh fake Redis instance for each test."""
    return FakeRedis(decode_responses=True)

@pytest.fixture(scope="function")
def test_client(fake_redis):
    """
    Provides a TestClient with dependency overrides to use fake Redis.
    This prevents tests from trying to connect to real Redis.
    """
    # Create clients with fake Redis
    poke_client = PokeAPIClient()
    poke_client.redis = fake_redis
    
    translation_client = TranslationClient()
    translation_client.redis = fake_redis
    
    # Override the dependencies to return our fake-Redis clients
    app.dependency_overrides[get_poke_client] = lambda: poke_client
    app.dependency_overrides[get_translation_client] = lambda: translation_client
    
    # Create the test client
    with TestClient(app) as client:
        yield client
    
    # Cleanup: Clear dependency overrides after test
    app.dependency_overrides.clear()


@pytest.mark.httpx_mock
def test_e2e_get_basic_info_success(httpx_mock, test_client):
    """
    E2E test for Endpoint 1: Verify the /pokemon/{name} endpoint.
    """
    # Arrange Mocks
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        json=MOCK_POKEAPI_SUCCESS,
        status_code=200
    )

    # Act (Hit the public API endpoint)
    response = test_client.get("/pokemon/mewtwo")

    # Assert
    assert response.status_code == 200
    assert response.json()["name"] == "mewtwo"
    assert "scientist" in response.json()["description"] # Original English description
    assert response.json()["is_legendary"] is True


@pytest.mark.httpx_mock
def test_e2e_get_translated_info_yoda_rule(httpx_mock, test_client):
    """
    E2E test for Endpoint 2: Verify Yoda translation rule and response structure.
    """
    # Arrange Mocks for two external calls
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

    # Act (Hit the public API endpoint)
    response = test_client.get("/pokemon/mewtwo/translated")

    # Assert
    assert response.status_code == 200
    assert response.json()["name"] == "mewtwo"
    assert "Created by scientist, it was." == response.json()["description"] # Translated text
    assert response.json()["habitat"] == "cave" # Habitat check for the rule


@pytest.mark.httpx_mock
def test_e2e_translation_rate_limit_error(httpx_mock, test_client):
    """
    E2E test: Verify that a 429 from the Translation API is mapped to a public 503.
    This tests the exception handling in app/main.py.
    """
    # Arrange Mocks
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

    # Act
    response = test_client.get("/pokemon/mewtwo/translated")

    # Assert
    assert response.status_code == 503 # Must be 503 Service Unavailable
    assert "rate limit" in response.json()["detail"].lower()