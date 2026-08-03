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

EXPECTED_MODEL_ALIASES = {
    "kimi-k3",
    "kimi-code",
    "kimi",
    "deepseek-pro",
    "deepseek-flash",
    "glm",
    "qwen-max",
    "qwen",
}
EXPECTED_ROUTES = {
    "simple": "deepseek-flash",
    "simple-structured": "kimi-k3",
    "code": "kimi-code",
    "synthesis": "deepseek-pro",
    "review": "kimi-k3",
}
EXPECTED_LIVE_TOOLS = {
    "ask",
    "ask_deepseek",
    "ask_deepseek_flash",
    "ask_glm",
    "ask_kimi",
    "ask_kimi_code",
    "ask_kimi_k3",
    "ask_qwen",
    "ask_qwen_max",
    "ask_route",
    "audit_report",
    "clinepass_audit_report",
    "clinepass_audit_reset",
    "clinepass_config",
    "clinepass_list_models",
    "configured_models",
    "reset_audit",
}


def load_server():
    class DummyFastMCP:
        def __init__(self, _name: str) -> None:
            self.registered_tools: dict[str, str] = {}

        def tool(self):
            def decorator(function):
                self.registered_tools[function.__name__] = function.__doc__ or ""
                return function

            return decorator

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

    def test_committed_registry_is_limited_to_the_four_allowed_families(self) -> None:
        models, routes = self.server.load_model_registry(
            Path(__file__).with_name("models.env")
        )

        self.assertEqual(set(models), EXPECTED_MODEL_ALIASES)
        self.assertEqual(routes, EXPECTED_ROUTES)
        self.assertEqual(len(models), 8)
        self.assertEqual(len(routes), 5)
        self.assertTrue(all(slug.startswith("cline-pass/") for slug in models.values()))
        self.assertTrue(all(alias in models for alias in routes.values()))

    def test_allowed_families_constant_is_exactly_the_four_families(self) -> None:
        self.assertEqual(
            tuple(self.server.ALLOWED_MODEL_FAMILIES),
            ("kimi", "deepseek", "qwen", "glm"),
        )

    def test_registry_rejects_alias_outside_the_family_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                "CLINE_MODEL_OTHER=cline-pass/other\n"
                "CLINE_ROUTE_SIMPLE=other\n"
                "CLINE_ROUTE_SIMPLE_STRUCTURED=other\n"
                "CLINE_ROUTE_CODE=other\n"
                "CLINE_ROUTE_SYNTHESIS=other\n"
                "CLINE_ROUTE_REVIEW=other\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported model aliases"):
                self.server.load_model_registry(registry)

    def test_registry_rejects_slug_family_hidden_behind_allowed_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                "CLINE_MODEL_KIMI=cline-pass/other-model\n"
                "CLINE_ROUTE_SIMPLE=kimi\n"
                "CLINE_ROUTE_SIMPLE_STRUCTURED=kimi\n"
                "CLINE_ROUTE_CODE=kimi\n"
                "CLINE_ROUTE_SYNTHESIS=kimi\n"
                "CLINE_ROUTE_REVIEW=kimi\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported model slugs"):
                self.server.load_model_registry(registry)

    def test_registry_rejects_duplicate_slugs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                "CLINE_MODEL_KIMI=cline-pass/kimi-k3\n"
                "CLINE_MODEL_KIMI_K3=cline-pass/kimi-k3\n"
                "CLINE_ROUTE_SIMPLE=kimi\n"
                "CLINE_ROUTE_SIMPLE_STRUCTURED=kimi\n"
                "CLINE_ROUTE_CODE=kimi\n"
                "CLINE_ROUTE_SYNTHESIS=kimi\n"
                "CLINE_ROUTE_REVIEW=kimi\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate model slugs"):
                self.server.load_model_registry(registry)

    def test_registry_rejects_usage_billing_slug(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                "CLINE_MODEL_KIMI=vendor/model\nCLINE_ROUTE_SIMPLE=kimi\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "cline-pass/"):
                self.server.load_model_registry(registry)

    def test_registry_requires_canonical_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                f"CLINE_MODEL_DEEPSEEK_FLASH={self.server.MODELS['deepseek-flash']}\n"
                "CLINE_ROUTE_SIMPLE=deepseek-flash\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "required canonical routes"):
                self.server.load_model_registry(registry)

    def test_registry_rejects_noncanonical_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            slug = self.server.MODELS["deepseek-flash"]
            registry.write_text(
                f"CLINE_MODEL_DEEPSEEK_FLASH={slug}\n"
                "CLINE_ROUTE_SIMPLE=deepseek-flash\n"
                "CLINE_ROUTE_SIMPLE_STRUCTURED=deepseek-flash\n"
                "CLINE_ROUTE_CODE=deepseek-flash\n"
                "CLINE_ROUTE_SYNTHESIS=deepseek-flash\n"
                "CLINE_ROUTE_REVIEW=deepseek-flash\n"
                "CLINE_ROUTE_REVIEW_SECONDARY=deepseek-flash\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "noncanonical routes"):
                self.server.load_model_registry(registry)

    def test_routes_must_reference_known_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "models.env"
            registry.write_text(
                f"CLINE_MODEL_KIMI={self.server.MODELS['kimi']}\n"
                "CLINE_ROUTE_SIMPLE=kimi-missing\n"
                "CLINE_ROUTE_SIMPLE_STRUCTURED=kimi\n"
                "CLINE_ROUTE_CODE=kimi\n"
                "CLINE_ROUTE_SYNTHESIS=kimi\n"
                "CLINE_ROUTE_REVIEW=kimi\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unknown model aliases"):
                self.server.load_model_registry(registry)

    def test_server_source_has_no_exact_model_slugs(self) -> None:
        source = SERVER_PATH.read_text(encoding="utf-8")
        for slug in self.server.MODELS.values():
            self.assertNotIn(slug, source)

    def test_unregistered_subscription_slug_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown ClinePass model alias"):
            self.server._resolve_model("cline-pass/not-in-registry")

    def test_resolve_model_fails_closed_without_a_silent_default(self) -> None:
        for unknown_alias in ("", "unknown", "other", "other-pro", "deepseek"):
            with self.assertRaisesRegex(ValueError, "Unknown ClinePass model alias"):
                self.server._resolve_model(unknown_alias)


class LiveToolMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server()

    def test_live_tool_inventory_matches_the_four_family_contract(self) -> None:
        self.assertEqual(
            set(self.server.mcp.registered_tools), EXPECTED_LIVE_TOOLS
        )
        self.assertEqual(len(self.server.mcp.registered_tools), 17)

    def test_no_tool_is_declared_outside_the_expected_inventory(self) -> None:
        source = SERVER_PATH.read_text(encoding="utf-8")

        self.assertEqual(source.count("@mcp.tool()"), len(EXPECTED_LIVE_TOOLS))
        for tool_name in self.server.mcp.registered_tools:
            self.assertIn(tool_name, EXPECTED_LIVE_TOOLS)

        model_tools = {
            name
            for name in self.server.mcp.registered_tools
            if name.startswith("ask_") and name != "ask_route"
        }
        families = {name.removeprefix("ask_").split("_")[0] for name in model_tools}
        self.assertEqual(families, set(self.server.ALLOWED_MODEL_FAMILIES))

    def test_tool_descriptions_never_duplicate_exact_slugs(self) -> None:
        descriptions = " ".join(self.server.mcp.registered_tools.values())
        for slug in self.server.MODELS.values():
            self.assertNotIn(slug, descriptions)

    def test_generic_ask_tool_points_at_the_committed_registry(self) -> None:
        self.assertIn("models.env", self.server.mcp.registered_tools["ask"])

    def test_tool_descriptions_carry_no_optional_delegation_wording(self) -> None:
        descriptions = " ".join(self.server.mcp.registered_tools.values()).lower()
        for forbidden in ("optional delegation", "optionally", "if available"):
            self.assertNotIn(forbidden, descriptions)

    def test_config_reports_eight_models_and_five_routes(self) -> None:
        report = self.server.clinepass_config()

        model_lines = [
            line for line in report.splitlines() if line.startswith("  ") and "->" in line
        ]
        self.assertEqual(len(model_lines), 13)
        for alias in EXPECTED_MODEL_ALIASES:
            self.assertIn(alias, report)
        for route in EXPECTED_ROUTES:
            self.assertIn(route, report)
        self.assertEqual(len(self.server.MODELS), 8)
        self.assertEqual(len(self.server.ROUTES), 5)


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
            model_alias="deepseek-flash",
            model_slug=self.server.MODELS["deepseek-flash"],
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
        self.assertEqual(call["model"], "deepseek-flash")
        self.assertEqual(call["package_id"], "atomic-unscoped")
        self.assertEqual(call["role"], "worker")
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

    def test_audit_records_package_and_role_without_context(self) -> None:
        prompt = (
            "PACKAGE_ID: skai7-policy-20260802\n"
            "ROLE: reviewer\n"
            "TASK: review policy\n"
            "CONTEXT_REFS: AGENTS.md\n"
            "CONTEXT: private-review-input"
        )
        self.server.record_audit(
            model_alias="kimi-k3",
            model_slug=self.server.MODELS["kimi-k3"],
            prompt=prompt,
            system=None,
            max_tokens=500,
            status="ok",
            finish_reason="stop",
            usage=None,
            response_chars=10,
        )

        report = json.loads(self.server.audit_report())
        call = report["calls"][0]
        self.assertEqual(call["package_id"], "skai7-policy-20260802")
        self.assertEqual(call["role"], "reviewer")
        self.assertNotIn("private-review-input", json.dumps(report))

    def test_canonical_audit_aliases_share_one_ledger(self) -> None:
        self.server.clinepass_audit_reset()
        self.server.record_audit(
            model_alias="deepseek-flash",
            model_slug=self.server.MODELS["deepseek-flash"],
            prompt="TASK: draft",
            system=None,
            max_tokens=100,
            status="error",
            finish_reason=None,
            usage=None,
            response_chars=0,
        )

        report = json.loads(self.server.clinepass_audit_report())
        self.assertEqual(report["total_calls"], 1)

    def test_list_models_reports_registry_fallback_without_key(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            result = json.loads(self.server.clinepass_list_models())

        self.assertEqual(result["status"], "registry_fallback")
        self.assertEqual(set(result["models"]), EXPECTED_MODEL_ALIASES)

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
            model_slug=self.server.MODELS["kimi-k3"],
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
            model_alias="deepseek-flash",
            model_slug=self.server.MODELS["deepseek-flash"],
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
            result = self.server._ask("deepseek-flash", "TASK: draft", max_tokens=100)

        report = json.loads(self.server.audit_report())
        self.assertIn("[cline bridge error]", result)
        self.assertEqual(report["total_calls"], 1)
        self.assertEqual(report["calls"][0]["status"], "bridge_error")

    def test_unknown_alias_raises_before_any_transport_call(self) -> None:
        class ExplodingClient:
            def __init__(self, **_kwargs: object) -> None:
                raise AssertionError("transport must not be reached")

        with (
            mock.patch.dict("os.environ", {"CLINE_API_KEY": "test-key"}, clear=True),
            mock.patch.object(self.server.httpx, "Client", ExplodingClient),
        ):
            with self.assertRaisesRegex(ValueError, "Unknown ClinePass model alias"):
                self.server.ask("other", "TASK: draft", max_tokens=100)
            with self.assertRaisesRegex(ValueError, "Unknown ClinePass model alias"):
                self.server._ask("other-pro", "TASK: draft", max_tokens=100)

        self.assertEqual(json.loads(self.server.audit_report())["total_calls"], 0)

    def test_unknown_route_raises_before_any_transport_call(self) -> None:
        class ExplodingClient:
            def __init__(self, **_kwargs: object) -> None:
                raise AssertionError("transport must not be reached")

        with (
            mock.patch.dict("os.environ", {"CLINE_API_KEY": "test-key"}, clear=True),
            mock.patch.object(self.server.httpx, "Client", ExplodingClient),
        ):
            with self.assertRaisesRegex(ValueError, "Unknown ClinePass route"):
                self.server.ask_route("unknown", "TASK: draft", max_tokens=100)

        self.assertEqual(json.loads(self.server.audit_report())["total_calls"], 0)

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
            result = self.server._ask("deepseek-flash", "TASK: draft", max_tokens=321)

        self.assertEqual(result, "ok")
        self.assertEqual(captured["model"], self.server.MODELS["deepseek-flash"])
        self.assertEqual(captured["max_completion_tokens"], 321)
        self.assertNotIn("max_tokens", captured)


if __name__ == "__main__":
    unittest.main()
