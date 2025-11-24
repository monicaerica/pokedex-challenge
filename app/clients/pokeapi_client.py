import httpx
from typing import Dict
from app.models import PokemonSpeciesData
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Define a custom exception for client errors (Used for 5xx errors)
class APIClientError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=f"External API Error: {detail}")

class PokeAPIClient:
    BASE_URL = "https://pokeapi.co/api/v2"

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=5.0)
        # Simple in-memory cache: {pokemon_name: raw_species_data}
        # 1 - Simple - Just a dictionary, no complex async cache libraries needed
        # 2 - Works with async - No coroutine reuse issues
        # 3 - Only caches successes - Exceptions prevent caching, so rate limits trigger retries
        self._cache: Dict[str, dict] = {}

    async def _fetch_species_data(self, pokemon_name: str) -> dict:
        """Internal method to fetch raw species data with caching and error handling."""
        # Normalize the name to lowercase for consistent caching
        normalized_name = pokemon_name.lower()
        
        # Check cache first
        if normalized_name in self._cache:
            logger.info(f"Cache hit for Pokemon: {normalized_name}")
            return self._cache[normalized_name]
        
        # Cache miss - make network call
        logger.info(f"Cache miss for Pokemon: {normalized_name}")
        url = f"/pokemon-species/{normalized_name}"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()  # Raises for 4xx/5xx status codes
            data = response.json()
            
            # Store in cache (only successful results get cached)
            self._cache[normalized_name] = data
            return data
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Map external 404 to a standardized internal 404
                raise HTTPException(status_code=404, detail=f"Pokemon '{pokemon_name}' not found.")
            # Map all other client errors (e.g., 500) to our custom APIClientError (503 Service Unavailable)
            raise APIClientError(status_code=503, detail=f"PokeAPI failed with status {e.response.status_code}")
        except httpx.RequestError as e:
             # Handle network failures/timeouts
            raise APIClientError(status_code=503, detail=f"PokeAPI network error: {str(e)}")

    async def get_pokemon_species(self, name: str) -> PokemonSpeciesData:
        """Fetches, processes, and validates the core Pokemon species data."""
        data = await self._fetch_species_data(name)
        
        # Data Extraction Logic (Filter for the first English description)
        english_description = next(
            (
                entry['flavor_text'].replace('\n', ' ').replace('\f', ' ')  # Clean up newlines/form feeds
                for entry in data.get('flavor_text_entries', [])
                if entry['language']['name'] == 'en'
            ),
            # Use a default if no English description is found
            "Description unavailable.",
        )
        
        return PokemonSpeciesData(
            name=data['name'],
            description=english_description, 
            habitat=data.get('habitat', {}).get('name'),
            is_legendary=data['is_legendary']
        )
    
    def clear_cache(self):
        """Clear the Pokemon species cache. Useful for testing."""
        self._cache.clear()