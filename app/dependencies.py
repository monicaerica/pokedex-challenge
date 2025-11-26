from app.clients.pokeapi_client import PokeAPIClient
from app.clients.translation_client import TranslationClient 
from app.services.pokemon_service import PokemonService

def get_poke_client() -> PokeAPIClient:
    return PokeAPIClient()

def get_translation_client() -> TranslationClient: 
    return TranslationClient()

def get_pokemon_service(
    poke_client: PokeAPIClient = get_poke_client,
    translation_client: TranslationClient = get_translation_client, 
) -> PokemonService:
    return PokemonService(poke_client=poke_client, translation_client=translation_client)