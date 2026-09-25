# Grok Bot task router — OpenJEV by default

This community project lets Grok Bot ask [OpenJEV](https://openjev.sh/docs) for a routing *recommendation* before expensive work. For example, it may suggest reusing a fresh result, stopping a repeated failure, limiting research, or asking a human. **It does not automatically run inside Grok Bot.** The Bot must invoke the router and follow its result. OpenJEV is the default; TypeSafe is a separate, optional provider choice.

**Independent project:** not affiliated with, endorsed by, or maintained by OpenJEV. This is not an official Grok Bot integration.

![Router dashboard illustration](media/jev-grok-bot-dashboard.png)

## Start here: OpenJEV

### 1. Install where the router will run

Use Python 3.10+ on the machine whose terminal Grok Bot will use. Grok Bot's [cloud computer](https://cursor.com/docs/grok-bot/work#the-computer-and-apps) is separate from your laptop; installing this repository locally does not install it there.

```bash
git clone https://github.com/mannnrachman/grok-bot-jev.git
cd grok-bot-jev
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.yaml config.yaml
.venv/bin/python -m unittest discover -s tests -v
```

The example starts with `provider: openjev` and `mode: shadow`. The only package in `requirements.txt` is `pyyaml`. OpenJEV uses standard-library HTTP; its [quickstart](https://openjev.sh/docs) says no SDK is required.

### 2. Make a key available to the router

Create an OpenJEV API key using the [OpenJEV dashboard](https://openjev.sh/dashboard). The running Python process needs `OPENJEV_API_KEY` in **its own environment**. The repository does **not** read `.env`, `config.yaml`, or a saved Grok Bot skill for credentials. A key set in a terminal on your laptop is not automatically available in Grok Bot's cloud terminal, and a key set in one shell session may not be present in a later Bot command.

Do not paste the key into ordinary Bot chat, a CLI argument, a Git file, or a skill. [Grok Bot's computer guide](https://cursor.com/docs/grok-bot/work#take-over-for-sensitive-steps) describes secure secret requests *for supported connections*, but does not document automatic injection of such secrets as `OPENJEV_API_KEY` for arbitrary Python subprocesses. **If you cannot provide that environment variable securely and verify that the Bot-run process receives it, stop here:** offline tests will still work, but live routing will fall back as `missing_api_key`. The cloud computer is shared among your own Bots; treat credentials on it accordingly.

### 3. Verify without spending an API request

The unit tests above are offline. To check the CLI and installation without a provider request, temporarily change `enabled: false` in your ignored `config.yaml`, then run from the repository directory:

```bash
.venv/bin/python -m src.cli '{"goal":"Summarize public release notes","kind":"research"}'
```

The result should contain `"action": "proceed_full"` and `"jev_used": false`. **This checks bypass only, not OpenJEV authentication or response quality.** Restore `enabled: true` before an intentional live run. With the router enabled, this command and `scripts/dry_run.py` may send data to the selected provider. Only use public or redacted task summaries: CLI arguments may be visible in process listings.

### 4. Have Grok Bot invoke it

The [router skill recipe](skill/jev-usage-router.SKILL.md) is instructions, **not an installed skill**. In Grok Bot, give a Bot access to the cloned repository on the computer that runs the router. Provide that recipe and ask the Bot to save it as a private skill named `jev-usage-router`; inspect the saved skill before using it. [Grok Bot's guide](https://cursor.com/docs/grok-bot/work#skills-and-routines) says to invoke a saved skill with `/` in the composer and to enable missing private skills in **Settings → Plugins → Yours**.

Start with a **public, non-sensitive** task and `mode: shadow`. Ask the Bot to invoke `/jev-usage-router`, run the CLI from the installed repository, and show the CLI's actual `action`, `jev_used`, `mode`, and `details.provider` before it proceeds normally. If the output says `jev_used: false`, check `details.error` (for example, `missing_api_key`); that is **not** proof of a successful OpenJEV call. A recommendation with `jev_used: true` shows that the router accepted a provider response, but does not prove the recommendation was correct. We have not verified this complete Grok Bot workflow in a live Bot session.

`shadow` only reports advice. Switch to `mode: active` **only after** checking decisions against representative tasks, latency, failures and usage; then the Bot must actually honor `action`. Neither a skill nor this code can force a Bot that ignores it. To stop, set `enabled: false` in `config.yaml` or say `bypass jev` for a single request. Actions never override normal approvals for payments, messages, deletion, or account changes.

## TypeSafe: optional alternative, not part of OpenJEV setup

If you intentionally want to use TypeSafe **instead of** OpenJEV, install `typesafe-sdk` separately in the same Python environment, set `provider: typesafe` in `config.yaml` (leave `model` unset for `jev-latest`), and make `TYPESAFE_API_KEY` available to the router process. See the [TypeSafe SDK documentation](https://docs.typesafe.ai/sdk/python.md). Only one provider is called per request; failures do **not** switch providers. The TypeSafe SDK is not needed for OpenJEV. This alternative is covered by offline mocks; an end-to-end SDK call has not been verified here.

## What it sends and returns

For OpenJEV, the router sends a short `state` and five independent typed `questions` to `POST https://api.openjev.sh/v1/systemone` and reads the returned `answers`. The `openjev` model alias is not pinned to a version. Choice returns a label and probabilities, Score can be fractional, and Noul is a yes probability—not intensity; confidence is not a correctness guarantee. Application policy chooses the action; OpenJEV does not execute it. See the [official quickstart](https://openjev.sh/docs), [advanced reference](https://openjev.sh/docs/advanced), [use cases](https://openjev.sh/use-cases), and [full text reference](https://openjev.sh/llm.txt).

The router may recommend `reuse_cache`, `stop_retry`, `run_deterministic`, `chat_only`, `research_capped`, `allow_subagent`, `ask_human`, or `proceed_full`. Missing credentials, invalid answers or exhausted provider errors return `proceed_full` with `jev_used: false`. See [architecture and failure handling](docs/architecture.md) and the [skill action rules](skill/jev-usage-router.SKILL.md). [Local A/B examples](examples/ab_results.md) are proxy measurements, not proof of Grok Bot token savings. [Demo](media/jev-grok-bot-demo.mp4) · [Media](media/README.md) · [Contributing](CONTRIBUTING.md) · [License](LICENSE).
