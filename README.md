# OpenJEV router for Grok Bot

Route Grok Bot tasks through [OpenJEV](https://openjev.sh/docs) before expensive work. The router recommends reusing a cached result, stopping repeated failures, doing a bounded lookup/research task, using a subagent, or asking for human approval. **OpenJEV is the default; the official TypeSafe SDK remains available as an optional provider.** Both providers access Jev; this repository neither replaces Grok Bot's model nor installs a pre-wake hook.

![Grok Bot + Jev dashboard](media/jev-grok-bot-dashboard.png)

## 1. Install on the computer that will run the router

Install Python 3.10+ and clone this fork into the environment accessible to Grok Bot (normally its [shared cloud computer](https://cursor.com/docs/grok-bot/work), **not** your separate local laptop):

```bash
git clone https://github.com/mannnrachman/grok-bot-jev.git
cd grok-bot-jev
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.yaml config.yaml
```

The complete requirements include the TypeSafe SDK; if you will **only use OpenJEV**, `.venv/bin/pip install pyyaml` is sufficient. The OpenJEV adapter uses Python's standard HTTP library; it does not import the SDK. Keep `config.yaml` and credentials out of Git.

Set `OPENJEV_API_KEY` in the **router process environment**, not in a chat message, command argument, JSON state, or committed file. Use a secure secret facility if your Bot environment provides one. The Bot's cloud computer and your local terminal have separate environments. If the Bot cannot access a secure runtime key, do not ask it to paste the key into chat: run the router in a trusted environment with access to the key instead.

`config.yaml` copied from the example uses `provider: openjev`, `mode: shadow`, and the `openjev` model alias. No TypeSafe key is needed for this path. For the optional TypeSafe path, set `provider: typesafe`, omit `model` (or use `jev-latest`), install the full requirements and provide `TYPESAFE_API_KEY` in that process environment. Provider/model mismatches fail without a provider request; failures never switch providers automatically.

## 2. Verify locally on that computer

Run offline tests first; these do not contact either provider:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

For a **no-network** routing check, temporarily set `enabled: false` in `config.yaml`, then run:

```bash
.venv/bin/python -m src.cli '{"goal":"Summarize the release notes","kind":"research"}'
```

Expect `"action": "proceed_full"` and `"jev_used": false`. Re-enable the router only when the key is available securely and you intend to send task state to the selected provider. The same command, or `scripts/dry_run.py`, makes **live API requests** when enabled; do not run it as an offline smoke test. Its output may contain task-derived signals; keep task state short and redacted.

## 3. Connect it to Grok Bot

The [integration skill](skill/jev-usage-router.SKILL.md) is a **recipe**, not an automatically installed Bot skill. In [Grok Bot](https://cursor.com/docs/grok-bot/get-started), create or select a Bot with access to the router's computer. Ask the Bot to save the integration instructions as a private skill, or provide the skill file and have it create a saved skill named `jev-usage-router`. Check the saved skill before enabling it. [Grok Bot's skill guide](https://cursor.com/docs/grok-bot/work#skills-and-routines) says to invoke saved skills with `/` in the composer; if yours does not appear, enable it for that Bot under **Settings → Plugins → Yours**. Saving a skill alone does not install this Python repo, configure an API key, or guarantee that the Bot can execute the router.

Start with a non-sensitive task and invoke the saved skill explicitly, for example: `/jev-usage-router Summarize these public release notes; use shadow mode and report the router action separately from your normal decision.` The skill should assemble a compact JSON state, execute `.venv/bin/python -m src.cli '<json state>'` **from the repo directory on the computer with the key**, parse its JSON output, and treat the recommendation as advice in `shadow`. Confirm it can execute commands in that environment; local execution can require approval under [Grok Bot's computer policy](https://cursor.com/docs/grok-bot/work#your-local-computer-is-separate). If commands cannot run there, the integration cannot operate just by pasting a skill into chat.

Only after testing representative tasks and comparing actions, latency, failures and usage should you change `mode: active`. In active mode the Bot must actually honor `route.action`; neither the router nor a saved skill can enforce compliance by itself. Roll back immediately with `enabled: false`, or bypass a single request with `bypass jev`.

## What the router does and does not do

- OpenJEV sends `state` and five independent `questions` via `POST https://api.openjev.sh/v1/systemone`, using a server-side Bearer key, and reads `answers`. Its public `openjev` model is a moving alias. See the [official OpenJEV API reference](https://openjev.sh/docs/advanced).
- The optional TypeSafe adapter uses the [official Python SDK](https://docs.typesafe.ai/sdk/python.md). Only the selected provider's environment key is read.
- The router returns `reuse_cache`, `stop_retry`, `run_deterministic`, `chat_only`, `research_capped`, `allow_subagent`, `ask_human`, or `proceed_full`. It does **not** perform research, clicks, payments, sends, account changes, or human approval. The [skill](skill/jev-usage-router.SKILL.md) explains how to handle these actions; normal confirmation rules still apply.
- Missing keys, invalid answers and exhausted provider errors yield `proceed_full` with `jev_used: false`. OpenJEV retries 429/503 and network failures once, honors numeric `Retry-After` up to five seconds, and does not retry 401/422. The TypeSafe SDK handles its own retries, including 429/529.
- No exact Grok Bot token savings are promised. The [A/B examples](examples/ab_results.md) are local proxy measurements; see the [architecture](docs/architecture.md) for limitations and fallback.

The [demo video](media/jev-grok-bot-demo.mp4) and [media notes](media/README.md) illustrate the integration. Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). License: [MIT](LICENSE).
