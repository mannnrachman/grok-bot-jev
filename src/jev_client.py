from __future__ import annotations

import json
import math
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.secrets import ensure_api_key

OPENJEV_URL = "https://api.openjev.sh/v1/systemone"


class ProviderError(Exception):
    """A provider call or response failed without exposing request contents."""

    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


def _number(value: Any, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError("invalid_response")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ProviderError("invalid_response")
    return value


def _normalize(answers: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(answers, dict):
        raise ProviderError("invalid_response")
    try:
        intent = answers["intent"]
        complexity = answers["complexity"]
        options = questions["intent"]["criteria"]
        if intent["type"] != "choice" or complexity["type"] != "score":
            raise ProviderError("invalid_response")
        choice = intent["choice"]
        probs = intent["probabilities"]
        if not isinstance(choice, str) or choice not in options or not isinstance(probs, dict) or set(probs) != set(options):
            raise ProviderError("invalid_response")
        probabilities = {key: _number(value, 0, 1) for key, value in probs.items()}
        if abs(sum(probabilities.values()) - 1) > 0.02:
            raise ProviderError("invalid_response")
        result = {
            "intent": choice,
            "intent_confidence": _number(intent["confidence"], 0, 1),
            "intent_probs": probabilities,
            "complexity": _number(complexity["score"], 0, len(questions["complexity"]["criteria"]) - 1),
        }
        for name in ("reuse_cache", "needs_subagent", "stop_retry"):
            answer = answers[name]
            if answer["type"] != "noul":
                raise ProviderError("invalid_response")
            result[name] = _number(answer["noul"], 0, 1)
        return result
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ProviderError("invalid_response") from exc


def _retry_delay(error: HTTPError, attempt: int) -> float:
    header = error.headers.get("Retry-After") if error.headers else None
    try:
        delay = float(header) if header is not None else float(2 ** attempt)
        if not math.isfinite(delay) or delay < 0:
            raise ValueError
    except ValueError:
        delay = float(2 ** attempt)
    return min(delay, 5.0)


def _openjev(state: dict[str, Any], questions: dict[str, Any], model: str) -> dict[str, Any]:
    key = ensure_api_key("openjev")
    payload = json.dumps({"model": model, "state": state, "questions": questions}).encode("utf-8")
    request = Request(
        OPENJEV_URL,
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(2):
        try:
            with urlopen(request, timeout=10) as response:
                if response.status != 200:
                    raise ProviderError("http_error")
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ProviderError("invalid_response")
                data = json.loads(raw)
            if not isinstance(data, dict):
                raise ProviderError("invalid_response")
            return _normalize(data.get("answers"), questions)
        except HTTPError as exc:
            if exc.code in (429, 503) and attempt == 0:
                time.sleep(_retry_delay(exc, attempt))
                continue
            raise ProviderError(f"http_{exc.code}") from exc
        except ProviderError:
            raise
        except (URLError, TimeoutError, OSError) as exc:
            if attempt == 0:
                time.sleep(1)
                continue
            raise ProviderError("network_error") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("invalid_response") from exc
    raise ProviderError("network_error")


def _typesafe(state: dict[str, Any], questions: dict[str, Any], model: str) -> dict[str, Any]:
    ensure_api_key("typesafe")
    try:
        from typesafe_sdk import Choice, Noul, Score, TypeSafeClient
    except ImportError as exc:
        raise ProviderError("sdk_missing") from exc
    constructors = {"choice": Choice, "noul": Noul, "score": Score}
    try:
        typed = {
            name: constructors[question["type"]](
                **{key: value for key, value in question.items() if key != "type"}
            )
            for name, question in questions.items()
        }
        with TypeSafeClient(model=model) as client:
            response = client.system_one(state=state, questions=typed)
        answers = {}
        for name, question in questions.items():
            kind = question["type"]
            obj = getattr(response, {"choice": "choices", "noul": "nouls", "score": "scores"}[kind])[name]
            fields = {
                "choice": ("choice", "confidence", "probabilities"),
                "noul": ("noul",),
                "score": ("score",),
            }[kind]
            answers[name] = {"type": kind, **{field: getattr(obj, field) for field in fields}}
        return _normalize(answers, questions)
    except ProviderError:
        raise
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise ProviderError("invalid_response") from exc
    except Exception as exc:
        # Avoid leaking SDK errors containing request contents to the log.
        raise ProviderError("sdk_error") from exc


def system_one(state: dict[str, Any], questions: dict[str, Any], provider: str, model: str) -> dict[str, Any]:
    models = {"typesafe": "jev-latest", "openjev": "openjev"}
    if provider not in models:
        raise ProviderError("invalid_provider")
    if model != models[provider]:
        raise ProviderError("invalid_model")
    if provider == "typesafe":
        return _typesafe(state, questions, model)
    return _openjev(state, questions, model)
