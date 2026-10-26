#!/usr/bin/env python3
"""Deterministic validator for the roblox-playtest-fix repository and skill payload."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "roblox-playtest-fix"
SKILL_MD = SKILL_DIR / "SKILL.md"
PROBES_MD = SKILL_DIR / "references" / "playtest-probes.md"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"


def check_versions() -> str:
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.match(r"^\d+\.\d+\.\d+$", version), f"Invalid SemVer in VERSION: {version}"

    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads(
        (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    gemini_ext = json.loads((REPO_ROOT / "gemini-extension.json").read_text(encoding="utf-8"))

    assert plugin["version"] == version, "plugin.json version mismatch"
    assert marketplace["plugins"][0]["version"] == version, "marketplace.json version mismatch"
    assert gemini_ext["version"] == version, "gemini-extension.json version mismatch"

    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{version}]" in changelog, f"CHANGELOG.md missing section for {version}"
    return version


def check_symlinks() -> None:
    for link_name in ("CLAUDE.md", "GEMINI.md"):
        p = REPO_ROOT / link_name
        assert p.is_symlink(), f"{link_name} must be a symlink to AGENTS.md"
        assert p.resolve() == (REPO_ROOT / "AGENTS.md").resolve(), (
            f"{link_name} does not resolve to AGENTS.md"
        )


def check_skill_files() -> list[str]:
    assert SKILL_MD.is_file(), "Missing skills/roblox-playtest-fix/SKILL.md"
    assert PROBES_MD.is_file(), "Missing skills/roblox-playtest-fix/references/playtest-probes.md"
    assert OPENAI_YAML.is_file(), "Missing skills/roblox-playtest-fix/agents/openai.yaml"

    skill_text = SKILL_MD.read_text(encoding="utf-8")
    assert skill_text.startswith("---\nname: roblox-playtest-fix\ndescription:"), (
        "Invalid YAML frontmatter in SKILL.md"
    )
    assert "references/playtest-probes.md" in skill_text, "SKILL.md must link to playtest-probes.md"

    yaml_text = OPENAI_YAML.read_text(encoding="utf-8")
    for required_key in ("display_name:", "short_description:", "default_prompt:"):
        assert required_key in yaml_text, f"openai.yaml missing {required_key}"

    probes_text = PROBES_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```lua\n(.*?)```", probes_text, flags=re.S)
    assert len(blocks) == 5, f"Expected 5 Lua probe blocks in playtest-probes.md, found {len(blocks)}"
    for idx, block in enumerate(blocks, 1):
        assert block.startswith("--!strict\n"), f"Probe {idx} must start with --!strict"
    return blocks


def check_luau_probes(blocks: list[str], defs: Path | None) -> bool:
    tools = {name: shutil.which(name) for name in ("stylua", "selene", "luau-lsp")}
    incomplete = []
    for name, path in tools.items():
        if path is None:
            incomplete.append(f"{name} not found in PATH")
    if defs is None or not defs.is_file():
        incomplete.append("Roblox definitions missing; set ROBLOX_LUAU_DEFINITIONS or --definitions")

    failed = False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for idx, code in enumerate(blocks, 1):
            raw = tmp_path / f"raw_{idx}.luau"
            raw.write_text(code, encoding="utf-8")
            wrapped = tmp_path / f"probe_{idx}.luau"
            wrapped.write_text(
                "--!strict\nlocal function runProbe()\n"
                + code.removeprefix("--!strict\n")
                + "\nend\nreturn runProbe\n",
                encoding="utf-8",
            )
            commands = {
                "stylua": ["--check", "--config-path", str(REPO_ROOT / "stylua.toml"), str(raw)],
                "selene": ["--config", str(REPO_ROOT / "selene.toml"), str(wrapped)],
                "luau-lsp": ["analyze", "--definitions", str(defs), str(wrapped)],
            }
            for name, args in commands.items():
                if tools[name] is None or (name == "luau-lsp" and (defs is None or not defs.is_file())):
                    continue
                try:
                    result = subprocess.run([tools[name], *args], cwd=REPO_ROOT, check=False)
                    if result.returncode != 0:
                        print(f"[fail] {name} probe {idx}: exit {result.returncode}")
                        failed = True
                except OSError as exc:
                    print(f"[fail] {name} probe {idx}: {exc}")
                    failed = True
    for reason in incomplete:
        print(f"[incomplete] {reason}")
    if not failed and not incomplete:
        print(f"[ok] Validated {len(blocks)} Luau probes with stylua, selene, and luau-lsp")
    return not failed and not incomplete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--definitions", type=Path,
        default=os.environ.get("ROBLOX_LUAU_DEFINITIONS"),
        help="path to Roblox Luau definitions (or set ROBLOX_LUAU_DEFINITIONS)",
    )
    args = parser.parse_args()
    defs = Path(args.definitions).expanduser().resolve() if args.definitions else None
    version = check_versions()
    check_symlinks()
    blocks = check_skill_files()
    if not check_luau_probes(blocks, defs):
        print("[fail] Luau validation did not pass")
        return 1
    print(f"[ok] roblox-playtest-fix v{version} passed all validation checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
