# Grok Bot OpenJEV Router

Connect [OpenJEV](https://openjev.sh/docs) to Grok Bot as a decision layer before expensive research, browser work, retries, or subagents. The router suggests actions such as `reuse_cache`, `stop_retry`, `run_deterministic`, `chat_only`, `research_capped`, `allow_subagent`, and `ask_human`. OpenJEV provides access to Jev; this project does not replace Grok Bot's model.

![Grok Bot + Jev dashboard](media/jev-grok-bot-dashboard.png)

See the [demo video](media/jev-grok-bot-demo.mp4) and [architecture](docs/architecture.md).

## Install

```bash
git clone https://github.com/mannnrachman/grok-bot-jev.git
cd grok-bot-jev
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.yaml config.yaml
export OPENJEV_API_KEY=... # set securely; never commit a real key
```

`provider: openjev` is the only supported provider. The default model is `openjev`; other provider/model settings fail closed to the normal Grok Bot path, without sending a request. OpenJEV uses `POST https://api.openjev.sh/v1/systemone`, Bearer authentication, an explicit `state` and five independent typed `questions`, and returns results under `answers`. No TypeSafe SDK is required. Keep `config.yaml`, `.env`, and local logs uncommitted. Do not include credentials or sensitive content in task state.

## Run

```bash
.venv/bin/python scripts/dry_run.py
# or one state:
.venv/bin/python -m src.cli '{"goal":"summarize the latest release notes","kind":"research"}'
```

**These commands make live OpenJEV requests when enabled and a key is set.** For an offline check, set `enabled: false` in `config.yaml` first; the router returns `proceed_full` without a network request. Unit tests are offline:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Copy [`skill/jev-usage-router.SKILL.md`](skill/jev-usage-router.SKILL.md) into the Grok Bot skill runtime. Start with `mode: shadow`: decisions are advisory and should be measured on representative labeled tasks. Switch to `active` only after comparing actions, latency, errors, and usage; the skill must honor the action for it to have an effect. Roll back with `enabled: false` or the `bypass jev` marker. This is not a pre-wake hook.

## Limits and failure behavior

- Requests add latency and usage. The public `openjev` model is a moving alias; thresholds are not guaranteed calibrated.
- Missing credentials, 401/422, exhausted 429/503 retries, timeout, malformed JSON, or invalid answers return `proceed_full` with `jev_used: false`. OpenJEV retries 429/503 and network failures once; numeric `Retry-After` is capped at five seconds.
- The router never performs research, browser actions, payments, or account changes. `ask_human` and normal approval rules remain the bot's responsibility. Shadow mode cannot enforce a decision.
- The [local A/B results](examples/ab_results.md) are proxy measurements, not proof of token savings or universal speedups.

See the [OpenJEV API reference](https://openjev.sh/docs/advanced), [Grok Bot documentation](https://cursor.com/docs/grok-bot), and [contributing guide](CONTRIBUTING.md). Licensed under [MIT](LICENSE).
