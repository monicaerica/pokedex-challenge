import pytest
import httpx
from app.clients.pokeapi_client import PokeAPIClient, APIClientError
from fastapi import HTTPException
from app.models import PokemonSpeciesData
from fakeredis.aioredis import FakeRedis


MOCK_POKEAPI_SUCCESS = {
    "name": "mewtwo",
    "is_legendary": True,
    "habitat": {"name": "rare"},
    "flavor_text_entries": [
        {"flavor_text": "Ceci est français.", "language": {"name": "fr"}},
        {"flavor_text": "It was created by a scientist after years of horrific gene splicing.", "language": {"name": "en"}}, # <-- We must extract this one
        {"flavor_text": "Esto es español.", "language": {"name": "es"}}
    ]
}

MOCK_POKEAPI_DITTO = {
    "name": "ditto",
    "is_legendary": False,
    "habitat": {"name": "urban"},
    "flavor_text_entries": [
        {"flavor_text": "It can transform into anything.", "language": {"name": "en"}}
    ]
}

@pytest.fixture
def redis_client():
    """Provides a fake Redis client for testing."""
    return FakeRedis(decode_responses=True)
    
@pytest.fixture
def poke_client(redis_client):
    """Provides a PokeAPIClient with fake Redis."""
    client = PokeAPIClient()
    client.redis = redis_client  # Inject fake Redis
    return client

@pytest.mark.asyncio
async def test_successful_fetch_and_data_extraction(httpx_mock, poke_client):
    """Verifies the client successfully extracts the English description and required fields."""
    # ARRANGE: Mock the external API call
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        json=MOCK_POKEAPI_SUCCESS,
        status_code=200
    )

    # ACT
    result = await poke_client.get_pokemon_species("mewtwo")

    # ASSERT: Check if the result matches our clean internal model
    assert isinstance(result, PokemonSpeciesData)
    assert result.name == "mewtwo"
    # CRUCIAL: Check that the correct English description was extracted
    assert "horrific gene splicing" in result.description
    assert result.habitat == "rare"
    assert result.is_legendary is True

@pytest.mark.asyncio
async def test_pokemon_not_found_raises_404(httpx_mock, poke_client):
    """Test that a 404 from PokeAPI is correctly re-mapped to a FastAPI 404."""
    # ARRANGE: Mock the external API to return a 404 Not Found
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/nonexistent",
        status_code=404
    )
    
    # ACT & ASSERT: Expect a standard FastAPI HTTPException with status 404
    with pytest.raises(HTTPException) as excinfo:
        await poke_client.get_pokemon_species("nonexistent")
    
    assert excinfo.value.status_code == 404

@pytest.mark.asyncio
async def test_pokeapi_internal_error_raises_503(httpx_mock, poke_client):
    """Test that a 500 from PokeAPI is correctly re-mapped to our custom 503 error."""
    # ARRANGE: Mock the external API to return a 500 Internal Server Error
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/internalerror",
        status_code=500
    )

    # ACT & ASSERT: Expect our custom APIClientError (HTTP 503)
    with pytest.raises(APIClientError) as excinfo:
        await poke_client.get_pokemon_species("internalerror")
    
    assert excinfo.value.status_code == 503

@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
@pytest.mark.asyncio
async def test_pokemon_caching_prevents_redundant_calls(httpx_mock, poke_client):
    """
    Verifies that calling get_pokemon_species() with the same name twice results in only 
    ONE network call, proving the cache is active.
    """
    mewtwo_call_count = [0]
    ditto_call_count = [0]
    
    def count_mewtwo(request):
        mewtwo_call_count[0] += 1
        return httpx.Response(
            status_code=200,
            json=MOCK_POKEAPI_SUCCESS
        )
    
    def count_ditto(request):
        ditto_call_count[0] += 1
        return httpx.Response(
            status_code=200,
            json=MOCK_POKEAPI_DITTO
        )

    # ARRANGE: Set up callbacks to count network calls
    httpx_mock.add_callback(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        callback=count_mewtwo,
    )
    
    httpx_mock.add_callback(
        url="https://pokeapi.co/api/v2/pokemon-species/ditto",
        callback=count_ditto,
    )

    # ACT 1: First call for mewtwo (cache miss - network call #1)
    result1 = await poke_client.get_pokemon_species("mewtwo")
    assert mewtwo_call_count[0] == 1
    assert result1.name == "mewtwo"

    # ACT 2: Second call for mewtwo with SAME name (cache hit - NO network call)
    result2 = await poke_client.get_pokemon_species("mewtwo")
    assert result2.name == result1.name
    assert result2.description == result1.description
    assert mewtwo_call_count[0] == 1  # Should still be 1!

    # ACT 3: Third call with DIFFERENT Pokemon (cache miss - network call for ditto)
    result3 = await poke_client.get_pokemon_species("ditto")
    assert result3.name == "ditto"
    assert ditto_call_count[0] == 1  # Ditto should have been called once
    assert mewtwo_call_count[0] == 1  # Mewtwo count should not have changed

@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
@pytest.mark.asyncio
async def test_pokemon_caching_is_case_insensitive(httpx_mock, poke_client):
    """
    Verifies that Pokemon names are cached in a case-insensitive manner.
    'Mewtwo', 'mewtwo', and 'MEWTWO' should all hit the same cache entry.
    """
    call_count = [0]
    
    def count_and_respond(request):
        call_count[0] += 1
        return httpx.Response(
            status_code=200,
            json=MOCK_POKEAPI_SUCCESS
        )

    # ARRANGE
    httpx_mock.add_callback(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        callback=count_and_respond,
    )

    # ACT: Call with different casings
    result1 = await poke_client.get_pokemon_species("Mewtwo")
    assert call_count[0] == 1

    result2 = await poke_client.get_pokemon_species("MEWTWO")
    assert call_count[0] == 1  # Should still be 1 (cache hit)

    result3 = await poke_client.get_pokemon_species("mewtwo")
    assert call_count[0] == 1  # Should still be 1 (cache hit)

    # All results should be identical
    assert result1.name == result2.name == result3.name

@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
@pytest.mark.asyncio
async def test_failed_requests_are_not_cached(httpx_mock, poke_client):
    """
    Verifies that failed requests (404, 500, network errors) are NOT cached,
    allowing retries on subsequent calls.
    """
    call_count = [0]
    
    def count_and_fail(request):
        call_count[0] += 1
        # First call returns 500, second call returns success
        if call_count[0] == 1:
            return httpx.Response(status_code=500, json={"error": "Internal error"})
        else:
            return httpx.Response(status_code=200, json=MOCK_POKEAPI_SUCCESS)

    # ARRANGE
    httpx_mock.add_callback(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        callback=count_and_fail,
    )

    # ACT 1: First call fails with 500
    with pytest.raises(APIClientError):
        await poke_client.get_pokemon_species("mewtwo")
    
    assert call_count[0] == 1

    # ACT 2: Second call should retry (not use cache) and succeed
    result = await poke_client.get_pokemon_species("mewtwo")
    assert call_count[0] == 2  # Network was called again
    assert result.name == "mewtwo"