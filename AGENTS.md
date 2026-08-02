# Repository Instructions

## Language and naming

- Respond to the user in Russian.
- Keep code, identifiers, comments, and new file/folder names in English.
- Use `alarm`, not `event`, for alert-like domain concepts in code and schemas.
- Quote PostgreSQL column names with double quotes in SQL examples.

## Sources of truth

- The active full-stack contract is `prompts/v2-fullstack/00-CONTRACT.md`.
- The active development plan is `prompts/v2-fullstack/` and
  `init/playbook/00-day-plan.md`.
- Use local demo data from `datasets/ready/` and `datasets/media/`; do not call
  production action APIs without explicit user approval.

## Execution policy

- Claude Opus and Codex Sol are the owners and orchestrators. They own
  requirements, decomposition, shared contracts, permissions, security and
  privacy gates, integration, deterministic verification, commits, and the
  final response.
- Maximize native Claude/Codex subagents for independent reads, isolated
  non-overlapping write scopes, and fresh review. Give each subagent an exact
  goal, owned paths, expected output, check, and stop condition; verify every
  handoff before integration.
- Routine repository reads, classification, transformation, draft code and
  tests, and repetitive review default to small bounded ClinePass calls.
- Direct owner implementation is limited to owner-only gates, high-judgement,
  privacy/security/integration work, or a verified project-local bridge outage.
- Keep secrets, destructive actions, permission-sensitive operations, final
  architecture decisions, repository integration, and acceptance verification
  with Claude/Codex. This development policy applies to `skai_7` only; do not
  apply it to SKAI requirements or system-analysis repositories.

## ClinePass policy

- The project bridge is `tools/clinepass-mcp/server.py`.
- The complete model registry and route selection live only in the committed
  `tools/clinepass-mcp/models.env`. Never hardcode model versions or
  route-to-model mappings in agent files,
  prompts, or bridge code.
- Local connection settings and `CLINE_API_KEY` live only in the ignored
  `tools/clinepass-mcp/.env`; never commit or print secrets.
- Phase 0 is mandatory before every implementation wave. The owner creates or
  verifies the project-scoped bridge files, Claude and Codex registration,
  unit tests, selftest, JSON/TOML parsing, MCP `initialize` and `tools/list`,
  `clinepass_list_models` with model-registry fallback,
  `clinepass_audit_reset`/`clinepass_audit_report`, and the privacy boundary.
  Phase 0 configuration, credentials, and client registration are owner-only.
- At the start of a user task, call `clinepass_audit_reset` if the ClinePass
  bridge is available. Use the route-based ask tool for policy routes and
  verify every useful result before accepting it.
- Documents may name route categories, but every route, alias, and exact model
  slug must be resolved at runtime only from `models.env`.
- A ClinePass prompt contains `PACKAGE_ID`, `ROLE`, `TASK`, `CONTEXT_REFS`, the
  minimum required `CONTEXT`, `OUTPUT_CONTRACT`, `CHECK`, and `STOP` conditions.
  Never send secrets, credentials, private raw datasets, or unnecessary
  repository dumps.
- A non-trivial routine package uses separate audited calls sharing one
  `package_id`: planner, two or more independent workers, reviewer, and
  synthesizer. A ClinePass chat completion cannot spawn native agents or call
  MCP tools; never simulate these roles in one completion. An atomic task may
  use one worker call followed by owner verification.
- ClinePass failure never permits a silent fallback or an unverified result.
  Report the failure and continue directly only as a documented bridge outage
  when Claude/Codex can safely complete and verify the task.

## Mandatory final report

Every final Claude/Codex response must include a `ClinePass delegation report`.
Use `clinepass_audit_report` as the factual source when calls were made. Report total
calls, including failures and retries, and for each call its `package_id`, role,
model, bounded purpose/instruction preview, prompt size or hash, token limit,
status, finish reason, and usage when available. Redact
secret-like values. The audit preview may contain only redacted `TASK` and
`CONTEXT_REFS`; raw `CONTEXT`, system prompts, credentials, and private-key data
must never be retained in the ledger.

If there were no ClinePass calls, explicitly report `Total calls: 0` and the
exceptional reason: owner-only gate, privacy restriction, or verified bridge
outage. Never invent calls. Report native-agent work separately.

## Verification

- Run focused tests for changed behavior, then the relevant broader checks.
- Inspect `git diff --check` and the final staged diff before committing.
- Preserve unrelated user changes and generated/local files.
