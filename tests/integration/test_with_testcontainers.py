import pytest
from fastapi.testclient import TestClient
from testcontainers.redis import RedisContainer
from app.main import app
from app.dependencies import get_poke_client, get_translation_client
from app.clients.pokeapi_client import PokeAPIClient
from app.clients.translation_client import TranslationClient
import redis.asyncio as redis


@pytest.fixture(scope="module")
def redis_container():
    """Start a real Redis container for integration tests."""
    with RedisContainer("redis:7-alpine") as container:
        yield container


@pytest.fixture(scope="module")
def redis_url(redis_container):
    """Get Redis connection URL from the container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}"


@pytest.fixture
def test_client(redis_url):
    """TestClient with real Redis from Testcontainers."""
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    poke_client = PokeAPIClient()
    poke_client.redis = redis_client
    
    translation_client = TranslationClient()
    translation_client.redis = redis_client
    
    app.dependency_overrides[get_poke_client] = lambda: poke_client
    app.dependency_overrides[get_translation_client] = lambda: translation_client
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.mark.httpx_mock
def test_integration_caching_with_real_redis(httpx_mock, test_client):
    """Test that caching works with real Redis container."""
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/pikachu",
        json={
            "name": "pikachu",
            "is_legendary": False,
            "habitat": {"name": "forest"},
            "flavor_text_entries": [
                {"flavor_text": "Electric mouse Pokemon.", "language": {"name": "en"}}
            ]
        },
        status_code=200
    )
    
    response1 = test_client.get("/pokemon/pikachu")
    assert response1.status_code == 200
    assert response1.json()["name"] == "pikachu"
    
    response2 = test_client.get("/pokemon/pikachu")
    assert response2.status_code == 200
    assert response2.json() == response1.json()


@pytest.mark.httpx_mock
def test_integration_translation_with_real_redis(httpx_mock, test_client):
    """Test translation endpoint with real Redis caching."""
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/ditto",
        json={
            "name": "ditto",
            "is_legendary": False,
            "habitat": {"name": "urban"},
            "flavor_text_entries": [
                {"flavor_text": "It can transform.", "language": {"name": "en"}}
            ]
        },
        status_code=200
    )
    
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/shakespeare",
        json={
            "success": {"total": 1},
            "contents": {
                "translated": "It can transform, verily.",
                "text": "It can transform.",
                "translation": "shakespeare"
            }
        },
        status_code=200
    )
    
    response = test_client.get("/pokemon/ditto/translated")
    assert response.status_code == 200
    assert "transform" in response.json()["description"].lower()


@pytest.mark.httpx_mock
def test_cache_persists_across_requests(httpx_mock, test_client):
    """Verify cached data persists in real Redis across multiple requests."""
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/bulbasaur",
        json={
            "name": "bulbasaur",
            "is_legendary": False,
            "habitat": {"name": "grassland"},
            "flavor_text_entries": [
                {"flavor_text": "A grass type Pokemon.", "language": {"name": "en"}}
            ]
        },
        status_code=200
    )
    
    # First request - caches data
    response1 = test_client.get("/pokemon/bulbasaur")
    assert response1.status_code == 200
    
    # Subsequent requests should use cache (httpx_mock would fail if called again)
    for _ in range(3):
        response = test_client.get("/pokemon/bulbasaur")
        assert response.status_code == 200
        assert response.json() == response1.json()


@pytest.mark.httpx_mock
def test_yoda_translation_for_legendary(httpx_mock, test_client):
    """Test Yoda translation is applied for legendary Pokemon with real Redis."""
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/articuno",
        json={
            "name": "articuno",
            "is_legendary": True,
            "habitat": {"name": "mountain"},
            "flavor_text_entries": [
                {"flavor_text": "A legendary bird Pokemon.", "language": {"name": "en"}}
            ]
        },
        status_code=200
    )
    
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/yoda",
        json={
            "success": {"total": 1},
            "contents": {
                "translated": "Legendary bird pokemon, a is.",
                "text": "A legendary bird Pokemon.",
                "translation": "yoda"
            }
        },
        status_code=200
    )
    
    response = test_client.get("/pokemon/articuno/translated")
    assert response.status_code == 200
    assert response.json()["is_legendary"] is True
    assert "legendary" in response.json()["description"].lower()


@pytest.mark.httpx_mock
def test_yoda_translation_for_cave_habitat(httpx_mock, test_client):
    """Test Yoda translation is applied for cave habitat Pokemon with real Redis."""
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/zubat",
        json={
            "name": "zubat",
            "is_legendary": False,
            "habitat": {"name": "cave"},
            "flavor_text_entries": [
                {"flavor_text": "Lives in dark caves.", "language": {"name": "en"}}
            ]
        },
        status_code=200
    )
    
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/yoda",
        json={
            "success": {"total": 1},
            "contents": {
                "translated": "In dark caves, lives.",
                "text": "Lives in dark caves.",
                "translation": "yoda"
            }
        },
        status_code=200
    )
    
    response = test_client.get("/pokemon/zubat/translated")
    assert response.status_code == 200
    assert response.json()["habitat"] == "cave"
    assert "caves" in response.json()["description"].lower()


@pytest.mark.httpx_mock
def test_translation_cache_works(httpx_mock, test_client):
    """Verify translation results are cached in real Redis."""
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/charmander",
        json={
            "name": "charmander",
            "is_legendary": False,
            "habitat": {"name": "mountain"},
            "flavor_text_entries": [
                {"flavor_text": "Fire type Pokemon.", "language": {"name": "en"}}
            ]
        },
        status_code=200
    )
    
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/shakespeare",
        json={
            "success": {"total": 1},
            "contents": {
                "translated": "Fire type Pokemon, forsooth.",
                "text": "Fire type Pokemon.",
                "translation": "shakespeare"
            }
        },
        status_code=200
    )
    
    # First call - caches both Pokemon data and translation
    response1 = test_client.get("/pokemon/charmander/translated")
    assert response1.status_code == 200
    
    # Second call - should use cached data (httpx_mock would fail if called again)
    response2 = test_client.get("/pokemon/charmander/translated")
    assert response2.status_code == 200
    assert response2.json() == response1.json()
