from fastapi import HTTPException
import httpx
import logging 
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class APIClientError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=503, detail=f"External API Error: {detail}")

class TranslationClient:
    BASE_URL = "https://api.funtranslations.com/translate" 

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=5.0)
        # Simple in-memory cache: {(text, style): translated_text}
        # 1 - Simple - Just a dictionary, no complex async cache libraries needed
        # 2 - Works with async - No coroutine reuse issues
        # 3 - Only caches successes - Exceptions prevent caching, so rate limits trigger retries
        self._cache: Dict[Tuple[str, str], str] = {}

    async def translate(self, text: str, translation_style: str) -> str:
        """Translates text with caching."""
        cache_key = (text, translation_style)
        
        # Check cache first
        if cache_key in self._cache:
            logger.info(f"Cache hit for: {text[:30]}...")
            return self._cache[cache_key]
        
        # Cache miss - make network call
        logger.info(f"Cache miss for: {text[:30]}...")
        result = await self._translate_network_call(text, translation_style)
        
        # Store in cache (only successful results get cached)
        self._cache[cache_key] = result
        return result

    async def _translate_network_call(self, text: str, translation_style: str) -> str:
        """Performs the actual network call and error handling."""
        url = f"/{translation_style}"
        
        try:
            response = await self.client.post(url=url, json={"text": text})
            response.raise_for_status() 
            
            data = response.json()
            translated_text = data["contents"]["translated"]
            return translated_text
        
        except httpx.HTTPStatusError as e:
            detail = f"Translation API failed with status {e.response.status_code}. "
            if e.response.status_code == 429:
                detail += "Rate limit exceeded."
            logger.error(f"Translation API error: {detail}")
            raise APIClientError(status_code=503, detail=detail)
        
        except httpx.RequestError as e:
            logger.error(f"Translation API network error: {str(e)}")
            raise APIClientError(status_code=503, detail=f"Translation API network error: {str(e)}")
        
        except Exception:
            logger.error("Translation API response parsing error.")
            raise APIClientError(status_code=503, detail="Translation API returned an unexpected response format.")
    
    def clear_cache(self):
        """Clear the translation cache. Useful for testing."""
        self._cache.clear()