import pytest
from unittest.mock import AsyncMock
from app.services.pokemon_service import PokemonService
from app.models import PokemonResponse, PokemonSpeciesData, TranslatedPokemonResponse
from app.clients.translation_client import APIClientError

# Sample data returned by the MOCKED client
MOCK_SPECIES_DATA = PokemonSpeciesData(
    name="mewtwo",
    description="It was created by a scientist.",
    habitat="rare",
    is_legendary=True,
)

@pytest.fixture
def mock_clients():
    # Use AsyncMock for methods that are awaited
    poke_client = AsyncMock() 
    translation_client = AsyncMock()
    
    # Set default return values for clarity in tests
    poke_client.get_pokemon_species.return_value = MOCK_SPECIES_DATA
    translation_client.translate.return_value = "Translated description."
    
    return poke_client, translation_client

@pytest.fixture
def pokemon_service(mock_clients):
    poke_client, translation_client = mock_clients
    # The service needs both clients for the translated endpoint
    return PokemonService(poke_client=poke_client, translation_client=translation_client)


@pytest.mark.asyncio
async def test_get_basic_info_success(pokemon_service, mock_clients):
    """
    Verifies that the service correctly calls the client and maps the result 
    to the public PokemonResponse model.
    """
    # ARRANGE - unpack the clients from the fixture
    poke_client, translation_client = mock_clients
    
    # ACT
    result = await pokemon_service.get_basic_info("mewtwo")
    
    # ASSERT
    # 1. Check the client was called correctly
    poke_client.get_pokemon_species.assert_called_once_with("mewtwo")
    
    # 2. Check the output type is the public contract
    assert isinstance(result, PokemonResponse)
    
    # 3. Check the data mapping is correct
    assert result.name == "mewtwo"
    assert result.description == MOCK_SPECIES_DATA.description
    assert result.is_legendary is True

# --- TRANSLATION RULE TESTS ---

@pytest.mark.asyncio
async def test_yoda_translation_for_legendary_pokemon(pokemon_service, mock_clients):
    """
    Rule 1: If is_legendary is True, use Yoda translation.
    """
    # ARRANGE
    poke_client, translation_client = mock_clients
    
    # Configure the mock to return Legendary data
    poke_client.get_pokemon_species.return_value = MOCK_SPECIES_DATA 
    translation_client.translate.return_value = "Yoda translation, this is."
    
    # ACT
    result = await pokemon_service.get_translated_info("mewtwo")
    
    # ASSERT
    assert isinstance(result, TranslatedPokemonResponse)
    # Check that the correct translation style was requested
    translation_client.translate.assert_called_with(
        MOCK_SPECIES_DATA.description, 
        "yoda"
    )
    assert "Yoda translation" in result.description


@pytest.mark.asyncio
async def test_yoda_translation_for_cave_habitat(pokemon_service, mock_clients):
    """
    Rule 1: If habitat is 'cave', use Yoda translation (even if not legendary).
    """
    # ARRANGE
    poke_client, translation_client = mock_clients
    
    # Configure the mock to return Cave habitat, but NOT legendary
    MOCK_SPECIES_DATA_CAVE = MOCK_SPECIES_DATA.model_copy(update={'is_legendary': False, 'habitat': 'cave'})
    poke_client.get_pokemon_species.return_value = MOCK_SPECIES_DATA_CAVE
    translation_client.translate.return_value = "In cave lives, this one."
    
    # ACT
    result = await pokemon_service.get_translated_info("zubat")
    
    # ASSERT
    translation_client.translate.assert_called_with(
        MOCK_SPECIES_DATA.description, # Description content doesn't change
        "yoda"
    )
    assert "In cave lives" in result.description


@pytest.mark.asyncio
async def test_shakespeare_translation_for_normal_pokemon(pokemon_service, mock_clients):
    """
    Rule 2: Otherwise (not legendary AND not cave), use Shakespeare translation.
    """
    # ARRANGE
    poke_client, translation_client = mock_clients
    
    # Configure the mock to return Normal data (e.g., grassland)
    MOCK_SPECIES_DATA_NORMAL = MOCK_SPECIES_DATA.model_copy(update={'is_legendary': False, 'habitat': 'grassland'})
    poke_client.get_pokemon_species.return_value = MOCK_SPECIES_DATA_NORMAL
    translation_client.translate.return_value = "Hark! T'was a gentle creature."
    
    # ACT
    result = await pokemon_service.get_translated_info("pikachu")
    
    # ASSERT
    translation_client.translate.assert_called_with(
        MOCK_SPECIES_DATA.description, 
        "shakespeare"
    )
    assert "Hark! T'was" in result.description

# --- ERROR HANDLING TEST ---

@pytest.mark.asyncio
async def test_translation_api_failure_is_propagated(pokemon_service, mock_clients):
    """
    Test that if the Translation API fails (e.g., rate limit), the error is passed up.
    """
    # ARRANGE
    poke_client, translation_client = mock_clients
    
    # Simulate an error from the translation client (our custom APIClientError 503)
    translation_client.translate.side_effect = APIClientError(
        status_code=503, 
        detail="Translation API rate limited."
    )
    
    # ACT & ASSERT
    with pytest.raises(APIClientError) as excinfo:
        await pokemon_service.get_translated_info("mewtwo")
    
    assert excinfo.type is APIClientError
    assert "rate limited" in excinfo.value.detail