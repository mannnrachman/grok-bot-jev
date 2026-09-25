from __future__ import annotations

import os


def ensure_api_key(provider: str) -> str:
    """Read only the credential of the selected provider."""
    from src.jev_client import ProviderError

    if provider != "openjev":
        raise ProviderError("invalid_provider")
    key = os.environ.get("OPENJEV_API_KEY")
    if not key:
        raise ProviderError("missing_api_key")
    return key
