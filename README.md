# roblox-playtest-fix

[![Release](https://img.shields.io/github/v/release/shanemhamilton/roblox-playtest-fix?sort=semver&label=release)](https://github.com/shanemhamilton/roblox-playtest-fix/releases)
[![License: MIT](https://img.shields.io/github/license/shanemhamilton/roblox-playtest-fix)](LICENSE)

**Autonomous Roblox Studio playtester, target-audience UX friction hunter, and closed-loop bugfixer for Claude Code, Codex, Google Antigravity (`agl`), OpenClaw, and Cursor.**

Static linters (`stylua`, `selene`, `luau-lsp`) and mocked unit tests verify code syntax and isolated logic, but they cannot feel an awkward jump-to-flight transition, a modal button that accidentally triggers a combat ability underneath, a porch threshold that snags a character's feet, a skip button hidden behind Roblox's top-right `PlayerList`, or a passive phase timer that bores players into leaving.

`roblox-playtest-fix` connects to Roblox Studio through the official **Roblox Studio MCP server**, plays your game across a structured 5-cohort expedition, hunts for functional bugs and annoying controls/configurations, fixes the root cause in disk source and Studio `Edit` mode, replays the exact scenario to verify the fix, locks in a regression test, and continues to the next cohort.

---

## What it does

- **Actually plays the game in Studio**: Uses `start_stop_play`, `character_navigation`, `user_keyboard_input`, `user_mouse_input`, `execute_luau`, `screen_capture`, and `get_console_output` to traverse real world paths, press/hold abilities, click modals, and inspect live `Client` and `Server` state.
- **Hunts target-audience irritation & control friction**: Evaluates every interaction against a concrete friction matrix:
  - *Control & input irritations*: Compound/fussy activations, modal-to-gameplay input bleed, swallowed hold/release events (`UserInputState.Change`), unforgiving aiming without cone/proximity assist, and wrong device prompts (`Keyboard` vs. `Gamepad` vs. `Touch`).
  - *Camera, movement & spatial irritations*: Doorway and step-riser snags (`> 0.4` studs), server anti-cheat rubber-banding or false-positive fall recovery, low camera framing on small rigs, and foliage/props with `CanQuery = true` popping the camera.
  - *Pacing, UI & configuration irritations*: Slow time-to-first-fun (`> 30s`), unskippable intros or long summary timers, collisions with Roblox's `PlayerList` / TopBar / mobile `TouchGui` Jump button, `< 48x48` px touch targets, `Highlight` pool exhaustion (`> 31` instances), and untelegraphed enemy strikes.
- **Enforces the Iron Law of Playtest Fixes**: *No fix without live reproduction evidence* (exact input sequence + console/telemetry probe output + `PreFix_<slug>` viewport capture).
- **Zero drift between disk and Studio**: Stops Play mode (`is_start: false`), patches tracked source files on disk (`src/`) and mirrors edits to Studio `Edit` mode (`multi_edit`) when Rojo live sync is not running, runs static checks, and re-verifies in live Play mode (`PostFix_<slug>`).
- **Built for long autonomous runs**: Works through a **5-Cohort Expedition Backlog** with a live **Playtest Ledger**, a **3-Strike Circuit Breaker** per defect so runs never stall, and periodic full-suite regression gates.

---

## Prerequisites

1. **Roblox Studio** with the built-in MCP server enabled (**Assistant → ⋯ → Manage MCP Servers → Enable Studio as MCP server**).
2. **An MCP-capable coding agent**: Claude Code, Codex CLI, Google Antigravity (`agl`), OpenClaw, or Cursor connected to `Roblox_Studio`.
3. *(Optional, for file-synced repos)*: `rojo`, `stylua`, `selene`, and `luau-lsp`.

---

## Install

### Option 1: Multi-host installer (`Claude Code`, `Codex`, `Antigravity`, `OpenClaw`)

```bash
curl -fsSL https://raw.githubusercontent.com/shanemhamilton/roblox-playtest-fix/main/install.sh -o /tmp/roblox-playtest-fix-install.sh
bash /tmp/roblox-playtest-fix-install.sh --all
```

Or target specific hosts (`--claude`, `--codex`, `--agy`, or `--symlink` from a local clone):

```bash
git clone https://github.com/shanemhamilton/roblox-playtest-fix.git ~/Projects/roblox-playtest-fix
~/Projects/roblox-playtest-fix/install.sh --all --symlink
```

### Option 2: Claude Code Plugin Marketplace

```text
/plugin marketplace add shanemhamilton/roblox-playtest-fix
/plugin install roblox-playtest-fix@roblox-playtest-fix
```

---

## Use

Invoke the skill in your agent session (`$roblox-playtest-fix` in Codex, `/roblox-playtest-fix` in Claude Code / Antigravity, or in natural language):

| Prompt / Command | Outcome |
|---|---|
| `/roblox-playtest-fix` | Run the full 5-cohort autonomous playtest-and-fix expedition in Roblox Studio. |
| `Use $roblox-playtest-fix to test onboarding and mobile/gamepad controls` | Focus the playtest-and-fix loop on Cohorts 1 and 3 (FTUE, modals, input prompts, and thumbzones). |
| `Use $roblox-playtest-fix to hunt movement snags and camera issues` | Run Cohort 2 traversal paths with the live Traversal Snag & Camera Occlusion probe and fix colliders/offsets. |
| `/goal Use /roblox-playtest-fix for a long run across all 5 cohorts` | Run an extended multi-cycle marathon, fixing issues, adding regression tests, and committing atomic fixes as it goes. |

---

## Bundled Live Playtest Probes (`execute_luau`)

[`skills/roblox-playtest-fix/references/playtest-probes.md`](skills/roblox-playtest-fix/references/playtest-probes.md) includes 5 ready-to-run `--!strict` Luau probes:

1. **UI, CoreGui & Mobile Thumbzone Collision Probe (`Client`)**: Finds `< 48x48` px buttons, overlapping controls, collisions with Roblox's top-right `PlayerList`, TopBar inset, or mobile Jump button, and transparent `Active = true` frames swallowing camera drag.
2. **Traversal Snag, Step-Riser & Camera Occlusion Probe (`Client`)**: Detects ankle-level step risers (`> 0.4` studs), movement snags (`MoveDirection > 0.5` with speed `< 1.2` studs/s), and non-collidable props with `CanQuery = true` blocking the camera.
3. **Control Ergonomics, Modal Priority & Prompt Parity Probe (`Client`)**: Audits `ContextActionService` priorities, gamepad `SelectedObject` focus, and keyboard prompt leaks when `PreferredInput` is Touch or Gamepad.
4. **Server Authority, Pacing & Highlight Budget Probe (`Server`)**: Inspects live phase/player attributes, verifies `Highlight` count `<= 31`, and flags collidable decorative micro-parts (`< 0.65` studs).
5. **Studio Script Inventory & Drift Probe (`Edit`)**: Summarizes all `LuaSourceContainer` paths, byte counts, and line counts to confirm zero drift between disk source and Studio `Edit` mode.

---

## Repository Layout

```text
roblox-playtest-fix/
├── .claude-plugin/
│   ├── plugin.json              # Claude Code plugin manifest
│   └── marketplace.json         # Claude Code marketplace catalog entry
├── gemini-extension.json        # Google Antigravity / Gemini extension manifest
├── skills/
│   └── roblox-playtest-fix/
│       ├── SKILL.md             # Canonical harness-agnostic skill workflow
│       ├── agents/
│       │   └── openai.yaml      # OpenAI / Codex agent interface metadata
│       └── references/
│           └── playtest-probes.md # 5 strict-typed Luau Studio MCP probes
├── tests/
│   └── validate_skill.py        # Deterministic frontmatter, manifest, link & Luau verifier
├── install.sh                   # Multi-host installer (--claude, --codex, --agy, --all)
├── AGENTS.md                    # Contributor & agent instructions
├── CLAUDE.md -> AGENTS.md       # Symlink
├── GEMINI.md -> AGENTS.md       # Symlink
├── CHANGELOG.md                 # Keep a Changelog release history
├── VERSION                      # SemVer version (1.0.0)
└── LICENSE                      # MIT License
```

## License

[MIT](LICENSE) © Shane Hamilton
