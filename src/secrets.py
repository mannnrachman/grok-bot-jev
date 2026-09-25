from __future__ import annotations

import os


def ensure_api_key(provider: str) -> str:
    """Read only the credential of the selected provider."""
    from src.jev_client import ProviderError

    env_name = {"typesafe": "TYPESAFE_API_KEY", "openjev": "OPENJEV_API_KEY"}.get(provider)
    if env_name is None:
        raise ProviderError("invalid_provider")
    key = os.environ.get(env_name)
    if not key:
        raise ProviderError("missing_api_key")
    return key
