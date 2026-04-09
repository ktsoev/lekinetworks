import logging
import os
import httpx

logger = logging.getLogger(__name__)

def _api_headers():
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("SERVER_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers

async def post(url: str, data: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                json=data,
                headers=_api_headers(),
                timeout=30.0
            )

            print(f"POST {url} -> {response.status_code}")
            
            try:
                return response.json()
            except Exception:
                return response.text

        except Exception as e:
            logger.exception("Ошибка запроса %s: %s", url, e)
            return None