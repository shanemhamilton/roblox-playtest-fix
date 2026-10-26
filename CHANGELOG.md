# Changelog

All notable changes to `roblox-playtest-fix` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-26

### Added
- Harness-agnostic `roblox-playtest-fix` skill (`skills/roblox-playtest-fix/SKILL.md`) for long, continuous find-reproduce-fix-verify playtest runs in Roblox Studio via the official `Roblox_Studio` MCP server.
- Target-Audience Irritation & Control Friction Matrix covering compound input activations, modal-to-gameplay input bleed, swallowed hold/release events, unforgiving aiming, device prompt mismatches, doorway/step snags, rubber-banding, camera occlusion, slow time-to-first-fun, CoreGui collisions, and untelegraphed damage.
- Five strict-typed (`--!strict`) Luau live telemetry and diagnostic probes (`skills/roblox-playtest-fix/references/playtest-probes.md`) for `execute_luau` across `Client`, `Server`, and `Edit` DataModels:
  1. UI, CoreGui & Mobile Thumbzone Collision Probe (`Client`)
  2. Traversal Snag, Step-Riser & Camera Occlusion Probe (`Client`)
  3. Control Ergonomics, Modal Priority & Prompt Parity Probe (`Client`)
  4. Server Authority, Pacing & Highlight Budget Probe (`Server`)
  5. Studio Script Inventory & Drift Probe (`Edit`)
- Cross-harness packaging and manifests: Claude Code plugin manifests (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`), OpenAI/Codex agent metadata (`skills/roblox-playtest-fix/agents/openai.yaml`), Gemini/Antigravity extension manifest (`gemini-extension.json`), and multi-host `install.sh`.
- Deterministic validation test suite (`tests/validate_skill.py`) checking skill frontmatter, internal links, plugin manifests, and embedded Luau probes.
