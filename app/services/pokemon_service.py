from app.clients.pokeapi_client import PokeAPIClient
from app.models import PokemonResponse 

class PokemonService:
    # Use **kwargs to allow the service to be instantiated with only the poke_client for now, 
    # but be ready to accept the translation_client later.
    def __init__(self, poke_client: PokeAPIClient, **kwargs):
        self._poke_client = poke_client
        # We will add self._translation_client = kwargs.get('translation_client') later

    async def get_basic_info(self, name: str) -> PokemonResponse:
        """
        Endpoint 1: Fetches basic Pokemon data and maps to the response model.
        """
        # Call the client (which handles caching and fetching)
        species_data = await self._poke_client.get_pokemon_species(name)
        
        # Map the internal data model to the public API response model
        return PokemonResponse(
            name=species_data.name,
            description=species_data.description,
            habitat=species_data.habitat,
            is_legendary=species_data.is_legendary
        )

    # Placeholder for Endpoint 2 logic to be implemented later
    async def get_translated_info(self, name: str):
        # We raise this exception so the test for the translated endpoint fails initially
        raise NotImplementedError("Translated endpoint not yet implemented.")