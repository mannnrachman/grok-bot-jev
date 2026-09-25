# Jev Usage Router for Grok Bot

Use OpenJEV HTTP by default, or the optional TypeSafe SDK, as a decision layer before expensive work. This file is a recipe for creating a Grok Bot skill, not an automatically installed skill or hidden system hook. Follow the [setup guide](../README.md) first: the Python repo, config, and selected provider's key must exist on the computer that actually executes the router.

## Workflow

1. Check the kill switch first. If the configuration has `enabled: false`, or the user says `bypass jev` or `no jev`, skip Jev and proceed normally.
2. Before opening a browser, doing multi-source research, retrying a failed approach, loading several specialized skills, or launching a subagent, build a compact JSON state:

```json
{
  "goal": "what the user wants",
  "kind": "chat|lookup|research|browser|coding|write|account",
  "cached_artifact": false,
  "cached_note": "optional freshness and scope",
  "prior_error": "optional last error",
  "same_error_count": 0,
  "sources_found": 0,
  "constraints": "optional limits"
}
```

3. With permission to execute commands on the configured computer, run `.venv/bin/python -m src.cli '<json state>'` from the cloned repository directory. Pass only redacted task context, never a credential or a whole private conversation. The command prints JSON with `action`, `reason`, `mode`, and `details`. If the repo, execution access, or selected provider key is unavailable, report the integration failure and continue normally; do not pretend a live routing result exists.
4. In `shadow` mode, report the recommendation but continue according to normal Grok Bot judgment. In `active` mode, honor the actions below. Verify the user's actual intent and separate approval rules before any external action.

## Action policy in active mode

- `reuse_cache`: use the fresh artifact; do not repeat the expensive work.
- `stop_retry`: stop the repeated approach, explain the failure, and propose a different path or ask the user.
- `run_deterministic`: perform the known, bounded lookup without broad research.
- `chat_only`: answer directly without tools.
- `ask_human`: pause before any account, send, publish, pay, delete, or permission-changing action.
- `allow_subagent`: use a specialized subagent only when it is actually available and appropriate.
- `research_capped`: research with at most `details.max_browser_sources` sources/pages, then synthesize.
- `proceed_full`: continue with normal work while still applying ordinary safety and confirmation rules.

Never treat a Jev result as permission to reveal secrets or bypass a separate safety requirement. Do not include API keys in state, prompts, logs, or tool arguments. Keep goals and notes short and redact sensitive user content before logging.

## Honest integration limits

Grok Bot has to wake and invoke this router; this skill provides no pre-wake hook and cannot reduce the cost of waking the bot. Shadow mode is advisory. Active mode is enforceable only insofar as the Grok Bot skill runtime follows this policy. Jev can misclassify or be unavailable, so preserve a safe fallback and use the kill switch when needed. `provider: openjev` (default) reads `OPENJEV_API_KEY`; optional `provider: typesafe` reads `TYPESAFE_API_KEY`. The TypeSafe SDK is not imported for OpenJEV or bypass. Invalid provider/model settings fall back without making a request. Never auto-switch providers on failure. Missing credentials, API errors, or malformed answers produce `proceed_full` with `jev_used: false`, not authorization for irreversible work; normal confirmation rules still apply. Begin with `shadow` and compare decisions before enabling `active`.
