@AGENTS.md

# Claude Code Notes

Inherit the owner-orchestrator, native-subagent, mandatory Phase 0, and separate
audited ClinePass-call protocol from `AGENTS.md`. Claude retains shared contracts,
permissions, privacy and security gates, integration, deterministic acceptance,
commits, and the final response. Routine bounded work defaults to ClinePass;
native Claude agents cover independent repository scopes and fresh review.

ClinePass may use only the Kimi, DeepSeek, Qwen and GLM model families. Unknown or
disallowed aliases and routes fail closed without a silent fallback; a newly
announced model, including Qwen3.8, is added only after a successful live
availability check. Exact slugs and routes live only in
`tools/clinepass-mcp/models.env`.

Model routing (owner decision 2026-10-27): DeepSeek is the base —
`deepseek-flash` is the primary subagent model, `deepseek-pro` handles more
complex requests; `glm-53` may join frontend research and `glm-53-flash`
takes simple frontend tasks. Details in `AGENTS.md`.
