from app.clients.pokeapi_client import PokeAPIClient
from app.clients.translation_client import TranslationClient
from app.models import PokemonResponse, TranslatedPokemonResponse

class PokemonService:
    # Service now requires both clients via Dependency Injection
    def __init__(self, poke_client: PokeAPIClient, translation_client: TranslationClient):
        self._poke_client = poke_client
        self._translation_client = translation_client

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

    async def get_translated_info(self, name: str) -> TranslatedPokemonResponse:
        """
        Endpoint 2: Fetches data and applies the translation rule.
        Rule: Legendary OR Habitat is 'cave' -> Yoda. Otherwise -> Shakespeare.
        """
        species_data = await self._poke_client.get_pokemon_species(name)
        
        # --- CORE BUSINESS LOGIC: Determine Translation Style ---
        
        is_cave_habitat = species_data.habitat == "cave"
        
        if species_data.is_legendary or is_cave_habitat:
            translation_style = "yoda"
        else:
            translation_style = "shakespeare"
            
        # 2. Get the translation (exception handling is in the client)
        # Note: We await the translation call which will trigger the robust cache mechanism.
        translated_description = await self._translation_client.translate(
            species_data.description, 
            translation_style
        )
        
        # 3. Map to the final response model
        return TranslatedPokemonResponse(
            name=species_data.name,
            description=translated_description, # Use the translated text here
            habitat=species_data.habitat,
            is_legendary=species_data.is_legendary
        )