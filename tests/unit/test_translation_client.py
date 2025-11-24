import pytest
import httpx
from app.clients.translation_client import TranslationClient, APIClientError
from app.clients.translation_client import TranslationClient


MOCK_TRANSLATION_SUCCESS = {
    "success": {"total": 1},
    "contents": {
        "translated": "Yoda speaks, you listen.",
        "text": "You listen to Yoda speak.",
        "translation": "yoda"
    }
}


@pytest.mark.asyncio
async def test_successful_yoda_translation(httpx_mock):
    """Verifies successful API call and correct extraction of the translated text."""
    # ARRANGE: Mock the external API call
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/yoda",
        json=MOCK_TRANSLATION_SUCCESS,
        status_code=200
    )
    client = TranslationClient()

    # ACT
    result = await client.translate("You listen to Yoda speak.", "yoda")

    # ASSERT: Check that only the translated text is returned
    assert result == "Yoda speaks, you listen."


@pytest.mark.asyncio
async def test_api_rate_limit_raises_503(httpx_mock):
    """Tests that a 429 (Rate Limit) from the external API is mapped to our custom 503 error."""
    # ARRANGE: Mock the external API to return a 429 Too Many Requests
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/shakespeare",
        status_code=429,
        json={"error": {"code": 429, "message": "Too Many Requests"}}
    )
    client = TranslationClient()
    
    # ACT & ASSERT: Expect our custom APIClientError (HTTP 503)
    with pytest.raises(APIClientError) as excinfo:
        await client.translate("To be or not to be.", "shakespeare")
    
    # Verify the exception type and status code mapping
    assert excinfo.value.status_code == 503
    assert "rate limit" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_api_network_error_raises_503(httpx_mock):
    """Tests that a network failure (timeout, DNS error) raises our custom 503 error."""
    # ARRANGE: Mock a network failure (RequestError)
    httpx_mock.add_exception(
        httpx.ConnectError("Connection timed out."),
        url="https://api.funtranslations.com/translate/yoda"
    )
    client = TranslationClient()
    
    # ACT & ASSERT: Expect our custom APIClientError (HTTP 503)
    with pytest.raises(APIClientError) as excinfo:
        await client.translate("Test.", "yoda")
    
    assert excinfo.value.status_code == 503
    assert "network error" in excinfo.value.detail.lower()