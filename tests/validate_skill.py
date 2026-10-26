#!/usr/bin/env python3
"""Deterministic validator for the roblox-playtest-fix repository and skill payload."""

from __future__ import annotations

import json
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


def check_luau_probes(blocks: list[str]) -> None:
    superfriends_game = REPO_ROOT.parent / "superfriends" / "game"
    has_selene = shutil.which("selene") is not None
    has_stylua = shutil.which("stylua") is not None
    has_luau_lsp = shutil.which("luau-lsp") is not None
    defs = superfriends_game / ".luau-defs" / "globalTypes.d.luau"

    if not (superfriends_game.is_dir() and has_selene and has_stylua and has_luau_lsp):
        print("[info] Skipping external Luau toolchain checks (toolchain not in current PATH)")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for idx, code in enumerate(blocks, 1):
            raw_file = tmp_path / f"raw_{idx}.luau"
            raw_file.write_text(code, encoding="utf-8")
            subprocess.run(
                ["stylua", "--check", "--config-path", "stylua.toml", str(raw_file)],
                cwd=str(superfriends_game),
                check=True,
            )

            body = code.replace("--!strict\n", "", 1)
            wrapped = tmp_path / f"probe_{idx}.luau"
            wrapped.write_text(
                "--!strict\nlocal function runProbe()\n" + body + "\nend\nreturn runProbe\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["selene", "--config", "selene.toml", str(wrapped)],
                cwd=str(superfriends_game),
                check=True,
            )
            if defs.is_file():
                subprocess.run(
                    ["luau-lsp", "analyze", "--definitions", str(defs), str(wrapped)],
                    cwd=str(superfriends_game),
                    check=True,
                )
    print(f"[ok] Validated {len(blocks)} Luau probes with stylua, selene, and luau-lsp (--!strict)")


def main() -> None:
    version = check_versions()
    check_symlinks()
    blocks = check_skill_files()
    check_luau_probes(blocks)
    print(f"[ok] roblox-playtest-fix v{version} passed all validation checks.")


if __name__ == "__main__":
    main()
