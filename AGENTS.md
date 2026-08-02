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

- Claude and Codex are the primary direct executors and orchestrators. They own
  analysis, implementation, integration, safety decisions, and verification.
- Use native Claude/Codex agents as much as practical. Delegate independent,
  well-bounded work to them and run safe independent tracks in parallel. The
  lead agent remains responsible for reconciling changes and testing the result.
- Do not decompose work merely to send it through ClinePass. ClinePass is an
  optional auxiliary layer for suitable simple, repetitive, high-volume, or
  self-contained tasks when delegation provides a clear benefit.
- Keep secrets, destructive actions, permission-sensitive operations, final
  architecture decisions, repository integration, and acceptance verification
  with Claude/Codex and their native agents.

## ClinePass policy

- The project bridge is `tools/cline-mcp/server.py`.
- The complete model registry and route selection live only in the committed
  `tools/cline-mcp/models.env`. Never hardcode model versions in agent files,
  prompts, or bridge code.
- Local connection settings and `CLINE_API_KEY` live only in the ignored
  `tools/cline-mcp/.env`; never commit or print secrets.
- At the start of a user task, call `reset_audit()` if the ClinePass bridge is
  available. Use `ask_route()` for policy routes and verify every useful result
  before accepting it.
- Recommended routes: `simple` for drafts/classification, `simple-structured` for
  strict structured extraction, `code` for isolated code/test proposals,
  `synthesis` for broad synthesis, and `review` for independent review. For a
  high-risk panel, make two explicit calls: `review` (Kimi K3) and `synthesis`
  (DeepSeek Pro); do not introduce an additional panel route.
- A ClinePass prompt should contain `TASK`, `CONTEXT_REFS`, the minimum required
  `CONTEXT`, `OUTPUT_CONTRACT`, `CHECK`, and `STOP` conditions. Never send
  secrets, credentials, private raw datasets, or unnecessary repository dumps.
- ClinePass failure never permits a silent fallback or an unverified result.
  Report the failure and continue directly only when Claude/Codex can safely
  complete and verify the task.

## Mandatory final report

Every final Claude/Codex response must include a `ClinePass delegation report`.
Use `audit_report()` as the factual source when calls were made. Report total
calls and, for each call, its model, purpose/instruction preview, prompt size or
hash, token limit, status, finish reason, and usage when available. Redact
secret-like values. The audit preview may contain only redacted `TASK` and
`CONTEXT_REFS`; raw `CONTEXT`, system prompts, credentials, and private-key data
must never be retained in the ledger.

If there were no ClinePass calls, explicitly report `Total calls: 0` and the
reason, for example: direct Claude/Codex work with native agents was sufficient,
or the task was unsuitable for external delegation. Never invent calls.

## Verification

- Run focused tests for changed behavior, then the relevant broader checks.
- Inspect `git diff --check` and the final staged diff before committing.
- Preserve unrelated user changes and generated/local files.
