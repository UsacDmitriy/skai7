from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


SERVER_PATH = Path(__file__).with_name("server.py")


def load_server():
    class DummyFastMCP:
        def __init__(self, _name: str) -> None:
            pass

        def tool(self):
            return lambda function: function

        def run(self) -> None:
            pass

    class DummyHTTPStatusError(Exception):
        pass

    httpx = types.ModuleType("httpx")
    httpx.HTTPStatusError = DummyHTTPStatusError
    httpx.Client = object
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda _path: None
    fastmcp = types.ModuleType("mcp.server.fastmcp")
    fastmcp.FastMCP = DummyFastMCP
    sys.modules.update(
        {
            "httpx": httpx,
            "dotenv": dotenv,
            "mcp": types.ModuleType("mcp"),
            "mcp.server": types.ModuleType("mcp.server"),
            "mcp.server.fastmcp": fastmcp,
        }
    )
    spec = importlib.util.spec_from_file_location("cline_mcp_server", SERVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModelRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server()

    def test_committed_registry_contains_supported_routes(self) -> None:
        models, routes = self.server.load_model_registry(
            Path(__file__).with_name("models.env")
        )

        self.assertEqual(models["kimi-k3"], "cline-pass/kimi-k3")
        self.assertEqual(routes["simple"], "minimax")
        self.assertEqual(routes["simple-structured"], "kimi-k3")
        self.assertEqual(routes["code"], "kimi-code")
        self.assertEqual(routes["synthesis"], "deepseek-pro")
        self.assertEqual(routes["review"], "kimi-k3")
        self.assertEqual(routes["review-secondary"], "deepseek-pro")
        self.assertTrue(all(slug.startswith("cline-pass/") for slug in models.values()))
        self.assertTrue(all(alias in models for alias in routes.values()))

    def test_registry_rejects_usage_billing_slug(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                "CLINE_MODEL_UNSAFE=vendor/model\nCLINE_ROUTE_SIMPLE=unsafe\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "cline-pass/"):
                self.server.load_model_registry(registry)

    def test_registry_requires_canonical_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                "CLINE_MODEL_MINIMAX=cline-pass/minimax-m3\n"
                "CLINE_ROUTE_SIMPLE=minimax\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "required canonical routes"):
                self.server.load_model_registry(registry)

    def test_server_source_has_no_versioned_model_slugs(self) -> None:
        source = SERVER_PATH.read_text(encoding="utf-8")
        for versioned_slug in (
            "glm-5.2",
            "kimi-k2.7-code",
            "deepseek-v4-pro",
            "minimax-m3",
            "qwen3.7-max",
        ):
            self.assertNotIn(versioned_slug, source)

    def test_unregistered_subscription_slug_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown ClinePass model alias"):
            self.server._resolve_model("cline-pass/not-in-registry")


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server()

    def setUp(self) -> None:
        self.server.reset_audit()

    def test_audit_reports_prompt_count_hash_and_redacted_instruction(self) -> None:
        prompt = (
            "TASK: classify input\n"
            "CONTEXT_REFS: src/input.json\n"
            "CONTEXT: token=top-secret raw-private-context\n"
            "OUTPUT_CONTRACT: JSON"
        )
        self.server.record_audit(
            model_alias="minimax",
            model_slug="cline-pass/minimax-m3",
            prompt=prompt,
            system=None,
            max_tokens=700,
            status="ok",
            finish_reason="stop",
            usage={"completion_tokens": 12},
            response_chars=42,
        )

        report = json.loads(self.server.audit_report())

        self.assertEqual(report["total_calls"], 1)
        call = report["calls"][0]
        self.assertEqual(call["model"], "minimax")
        self.assertEqual(call["purpose"], "classify input")
        self.assertEqual(call["context_refs"], "src/input.json")
        self.assertEqual(
            call["instruction_preview"],
            "TASK: classify input\nCONTEXT_REFS: src/input.json",
        )
        self.assertEqual(call["prompt_chars"], len(prompt))
        self.assertEqual(len(call["prompt_sha256"]), 64)
        self.assertEqual(call["max_tokens"], 700)
        self.assertEqual(call["status"], "ok")
        self.assertEqual(call["finish_reason"], "stop")
        self.assertNotIn("top-secret", json.dumps(report))
        self.assertNotIn("raw-private-context", json.dumps(report))

    def test_redact_handles_bearer_uri_client_secret_and_private_key(self) -> None:
        raw = (
            "Authorization: Bearer bearer-value client_secret=client-value "
            "postgres://alice:db-password@db.example/skai\n"
            "-----BEGIN PRIVATE KEY-----\nprivate-key-material\n"
            "-----END PRIVATE KEY-----"
        )

        redacted = self.server._redact(raw)

        for secret in (
            "bearer-value",
            "client-value",
            "alice",
            "db-password",
            "private-key-material",
        ):
            self.assertNotIn(secret, redacted)
        self.assertIn("[REDACTED", redacted)

    def test_audit_does_not_retain_system_prompt_or_context(self) -> None:
        prompt = (
            "TASK: bounded review\n"
            "CONTEXT_REFS: api/service.py\n"
            "CONTEXT: private-context-payload"
        )
        system = "system-private-instruction"

        self.server.record_audit(
            model_alias="kimi-k3",
            model_slug="cline-pass/kimi-k3",
            prompt=prompt,
            system=system,
            max_tokens=200,
            status="ok",
            finish_reason="stop",
            usage=None,
            response_chars=12,
        )

        report = json.loads(self.server.audit_report())
        serialized = json.dumps(report)
        self.assertNotIn("private-context-payload", serialized)
        self.assertNotIn("system-private-instruction", serialized)
        self.assertEqual(
            report["calls"][0]["prompt_chars"],
            len(f"SYSTEM: {system}\n{prompt}"),
        )

    def test_audit_reset_clears_task_ledger(self) -> None:
        self.server.record_audit(
            model_alias="minimax",
            model_slug="cline-pass/minimax-m3",
            prompt="TASK: draft",
            system=None,
            max_tokens=100,
            status="error",
            finish_reason=None,
            usage=None,
            response_chars=0,
        )

        self.server.reset_audit()

        self.assertEqual(json.loads(self.server.audit_report())["total_calls"], 0)

    def test_missing_key_is_an_explicit_audited_failure(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            result = self.server._ask("minimax", "TASK: draft", max_tokens=100)

        report = json.loads(self.server.audit_report())
        self.assertIn("[cline bridge error]", result)
        self.assertEqual(report["total_calls"], 1)
        self.assertEqual(report["calls"][0]["status"], "bridge_error")

    def test_api_payload_uses_fireworks_completion_token_field(self) -> None:
        captured: dict[str, object] = {}

        class DummyResponse:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict[str, object]:
                return {
                    "data": {
                        "choices": [
                            {"message": {"content": "ok"}, "finish_reason": "stop"}
                        ]
                    }
                }

        class DummyClient:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                pass

            def post(self, _url: str, *, json: dict[str, object], **_kwargs: object):
                captured.update(json)
                return DummyResponse()

        with (
            mock.patch.dict("os.environ", {"CLINE_API_KEY": "test-key"}, clear=True),
            mock.patch.object(self.server.httpx, "Client", DummyClient),
        ):
            result = self.server._ask("minimax", "TASK: draft", max_tokens=321)

        self.assertEqual(result, "ok")
        self.assertEqual(captured["max_completion_tokens"], 321)
        self.assertNotIn("max_tokens", captured)


if __name__ == "__main__":
    unittest.main()
