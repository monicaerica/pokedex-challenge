from fastapi import HTTPException
import httpx
import logging 
import json
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

class APIClientError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=503, detail=f"External API Error: {detail}")

class TranslationClient:
    BASE_URL = "https://api.funtranslations.com/translate"
    CACHE_TTL = 604800  # 7 days (translations are deterministic)

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=5.0)
        # Redis client instead of dictionary
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    async def translate(self, text: str, translation_style: str) -> str:
        """Translates text with caching."""
        cache_key = f"translation:{translation_style}:{hash(text)}"
        
        # Check cache first (Redis instead of dict)
        cached_translation = await self.redis.get(cache_key)
        if cached_translation:
            logger.info(f"Cache hit for: {text[:30]}...")
            return cached_translation
        
        # Cache miss - make network call
        logger.info(f"Cache miss for: {text[:30]}...")
        result = await self._translate_network_call(text, translation_style)
        
        # Store in cache (only successful results get cached)
        await self.redis.setex(cache_key, self.CACHE_TTL, result)
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
    
    async def clear_cache(self):
        """Clear the translation cache. Useful for testing."""
        keys = await self.redis.keys("translation:*")
        if keys:
            await self.redis.delete(*keys)
    
    async def close(self):
        """Close Redis connection (call on app shutdown)."""
        await self.redis.close()