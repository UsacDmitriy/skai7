# ClinePass MCP bridge

Project-local FastMCP server for auditable routine execution in the `skai_7`
development repository. Claude Opus and Codex Sol remain the owners of requirements,
shared contracts, permissions, sensitive context, integration, deterministic checks,
commits, pushes, and the final answer. Native subagents handle isolated repository
reads, non-overlapping writes, and fresh review.

Routine reading, classification, transformation, draft code/tests, and repetitive
review default to small bounded ClinePass calls. Never send credentials, private or
production data, private media, privileged configuration, unrestricted raw corpora,
or unrestricted repository context. Phase 0, destructive actions, integration, and
final verification are owner-only.

This directory is the canonical replacement for the former `tools/cline-mcp` path.
The bridge, registry, tests, environment example, README, and methodology prompt moved
together so no second registry or route mapping remains.

## Mandatory Phase 0

Before an implementation wave, the owner:

1. Verifies `server.py`, `test_server.py`, `models.env`, `.env.example`, and this
   `README.md`.
2. Keeps exact model slugs and route mappings only in committed `models.env`; keys and
   transport overrides remain only in ignored `.env`.
3. Verifies tracked Claude registration in `.mcp.json` and merges only the tracked
   `.codex/config.toml.example` stanza into local Codex configuration.
4. Runs unit tests, `server.py --selftest`, JSON/TOML parsing, and MCP `initialize`
   plus `tools/list`.
5. Calls `clinepass_config`, `clinepass_audit_reset`, and
   `clinepass_list_models`. When the live endpoint is unavailable, it records the
   committed registry fallback and outage instead of switching providers.

Phase 0 configuration, credentials, and client registration cannot be delegated to a
ClinePass model. This policy applies only to `skai_7`; do not copy it to SKAI
requirements or system-analysis repositories.

## Configuration

1. Copy `.env.example` to `.env`.
2. Put the project-scoped `CLINE_API_KEY` in `.env`.
3. Restart the MCP client after changing `.env`, `models.env`, or `server.py`.

The legacy `tools/cline-mcp/.env` path remains ignored only to prevent an existing
local key from becoming visible to Git during migration. Do not commit, print, or
copy its value to another project; the owner may relocate the same-project local
configuration deliberately.

The tracked Claude command and Codex template both run:

```text
uv run --script tools/clinepass-mcp/server.py
```

Do not overwrite an existing local Codex configuration. Merge only the
`[mcp_servers.clinepass]` stanza from the tracked example.

## Route categories

| Work package | Route category |
| --- | --- |
| Simple draft, classification, non-strict extraction | `simple` |
| Strict structured output or requirements | `simple-structured` |
| Isolated code, tests, or patch proposal | `code` |
| Broad synthesis | `synthesis` |
| Independent review | `review` |

Resolve every route, alias, and exact model slug at runtime only from `models.env`.
This README does not define or duplicate a route-to-model mapping.

## Model family allowlist

Only the Kimi, DeepSeek, Qwen and GLM families are permitted. The registry loader
rejects an alias or slug outside that allowlist at process start, and an unknown or
disallowed alias or route fails closed at call time with no silent fallback to
another model or provider. A newly announced model, including Qwen3.8, enters
`models.env` only after a successful live ClinePass availability check.

Qwen3.8 availability check, 2026-08-04: `cline-pass/qwen3.8-max` answered a bounded live request
successfully and is now registered under the alias `qwen-38-max`, while `cline-pass/qwen3.8-plus` and
the bare `cline-pass/qwen3.8` both returned HTTP 404 "model not found". `GET /models` was unavailable,
so those verdicts come from per-slug live requests, not from a catalogue listing. The registry
therefore holds nine models; the five route defaults are unchanged and none of them maps to Qwen, so
`qwen-38-max` is reached by alias through the generic `ask` tool.

## Package protocol

One call owns one bounded objective:

```text
PACKAGE_ID: stable id shared by calls in one package
ROLE: planner, worker, reviewer, or synthesizer
TASK: exact bounded instruction
CONTEXT_REFS: source paths or identifiers
CONTEXT: minimal required content without secrets
OUTPUT_CONTRACT: required format and owned paths
CHECK: deterministic acceptance check
STOP: blocker conditions and prohibited expansion
```

A non-trivial package uses separate audited calls with one `PACKAGE_ID`: planner,
at least two independent workers, reviewer, and synthesizer. A ClinePass chat
completion cannot spawn native agents or call MCP tools, so prompt-only role
simulation is prohibited. An atomic task may use one worker call when it produces
one independently reviewable candidate with one explicit owner check.

Failures and retries remain separate audit entries. The synthesizer receives explicit
worker success/failure state and cannot hide missing inputs; the owner alone integrates
and accepts the candidate.

## Audit lifecycle

Reset the task ledger with `clinepass_audit_reset`. Before the final response, call
`clinepass_audit_report` and report every success, failure, and retry. Each entry
contains package id, role, model, redacted `TASK` and `CONTEXT_REFS`, prompt size/hash,
token limit, status, finish reason, and usage when available. Raw `CONTEXT`, system
prompts, credentials, and private-key data are not retained.

Report native-subagent delegation separately. If there were no ClinePass calls, state
zero and the exceptional reason: owner-only gate, privacy restriction, or a verified
project-local bridge outage.

## Checks

```bash
python3 -m unittest tools/clinepass-mcp/test_server.py -v
uv run --script tools/clinepass-mcp/server.py --selftest
python3 -m py_compile tools/clinepass-mcp/server.py
```
