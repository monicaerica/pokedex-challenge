from app.clients import PokeAPIClient
from app.clients import TranslationClient 
from app.services import PokemonService
from fastapi import Depends

_poke_client = None
_translation_client = None

def get_poke_client() -> PokeAPIClient:
    global _poke_client
    if _poke_client is None:
        _poke_client = PokeAPIClient()
    return _poke_client

def get_translation_client() -> TranslationClient:
    global _translation_client
    if _translation_client is None:
        _translation_client = TranslationClient()
    return _translation_client

def get_pokemon_service(
    poke_client: PokeAPIClient = Depends(get_poke_client),
    translation_client: TranslationClient = Depends(get_translation_client), 
) -> PokemonService:
    return PokemonService(poke_client=poke_client, translation_client=translation_client)