# Jev usage router for Grok Bot

This is a recipe for a Grok Bot skill, **not** an automatically installed skill. Follow the [OpenJEV quick start](../README.md) before using it. OpenJEV is the default provider; TypeSafe is an optional alternative configured in the router, not a second service to call. Grok Bot must have access to the repo and the selected provider's key in the router process environment.

## Before each expensive task

1. If `enabled: false`, or the user says `bypass jev` or `no jev`, skip routing and continue normally.
2. Before browser work, multi-source research, a repeated retry, or a subagent, assemble **only a short public/redacted task summary** as JSON. For example:

```json
{
  "goal": "Summarize public release notes",
  "kind": "research",
  "cached_artifact": false,
  "same_error_count": 0,
  "sources_found": 0
}
```

Optional state fields: `cached_note`, `prior_error`, and `constraints`. Never include a key, private conversation, or sensitive raw task text: CLI arguments can appear in process listings.

3. With command-execution permission, run `.venv/bin/python -m src.cli '<redacted JSON state>'` **from the installed repo directory on the computer with the provider key**. Parse `action`, `mode`, and `details` from the JSON output. If the repo, key or execution access is missing, report that routing could not run and continue normally; do not invent a result.
4. If `mode` is `shadow`, report the suggestion separately and proceed using normal Grok Bot judgment. Only in `active` mode follow the action below. Always apply normal approval requirements independently of the router.

## Actions in active mode

- `reuse_cache`: reuse a verified fresh artifact instead of repeating expensive work.
- `stop_retry`: stop the same failing approach; propose another path or ask the user.
- `run_deterministic`: do the bounded lookup, not broad research.
- `chat_only`: answer directly when appropriate.
- `ask_human`: pause before sending, publishing, paying, deleting, or changing permissions.
- `allow_subagent`: use an appropriate available specialist.
- `research_capped`: limit research to `details.max_browser_sources` sources/pages.
- `proceed_full`: continue normally; still require ordinary confirmations.

## Provider selection and limits

Normally no provider change is needed: `config.example.yaml` selects OpenJEV via HTTP, model `openjev`, with `OPENJEV_API_KEY`; **OpenJEV does not require a SDK**. If the owner explicitly selects `provider: typesafe`, the [README](../README.md#optional-alternative-typesafe) covers its separate SDK installation, `TYPESAFE_API_KEY`, and `jev-latest` model. Never send the same task to both providers or switch automatically on errors. Missing credentials, malformed answers and provider errors return `proceed_full` with `jev_used: false`, not permission for irreversible actions.

Grok Bot must wake and run this skill; there is no pre-wake interception. `shadow` is advisory, and `active` works only if the Bot honors the returned action. Jev does not browse, research, execute payments, or override normal confirmation rules.
