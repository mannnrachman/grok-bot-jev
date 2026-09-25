# Grok Bot router — OpenJEV by default

This fork asks [OpenJEV](https://openjev.sh/docs) for a small set of routing decisions before Grok Bot does expensive work. The router suggests actions; it does not replace Grok Bot's model or execute the task. **Start with OpenJEV.** TypeSafe is an optional alternative you can select later; the two providers are never called together and there is no automatic switch on failure.

**Independent project:** this community fork is not affiliated with, endorsed by, or maintained by OpenJEV. Links to OpenJEV documentation describe the external API, not a partnership or an official Grok Bot integration.

![Grok Bot + Jev dashboard](media/jev-grok-bot-dashboard.png)

## Quick start: OpenJEV

Install Python 3.10+ and run these commands on the computer that will actually execute the router. Grok Bot's [cloud computer is separate from your laptop](https://cursor.com/docs/grok-bot/work#your-local-computer-is-separate).

```bash
git clone https://github.com/mannnrachman/grok-bot-jev.git
cd grok-bot-jev
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.yaml config.yaml
.venv/bin/python -m unittest discover -s tests -v
```

The example config already sets `provider: openjev` and `mode: shadow`. Set `OPENJEV_API_KEY` securely **in the environment of the process running the router**. Never place the key in chat, JSON state, command arguments, or Git. `requirements.txt` installs only `pyyaml`: OpenJEV uses Python's standard HTTP client. Its [official quickstart](https://openjev.sh/docs) says *no SDK required; use any HTTP client*. The TypeSafe SDK is **not** used for OpenJEV.

### Check without contacting a provider

Temporarily set `enabled: false` in `config.yaml`, then run:

```bash
.venv/bin/python -m src.cli '{"goal":"Summarize public release notes","kind":"research"}'
```

Expect `"action": "proceed_full"` and `"jev_used": false`. Restore `enabled: true` only when you intend to send the redacted task state to OpenJEV. With the router enabled, the same CLI command and `scripts/dry_run.py` make **live provider requests**. Task text passed on the CLI can be visible in process listings: use only public or redacted summaries.

## Connect to Grok Bot

The [router skill recipe](skill/jev-usage-router.SKILL.md) does not install itself. Give Grok Bot access to this repository **on the computer where the key is configured**, then ask the Bot to save that recipe as a private skill named `jev-usage-router`. Review the saved instructions. Invoke it with `/jev-usage-router` in the Bot composer; [Grok Bot's skill instructions](https://cursor.com/docs/grok-bot/work#skills-and-routines) say to enable a missing private skill under **Settings → Plugins → Yours**.

For a first run, use a non-sensitive task and keep `mode: shadow`: ask the Bot to report the router's recommended action separately from what it actually did. The Bot must be able to execute `.venv/bin/python -m src.cli '<redacted JSON state>'` **from the repository directory**. If command execution or secure access to the key is unavailable, saving the skill alone cannot make the integration work. In `shadow`, recommendations are advisory; in `active`, the Bot must honor them itself. Switch to `active` only after comparing actions, errors, latency and usage on representative tasks. Roll back with `enabled: false` or bypass one request using `bypass jev`.

## Optional alternative: TypeSafe

This is a separate choice, **not an additional step in OpenJEV setup**. To select it instead:

1. Install `typesafe-sdk` separately in the same Python environment.
2. Set `provider: typesafe` in `config.yaml`; leave `model` unset (default `jev-latest`).
3. Supply `TYPESAFE_API_KEY` securely to the router process instead of `OPENJEV_API_KEY`.

The [official TypeSafe Python SDK](https://docs.typesafe.ai/sdk/python.md) is imported only on this path. Do not send an OpenJEV key to TypeSafe or a TypeSafe key to OpenJEV. A mismatched provider/model fails before a request; errors return `proceed_full` rather than switching providers. TypeSafe's SDK retry policy differs from OpenJEV's HTTP retry policy; see [architecture](docs/architecture.md).

## Scope and reference

OpenJEV receives explicit `state` and five independent `questions` at `POST https://api.openjev.sh/v1/systemone`; results appear under `answers`. Choice supplies a label, probabilities and confidence; Score can be fractional; Noul is a yes probability, not an intensity scale. Confidence is not guaranteed correctness. The application—not Jev—performs actions and confirms anything irreversible. See the [quickstart](https://openjev.sh/docs), [advanced reference](https://openjev.sh/docs/advanced), [use cases](https://openjev.sh/use-cases) and [full text reference](https://openjev.sh/llm.txt).

The router recommends `reuse_cache`, `stop_retry`, `run_deterministic`, `chat_only`, `research_capped`, `allow_subagent`, `ask_human`, or `proceed_full`. Missing keys, malformed answers, and exhausted provider errors fall back to `proceed_full` with `jev_used: false`; normal approval requirements still apply. This is not a pre-wake hook, and the [local A/B examples](examples/ab_results.md) do not prove Grok Bot token savings. See the [demo](media/jev-grok-bot-demo.mp4), [media notes](media/README.md), [contributing guide](CONTRIBUTING.md), and [license](LICENSE).
