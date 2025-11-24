import pytest
import httpx
from app.clients.pokeapi_client import PokeAPIClient, APIClientError
from fastapi import HTTPException
from app.models import PokemonSpeciesData


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

@pytest.mark.asyncio
async def test_successful_fetch_and_data_extraction(httpx_mock):
    """Verifies the client successfully extracts the English description and required fields."""
    # ARRANGE: Mock the external API call
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/mewtwo",
        json=MOCK_POKEAPI_SUCCESS,
        status_code=200
    )
    client = PokeAPIClient()

    # ACT
    result = await client.get_pokemon_species("mewtwo")

    # ASSERT: Check if the result matches our clean internal model
    assert isinstance(result, PokemonSpeciesData)
    assert result.name == "mewtwo"
    # CRUCIAL: Check that the correct English description was extracted
    assert "horrific gene splicing" in result.description
    assert result.habitat == "rare"
    assert result.is_legendary is True

@pytest.mark.asyncio
async def test_pokemon_not_found_raises_404(httpx_mock):
    """Test that a 404 from PokeAPI is correctly re-mapped to a FastAPI 404."""
    # ARRANGE: Mock the external API to return a 404 Not Found
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/nonexistent",
        status_code=404
    )
    client = PokeAPIClient()
    
    # ACT & ASSERT: Expect a standard FastAPI HTTPException with status 404
    with pytest.raises(HTTPException) as excinfo:
        await client.get_pokemon_species("nonexistent")
    
    assert excinfo.value.status_code == 404

@pytest.mark.asyncio
async def test_pokeapi_internal_error_raises_503(httpx_mock):
    """Test that a 500 from PokeAPI is correctly re-mapped to our custom 503 error."""
    # ARRANGE: Mock the external API to return a 500 Internal Server Error
    httpx_mock.add_response(
        url="https://pokeapi.co/api/v2/pokemon-species/internalerror",
        status_code=500
    )
    client = PokeAPIClient()

    # ACT & ASSERT: Expect our custom APIClientError (HTTP 503)
    with pytest.raises(APIClientError) as excinfo:
        await client.get_pokemon_species("internalerror")
    
    assert excinfo.value.status_code == 503