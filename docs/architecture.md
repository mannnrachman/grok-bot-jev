# Router architecture

## One provider per request

Grok Bot prepares a short redacted task state and invokes `src.cli`. The router checks `enabled` and bypass markers, then chooses **one** configured provider:

- **OpenJEV (default):** standard-library HTTP to `POST https://api.openjev.sh/v1/systemone`, using `OPENJEV_API_KEY` and model `openjev`. No SDK is required.
- **TypeSafe (optional alternative):** official `typesafe-sdk`, installed separately, using `TYPESAFE_API_KEY` and model `jev-latest`.

The providers are alternative paths to Jev, not a sequence or automatic failover. The router shares the same five question definitions and decision policy across both paths. Questions are independent judgments against the same state: `intent` is a Choice, `complexity` a Score (fractional values allowed), and `reuse_cache`, `needs_subagent`, and `stop_retry` are Noul values. Provider answers are normalized before policy evaluation. Invalid provider/model pairs fail before a request. A missing key or failed call returns `proceed_full` with `jev_used: false` instead of querying the other provider.

## Grok Bot boundary

Grok Bot must wake, invoke the installed skill, and run the router command in the environment containing the selected key. The router does not browse, perform research, run subagents or take external actions. In `shadow` mode the returned action is advice; in `active` mode the skill instructs Grok Bot to honor it. The integration cannot enforce a Bot that ignores its skill and cannot reduce the Bot's wake-up cost. Account changes and other irreversible actions still require independent human confirmation.

## Failure and data handling

OpenJEV does not retry invalid credentials or requests (401/422). It retries 429, 503 and network errors once with bounded delay; numeric `Retry-After` is capped at five seconds. TypeSafe delegates its 429/529 retry handling to the official SDK. Non-JSON or invalid answers are rejected. The router logs action, provider, error category and derived signals rather than the task goal or API key. Nevertheless the state is sent to the selected provider and CLI process arguments may expose task text; pass only short public/redacted summaries.

The [local A/B results](../examples/ab_results.md) are proxy measurements, not proof of universal savings. Start in `shadow`, compare routing decisions, latency, error rate and usage, then consider `active`. Use `enabled: false` to roll back either path. [OpenJEV reference](https://openjev.sh/docs/advanced) · [TypeSafe SDK](https://docs.typesafe.ai/sdk/python.md) · [setup and Grok Bot instructions](../README.md).
