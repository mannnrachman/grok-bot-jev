from __future__ import annotations

from typing import Any

from src.config import load_config, resolve_log_path
from src.jev_client import ProviderError, system_one
from src.logger import log_run


BYPASS_MARKERS = ("bypass jev", "bypass jev:", "no jev")


def _bypassed(state: dict[str, Any]) -> bool:
    raw = " ".join(
        str(state.get(k, ""))
        for k in ("goal", "raw", "user_message", "notes")
    ).lower()
    return any(m in raw for m in BYPASS_MARKERS)


def route_task(state: dict[str, Any]) -> dict[str, Any]:
    """Run Jev gates and return a routing decision for Grok Bot."""
    cfg = load_config()
    log_path = resolve_log_path(cfg)

    if not cfg.get("enabled", True) or _bypassed(state):
        out = {
            "action": "proceed_full",
            "reason": "lab disabled or bypass jev",
            "mode": cfg.get("mode"),
            "jev_used": False,
            "details": {},
        }
        log_run(log_path, {"event": "route", **out})
        return out

    # Keep the kill-switch path dependency-free so it works during incidents.
    thr = cfg.get("thresholds") or {}
    limits = cfg.get("limits") or {}
    provider = cfg.get("provider", "openjev")
    model = cfg.get("model") or "openjev"

    # Normalize state for Jev
    jstate = {
        "goal": state.get("goal") or state.get("raw") or "",
        "kind_hint": state.get("kind") or state.get("kind_hint") or "unknown",
        "has_cached_artifact": bool(state.get("cached_artifact")),
        "cached_note": state.get("cached_note") or "",
        "prior_error": state.get("prior_error") or "",
        "same_error_count": int(state.get("same_error_count") or 0),
        "sources_found": int(state.get("sources_found") or 0),
        "constraints": state.get("constraints") or "",
    }

    questions = {
        "intent": dict(
            type="choice",
            instructions="What kind of work does this request mainly need?",
            criteria={
                "chat": "Short answer or conversation; no tools needed",
                "lookup": "Known file/API/status check; mostly deterministic",
                "research": "Need web/search and synthesis",
                "browser": "Need interactive browser clicks",
                "coding": "Edit code / tests / repo work",
                "write": "Draft long prose/email/doc",
                "account": "Send, publish, pay, delete, change permissions",
            },
        ),
        "reuse_cache": dict(
            type="noul",
            instructions="Is there already a fresh enough cached result that should be reused instead of doing new heavy work?"
        ),
        "needs_subagent": dict(
            type="noul",
            instructions="Does this clearly need an extra specialized bot (research/browser/coding) beyond one Grok Bot turn?"
        ),
        "stop_retry": dict(
            type="noul",
            instructions="Given prior_error and same_error_count, should we STOP retrying the same approach?"
        ),
        "complexity": dict(
            type="score",
            instructions="How much Grok Bot effort is justified?",
            criteria=[
                "Trivial — one step or cached",
                "Normal — short tool use",
                "Heavy — multi-step research/browser/coding",
            ],
        ),
    }

    try:
        if provider != "openjev":
            raise ProviderError("invalid_provider")
        if model != "openjev":
            raise ProviderError("invalid_model")
        result = system_one(jstate, questions, provider=provider, model=model)
    except ProviderError as exc:
        out = {
            "action": "proceed_full",
            "reason": "jev unavailable; normal Grok Bot path",
            "mode": cfg.get("mode"),
            "jev_used": False,
            "details": {"provider": str(provider), "error": exc.category},
        }
        log_run(log_path, {"event": "route_error", "action": out["action"], "provider": str(provider), "error": exc.category})
        return out

    reuse_n = result["reuse_cache"]
    sub_n = result["needs_subagent"]
    stop_n = result["stop_retry"]
    # Score 0..2 → normalize
    comp = result["complexity"] / 2.0

    action = "proceed_full"
    reason = "default full Grok Bot work"

    if jstate["has_cached_artifact"] and reuse_n >= float(thr.get("reuse_min", 0.65)):
        action = "reuse_cache"
        reason = f"reuse_cache noul={reuse_n:.2f}"
    elif jstate["same_error_count"] >= int(limits.get("max_retries_same_error", 1)) and stop_n >= 0.55:
        action = "stop_retry"
        reason = f"stop_retry noul={stop_n:.2f} same_error_count={jstate['same_error_count']}"
    elif result["intent"] == "lookup" and result["intent_confidence"] >= float(thr.get("min_choice_confidence", 0.55)):
        action = "run_deterministic"
        reason = "intent=lookup"
    elif result["intent"] == "chat" and result["intent_confidence"] >= float(thr.get("min_choice_confidence", 0.55)):
        action = "chat_only"
        reason = "intent=chat"
    elif result["intent"] == "account":
        action = "ask_human"
        reason = "account/irreversible class — require approval"
    elif sub_n >= float(thr.get("subagent_min", 0.75)):
        action = "allow_subagent"
        reason = f"needs_subagent noul={sub_n:.2f}"
    elif result["intent"] in {"research", "browser"}:
        action = "research_capped"
        reason = f"cap sources at {limits.get('max_browser_sources', 5)}"

    details = {
        "intent": result["intent"],
        "intent_confidence": round(result["intent_confidence"], 4),
        "intent_probs": {k: round(float(v), 4) for k, v in result["intent_probs"].items()},
        "reuse_cache": round(reuse_n, 4),
        "needs_subagent": round(sub_n, 4),
        "stop_retry": round(stop_n, 4),
        "complexity_0_1": round(comp, 4),
        "max_browser_sources": int(limits.get("max_browser_sources", 5)),
        "provider": provider,
    }

    out = {
        "action": action,
        "reason": reason,
        "mode": cfg.get("mode"),
        "jev_used": True,
        "details": details,
        "policy": {
            "honor_in_active_mode": True,
            "shadow_mode_is_advisory": cfg.get("mode") == "shadow",
        },
    }
    log_run(
        log_path,
        {
            "event": "route",
            "provider": provider,
            "action": action,
            "reason": reason,
            "mode": cfg.get("mode"),
            "details": details,
        },
    )
    return out
