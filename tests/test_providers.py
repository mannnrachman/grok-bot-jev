import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
from unittest.mock import patch
from urllib.error import HTTPError

from src import jev_client, router

OPTIONS = ["chat", "lookup", "research", "browser", "coding", "write", "account"]
QUESTIONS = {
    "intent": {"type": "choice", "instructions": "Which?", "criteria": {x: x for x in OPTIONS}},
    "reuse_cache": {"type": "noul", "instructions": "Reuse?"},
    "needs_subagent": {"type": "noul", "instructions": "Subagent?"},
    "stop_retry": {"type": "noul", "instructions": "Stop?"},
    "complexity": {"type": "score", "instructions": "Effort?", "criteria": ["low", "mid", "high"]},
}


def answers(intent="chat", reuse=0.1, sub=0.1, stop=0.1, score=1.05):
    probs = {key: (1.0 if key == intent else 0.0) for key in OPTIONS}
    return {
        "intent": {"type": "choice", "choice": intent, "confidence": 0.9, "probabilities": probs},
        "reuse_cache": {"type": "noul", "noul": reuse},
        "needs_subagent": {"type": "noul", "noul": sub},
        "stop_retry": {"type": "noul", "noul": stop},
        "complexity": {"type": "score", "score": score},
    }


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, limit):
        return json.dumps({"model": "openjev", "answers": self.payload}).encode()


class ProviderTests(unittest.TestCase):
    def test_openjev_contract(self):
        def send(request, timeout):
            self.assertEqual(timeout, 10)
            self.assertEqual(request.full_url, jev_client.OPENJEV_URL)
            self.assertEqual(request.get_header("Authorization"), "Bearer test")
            body = json.loads(request.data)
            self.assertEqual(body["model"], "openjev")
            self.assertEqual(body["questions"], QUESTIONS)
            return FakeResponse(answers())

        with patch.dict("os.environ", {"OPENJEV_API_KEY": "test"}), patch.object(jev_client, "urlopen", side_effect=send):
            out = jev_client.system_one({"goal": "hi"}, QUESTIONS, "openjev", "openjev")
        self.assertEqual(out["complexity"], 1.05)
        self.assertEqual(out["intent"], "chat")

    def test_invalid_answer_and_missing_key(self):
        bad = answers()
        bad["reuse_cache"]["noul"] = 1.5
        with self.assertRaises(jev_client.ProviderError):
            jev_client._normalize(bad, QUESTIONS)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(jev_client.ProviderError, "missing_api_key"):
                jev_client.system_one({}, QUESTIONS, "openjev", "openjev")

    def test_provider_models_before_request(self):
        with patch.dict("os.environ", {"OPENJEV_API_KEY": "test", "TYPESAFE_API_KEY": "test"}), patch.object(jev_client, "urlopen") as call:
            for provider, model, category in (("unknown", "openjev", "invalid_provider"), ("openjev", "jev-latest", "invalid_model"), ("typesafe", "openjev", "invalid_model")):
                with self.subTest(provider=provider, model=model), self.assertRaisesRegex(jev_client.ProviderError, category):
                    jev_client.system_one({}, QUESTIONS, provider, model)
            call.assert_not_called()

    def test_typesafe_adapter_matches_openjev_contract(self):
        sdk = ModuleType("typesafe_sdk")

        class Question:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        class Client:
            def __init__(self, model):
                self.model = model

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def system_one(self, state, questions):
                self_outer.assertEqual(self.model, "jev-latest")
                self_outer.assertEqual(set(questions), set(QUESTIONS))
                for name, question in questions.items():
                    self_outer.assertEqual(question.instructions, QUESTIONS[name]["instructions"])
                    if "criteria" in QUESTIONS[name]:
                        self_outer.assertEqual(question.criteria, QUESTIONS[name]["criteria"])
                payload = answers()
                return SimpleNamespace(
                    choices={"intent": SimpleNamespace(**payload["intent"])},
                    nouls={name: SimpleNamespace(**payload[name]) for name in ("reuse_cache", "needs_subagent", "stop_retry")},
                    scores={"complexity": SimpleNamespace(**payload["complexity"])},
                )

        self_outer = self
        sdk.Choice = sdk.Noul = sdk.Score = Question
        sdk.TypeSafeClient = Client
        with patch.dict(sys.modules, {"typesafe_sdk": sdk}), patch.dict("os.environ", {"TYPESAFE_API_KEY": "test"}), patch.object(jev_client, "urlopen") as http:
            result = jev_client.system_one({"goal": "hi"}, QUESTIONS, "typesafe", "jev-latest")
            http.assert_not_called()
        self.assertEqual(result, jev_client._normalize(answers(), QUESTIONS))

    def test_openjev_http_failures(self):
        with patch.dict("os.environ", {"OPENJEV_API_KEY": "test"}):
            for status in (401, 422, 429, 503):
                with self.subTest(status=status):
                    error = HTTPError(jev_client.OPENJEV_URL, status, "bad", {}, None)
                    with patch.object(jev_client, "urlopen", side_effect=error) as call, patch.object(jev_client.time, "sleep"):
                        with self.assertRaisesRegex(jev_client.ProviderError, f"http_{status}"):
                            jev_client._openjev({}, QUESTIONS, "openjev")
                        self.assertEqual(call.call_count, 2 if status in (429, 503) else 1)

    def test_router_actions_and_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(router, "load_config", return_value={"enabled": True, "mode": "shadow", "provider": "openjev"}), patch.object(router, "resolve_log_path", return_value=Path(directory) / "runs.jsonl"):
            for intent, state, signals, action in (
                ("chat", {"goal": "hi"}, {}, "chat_only"),
                ("lookup", {"goal": "find"}, {}, "run_deterministic"),
                ("account", {"goal": "send"}, {}, "ask_human"),
                ("research", {"goal": "read"}, {}, "research_capped"),
                ("coding", {"goal": "code"}, {"needs_subagent": 0.9}, "allow_subagent"),
                ("chat", {"goal": "hi", "cached_artifact": True}, {"reuse_cache": 0.9}, "reuse_cache"),
                ("chat", {"goal": "hi", "same_error_count": 2}, {"stop_retry": 0.9}, "stop_retry"),
            ):
                with self.subTest(action=action), patch.object(router, "system_one", return_value=jev_client._normalize(answers(intent, **{("sub" if k == "needs_subagent" else "reuse" if k == "reuse_cache" else "stop" if k == "stop_retry" else k): v for k, v in signals.items()}), QUESTIONS)):
                    self.assertEqual(router.route_task(state)["action"], action)
            with patch.object(router, "system_one", side_effect=jev_client.ProviderError("http_503")):
                out = router.route_task({"goal": "private"})
                self.assertEqual((out["action"], out["jev_used"]), ("proceed_full", False))
            self.assertNotIn("private", (Path(directory) / "runs.jsonl").read_text())

    def test_bypass_without_sdk(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(router, "load_config", return_value={"enabled": False, "mode": "shadow"}), patch.object(router, "resolve_log_path", return_value=Path(directory) / "runs.jsonl"), patch.object(router, "system_one") as call:
            self.assertEqual(router.route_task({"goal": "skip"})["action"], "proceed_full")
            call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
