<!--
This is the canonical agent-instruction file. CLAUDE.md and GEMINI.md are symlinks to it.
Edit this file, never the symlinks.
-->

# Developing `roblox-playtest-fix`

`roblox-playtest-fix` is a harness-agnostic AI agent skill for Claude Code, OpenAI Codex, Google Antigravity (`agl`), OpenClaw, and Cursor. It autonomously playtests a Roblox game inside Roblox Studio via the official `Roblox_Studio` MCP server, detects functional bugs and target-audience UX/control friction, fixes the root cause in source and Studio `Edit` mode, verifies the fix in live `Play` mode, and locks in regression tests over long multi-cohort runs.

## Architecture & Invariants

1. **Canonical instruction file**: `AGENTS.md` is the canonical file; `CLAUDE.md` and `GEMINI.md` are symlinks to `AGENTS.md`.
2. **Harness-agnostic skill payload**:
   - `skills/roblox-playtest-fix/SKILL.md`: Main workflow instructions. Keep completely free of harness-coupled bash preambles or single-vendor tool assumptions.
   - `skills/roblox-playtest-fix/references/playtest-probes.md`: Self-contained `--!strict` Luau probes executed via `execute_luau` in Studio (`Client`, `Server`, and `Edit` DataModels).
   - `skills/roblox-playtest-fix/agents/openai.yaml`: OpenAI/Codex skill interface metadata.
3. **Manifest synchronization**: `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `gemini-extension.json` must share the exact same SemVer string.

## Deterministic Verification

Before committing or releasing any change, run:

```bash
python3 tests/validate_skill.py
bash -n install.sh
```

When `stylua`, `selene`, and `luau-lsp` are installed on the machine, `python3 tests/validate_skill.py` also validates all 5 embedded `--!strict` Luau probe blocks in `skills/roblox-playtest-fix/references/playtest-probes.md`.
