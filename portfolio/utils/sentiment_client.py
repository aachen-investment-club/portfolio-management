import os
from typing import Any, Dict, Optional

import requests

SENTIMENT_API_URL = os.getenv("SENTIMENT_API_URL", "").rstrip("/")

_TIMEOUT = 10


def get_sentiment_by_asset(
    asset: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call GET /by-asset on the sentiment service.

    Returns the full response dict:
      { asset, article_count, average_sentiment, label, articles[] }

    Raises requests.HTTPError on non-2xx responses.
    """
    params: Dict[str, str] = {"asset": asset}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    resp = requests.get(
        f"{SENTIMENT_API_URL}/by-asset",
        params=params,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_article_sentiment(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Call GET /article/{document_id} on the sentiment service.

    Returns the sentiment dict or None when the service returns 404
    (article exists but has no cached sentiment yet).

    Raises requests.HTTPError on other non-2xx responses.
    """
    resp = requests.get(
        f"{SENTIMENT_API_URL}/article/{document_id}",
        timeout=_TIMEOUT,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()
