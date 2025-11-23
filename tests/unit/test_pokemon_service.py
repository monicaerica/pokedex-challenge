import pytest
from unittest.mock import AsyncMock
from app.services.pokemon_service import PokemonService
from app.models import PokemonResponse, PokemonSpeciesData

# Sample data returned by the MOCKED client
MOCK_SPECIES_DATA = PokemonSpeciesData(
    name="mewtwo",
    description="It was created by a scientist.",
    habitat="rare",
    is_legendary=True,
)

@pytest.fixture
def mock_poke_client():
    poke_client = AsyncMock()
    poke_client.get_pokemon_species.return_value = MOCK_SPECIES_DATA
    return poke_client

@pytest.fixture
def pokemon_service_basic(mock_poke_client):
    return PokemonService(poke_client=mock_poke_client)


@pytest.mark.asyncio
async def test_get_basic_info_success(pokemon_service_basic, mock_poke_client):
    """
    Verifies that the service correctly calls the client and maps the result 
    to the public PokemonResponse model.
    """
    # ARRANGE is handled by the fixtures (mocking the client)
    
    # ACT
    result = await pokemon_service_basic.get_basic_info("mewtwo")
    
    # ASSERT
    # 1. Check the client was called correctly
    mock_poke_client.get_pokemon_species.assert_called_once_with("mewtwo")
    
    # 2. Check the output type is the public contract
    assert isinstance(result, PokemonResponse)
    
    # 3. Check the data mapping is correct
    assert result.name == "mewtwo"
    assert result.description == MOCK_SPECIES_DATA.description
    assert result.is_legendary is True