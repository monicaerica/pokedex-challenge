from fastapi import FastAPI, Depends, status, HTTPException
from app.services.pokemon_service import PokemonService
from app.dependencies import get_pokemon_service
from app.models import PokemonResponse, TranslatedPokemonResponse
from app.clients.translation_client import APIClientError 

app = FastAPI(
    title="TrueLayer Pokedex API",
    description="Microservice demonstrating clean architecture and robust error handling.",
)

# Endpoint 1: Basic Pokemon Info
@app.get(
    "/pokemon/{name}",
    response_model=PokemonResponse,
    summary="Returns basic Pokemon information",
)
async def get_pokemon_info(
    name: str,
    service: PokemonService = Depends(get_pokemon_service),
):
    """Fetches basic information (name, description, habitat, legendary status) for a given Pokemon name."""
    # Errors (404, 503) are already handled within the PokeAPIClient and propagated as FastAPI HTTPExceptions
    return await service.get_basic_info(name)


# Endpoint 2: Translated Pokemon Info
@app.get(
    "/pokemon/{name}/translated",
    response_model=TranslatedPokemonResponse,
    summary="Returns Pokemon information with fun translation based on legendary/habitat status",
)
async def get_translated_pokemon_info(
    name: str,
    service: PokemonService = Depends(get_pokemon_service),
):
    """Applies the translation rule (Yoda for legendary/cave, Shakespeare otherwise)."""
    # This try/except block handles APIClientErrors raised by the TranslationClient
    try:
        return await service.get_translated_info(name)
    except APIClientError as e:
        # If the external Translation API fails (e.g., rate limit, 500 error), 
        # we map it to a 503 Service Unavailable for the API consumer.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.detail
        )