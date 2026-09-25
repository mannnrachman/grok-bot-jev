# Architecture

## Architecture A: skill gates around Grok Bot

This package implements an external decision layer rather than changing Grok Bot. A Grok Bot skill prepares a small task state, calls `src.cli` (or the equivalent Python function), and then applies the returned action before expensive work.

```text
user request
    |
    v
Grok Bot wakes and loads the skill
    |
    +--> kill switch / bypass marker? ---- yes ---> normal Grok Bot path
    |
    v
TypeSafe SDK or OpenJEV HTTP systemone(state, questions)
    |
    v
router policy: cache | stop | deterministic | chat | capped research |
                subagent | human approval | full work
    |
    v
Grok Bot executes the action (active) or treats it as advice (shadow)
```

The Python router normalizes state, defines five provider-neutral choice/noul/score questions, applies thresholds and limits, and appends a JSONL decision record without the task goal. `provider: typesafe` (default) uses the official SDK, `TYPESAFE_API_KEY`, and `jev-latest`; `provider: openjev` uses stdlib HTTP, `OPENJEV_API_KEY`, and `openjev`. Invalid provider/model combinations fall back without making a provider request. OpenJEV receives explicit state plus independent questions and returns `answers` keyed by question ID. Neither provider can reference a sibling question's answer in the same request. Credentials are read from the process environment only.

## What works

- Cache reuse, bounded research, retry stopping, direct chat/lookup suggestions, subagent suggestions, and an approval gate for account-changing intents.
- A configuration kill switch and explicit `shadow`/`active` modes.
- Auditable decision records without storing the credential.

## What does not

- This is not a Grok Bot middleware or pre-wake interceptor. The bot must wake, load the skill, and make the router call.
- Shadow mode cannot force behavior. Active mode relies on the installed skill honoring `route.action`.
- Jev does not perform the browser/research/coding work and does not replace Grok Bot's confirmation or safety policy.
- The included A/B results are local proxy measurements, not proof of lower Grok Bot token usage or a universal speedup.

## Failure behavior

If the router is disabled, bypassed, or unavailable, the integration returns `proceed_full` with `jev_used: false` to follow the normal Grok Bot path; it does not send state to another provider. Account and irreversible actions still require human confirmation independently of this router. The TypeSafe SDK owns its 429/529 retries; OpenJEV HTTP retries 429/503 or network errors once (bounded delay and numeric Retry-After). Authentication/validation failures (401/422), invalid JSON and invalid answers are not retried. Logs contain only action, provider, error category and derived signals; do not put sensitive state in a request.
