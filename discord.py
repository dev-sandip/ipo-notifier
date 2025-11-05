from typing import Any

import httpx

import logger


def send_discord_alert(payload: dict[str, Any], url: str):
    headers = {"Content-Type": "application/json"}
    print("Sending webhook to Discord...",url)
    try:
        response = httpx.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Failed to send webhook: {e.response.status_code}, {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"An error occurred while requesting {e.request.url!r}.")