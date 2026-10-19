"""Shared Spritmonitor API request helpers."""

import aiohttp

from .const import API_BASE_URL


class SpritmonitorAPIError(Exception):
    """An API request failed or Spritmonitor rejected its parameters."""


def api_headers(app_token: str, bearer_token: str) -> dict[str, str]:
    """Return authorization headers, accepting previously prefixed tokens."""
    token = bearer_token.strip()
    if not token.lower().startswith("bearer "):
        token = f"Bearer {token}"
    return {
        "Accept": "application/json",
        "Application-ID": app_token,
        "Authorization": token,
    }


async def api_get(session: aiohttp.ClientSession, path: str, headers: dict, *, params=None, timeout=30):
    """Call the API and check both HTTP errors and JSON-level rejections."""
    url = path if path.startswith("https://") else f"{API_BASE_URL}/{path.lstrip('/')}"
    async with session.get(
        url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=timeout)
    ) as response:
        response.raise_for_status()
        try:
            result = await response.json()
        except (ValueError, aiohttp.ContentTypeError) as err:
            raise SpritmonitorAPIError("Spritmonitor returned invalid JSON") from err
    if isinstance(result, dict) and result.get("errors"):
        raise SpritmonitorAPIError(
            f"Spritmonitor rejected request: {result.get('errormessages', result['errors'])}"
        )
    return result
