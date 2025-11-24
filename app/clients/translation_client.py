from fastapi import HTTPException
import httpx
import logging 

logger = logging.getLogger(__name__)

# Define the custom exception 
class APIClientError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        # We use a 503 Service Unavailable for external API failures
        super().__init__(status_code=503, detail=f"External API Error: {detail}")

class TranslationClient:
    BASE_URL = "https://api.funtranslations.com/translate" 

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=5.0)

    async def translate(self, text: str, translation_style: str) -> str:
        """
        Translates text using the specified funtranslations style (yoda or shakespeare).
        """
        url = f"/{translation_style}"
        
        try:
            response = await self.client.post(
                url=url, 
                json={"text": text}
            )
            response.raise_for_status() 
            
            # The result is nested deep in the JSON response
            data = response.json()
            translated_text = data["contents"]["translated"]
            
            return translated_text
        
        except httpx.HTTPStatusError as e:
            # Handle 4xx/5xx errors
            detail = f"Translation API failed with status {e.response.status_code}. "
            if e.response.status_code == 429:
                detail += "Rate limit exceeded."
            
            # Map all failures to our standard 503 APIClientError
            logger.error(f"Translation API error: {detail}")
            raise APIClientError(status_code=503, detail=detail)
        
        except httpx.RequestError as e:
             # Handle network failures/timeouts
            logger.error(f"Translation API network error: {str(e)}")
            raise APIClientError(status_code=503, detail=f"Translation API network error: {str(e)}")
        
        except Exception as e:
             # Handle malformed JSON response or missing keys
            logger.error(f"Translation API response parsing error: {str(e)}")
            raise APIClientError(status_code=503, detail="Translation API returned an unexpected response format.")