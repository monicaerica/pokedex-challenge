import pytest
import httpx
from app.clients.translation_client import TranslationClient, APIClientError
from fakeredis.aioredis import FakeRedis


MOCK_TRANSLATION_SUCCESS = {
    "success": {"total": 1},
    "contents": {
        "translated": "Yoda speaks, you listen.",
        "text": "You listen to Yoda speak.",
        "translation": "yoda"
    }
}

@pytest.fixture
def redis_client():
    """Provides a fake Redis client for testing."""
    return FakeRedis(decode_responses=True)

@pytest.fixture
def translation_client(redis_client):
    """Provides a TranslationClient with fake Redis."""
    client = TranslationClient()
    client.redis = redis_client  # Inject fake Redis
    return client

@pytest.mark.asyncio
async def test_successful_yoda_translation(httpx_mock, translation_client):
    """Verifies successful API call and correct extraction of the translated text."""
    # ARRANGE: Mock the external API call
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/yoda",
        json=MOCK_TRANSLATION_SUCCESS,
        status_code=200
    )

    # ACT
    result = await translation_client.translate("You listen to Yoda speak.", "yoda")

    # ASSERT: Check that only the translated text is returned
    assert result == "Yoda speaks, you listen."


@pytest.mark.asyncio
async def test_api_rate_limit_raises_503(httpx_mock, translation_client):
    """Tests that a 429 (Rate Limit) from the external API is mapped to our custom 503 error."""
    # ARRANGE: Mock the external API to return a 429 Too Many Requests
    httpx_mock.add_response(
        url="https://api.funtranslations.com/translate/shakespeare",
        status_code=429,
        json={"error": {"code": 429, "message": "Too Many Requests"}}
    )
    
    # ACT & ASSERT: Expect our custom APIClientError (HTTP 503)
    with pytest.raises(APIClientError) as excinfo:
        await translation_client.translate("To be or not to be.", "shakespeare")
    
    # Verify the exception type and status code mapping
    assert excinfo.value.status_code == 503
    assert "rate limit" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_api_network_error_raises_503(httpx_mock, translation_client):
    """Tests that a network failure (timeout, DNS error) raises our custom 503 error."""
    # ARRANGE: Mock a network failure (RequestError)
    httpx_mock.add_exception(
        httpx.ConnectError("Connection timed out."),
        url="https://api.funtranslations.com/translate/yoda"
    )
    
    # ACT & ASSERT: Expect our custom APIClientError (HTTP 503)
    with pytest.raises(APIClientError) as excinfo:
        await translation_client.translate("Test.", "yoda")
    
    assert excinfo.value.status_code == 503
    assert "network error" in excinfo.value.detail.lower()

@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
@pytest.mark.asyncio
async def test_translation_caching_prevents_redundant_calls(httpx_mock, translation_client):
    """
    Verifies that calling translate() with the same arguments twice results in only 
    ONE network call, proving the cache is active.
    """
    call_count = [0]
    
    def count_and_respond(request):
        call_count[0] += 1
        return httpx.Response(
            status_code=200,
            json=MOCK_TRANSLATION_SUCCESS
        )

    # ARRANGE: Allow the callback to match multiple requests
    httpx_mock.add_callback(
        callback=count_and_respond,
        url="https://api.funtranslations.com/translate/yoda",
    )
    text_to_translate = "The cache is important for rate limits."

    # ACT 1: First call (cache miss - should trigger network call)
    result1 = await translation_client.translate(text_to_translate, "yoda")
    
    # ASSERT 1
    assert call_count[0] == 1  # Network called once
    assert result1 == "Yoda speaks, you listen."

    # ACT 2: Second call with SAME arguments (cache hit - NO network call)
    result2 = await translation_client.translate(text_to_translate, "yoda")
    
    # ASSERT 2
    assert result2 == result1  # Results must be identical
    assert call_count[0] == 1  # Network call count should NOT have increased

    # ACT 3: Third call with DIFFERENT arguments (cache miss - should trigger network call)
    text_2 = "A different request."
    result3 = await translation_client.translate(text_2, "yoda")

    # ASSERT 3
    assert call_count[0] == 2  # Network call count should increase to 2
    assert result3 == "Yoda speaks, you listen."