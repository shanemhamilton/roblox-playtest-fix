#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="roblox-playtest-fix"
REPO_URL="https://github.com/shanemhamilton/roblox-playtest-fix.git"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Install the ${SKILL_NAME} skill across Claude Code, Codex, OpenClaw, and Google Antigravity.

Options:
  --claude      Install to Claude Code (\${CLAUDE_SKILLS_DIR:-~/.claude/skills})
  --codex       Install to Codex & Agent Skills (\${CODEX_SKILLS_DIR:-~/.agents/skills} and ~/.codex/skills)
  --agy         Install to Google Antigravity (\${AGY_SKILLS_DIR:-~/.gemini/antigravity-cli/skills})
  --all         Install to all supported skill roots (default if no host flag is given)
  --symlink     Symlink to the local repository checkout instead of copying files
  -h, --help    Show this help message
EOF
}

DO_CLAUDE=0
DO_CODEX=0
DO_AGY=0
USE_SYMLINK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude) DO_CLAUDE=1; shift ;;
    --codex) DO_CODEX=1; shift ;;
    --agy) DO_AGY=1; shift ;;
    --all) DO_CLAUDE=1; DO_CODEX=1; DO_AGY=1; shift ;;
    --symlink) USE_SYMLINK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ "$DO_CLAUDE" -eq 0 && "$DO_CODEX" -eq 0 && "$DO_AGY" -eq 0 ]]; then
  DO_CLAUDE=1
  DO_CODEX=1
  DO_AGY=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_CLONE=""
cleanup() {
  if [[ -n "$TEMP_CLONE" && -d "$TEMP_CLONE" ]]; then
    rm -rf "$TEMP_CLONE"
  fi
}
trap cleanup EXIT

if [[ -f "${SCRIPT_DIR}/skills/${SKILL_NAME}/SKILL.md" ]]; then
  SOURCE_SKILL_DIR="${SCRIPT_DIR}/skills/${SKILL_NAME}"
else
  if [[ "$USE_SYMLINK" -eq 1 ]]; then
    echo "Error: --symlink requires running install.sh from a local clone." >&2
    exit 1
  fi
  TEMP_CLONE="$(mktemp -d "${TMPDIR:-/tmp}/${SKILL_NAME}.XXXXXX")"
  git clone --depth 1 "$REPO_URL" "$TEMP_CLONE" >/dev/null 2>&1
  SOURCE_SKILL_DIR="${TEMP_CLONE}/skills/${SKILL_NAME}"
fi

install_target() {
  local dest_root="$1"
  local dest_path="${dest_root}/${SKILL_NAME}"
  mkdir -p "$dest_root"
  if [[ "$USE_SYMLINK" -eq 1 ]]; then
    rm -rf "$dest_path"
    ln -sfn "$SOURCE_SKILL_DIR" "$dest_path"
    echo "[ok] Symlinked ${dest_path} -> ${SOURCE_SKILL_DIR}"
  else
    local stage_path="${dest_root}/.${SKILL_NAME}.stage.$$"
    rm -rf "$stage_path"
    cp -R "$SOURCE_SKILL_DIR" "$stage_path"
    rm -rf "$dest_path"
    mv "$stage_path" "$dest_path"
    echo "[ok] Installed ${dest_path}"
  fi
}

if [[ "$DO_CLAUDE" -eq 1 ]]; then
  install_target "${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
fi

if [[ "$DO_CODEX" -eq 1 ]]; then
  install_target "${CODEX_SKILLS_DIR:-$HOME/.agents/skills}"
  install_target "${CODEX_LEGACY_SKILLS_DIR:-$HOME/.codex/skills}"
fi

if [[ "$DO_AGY" -eq 1 ]]; then
  if [[ -d "$HOME/.gemini/antigravity-cli" || -n "${AGY_SKILLS_DIR:-}" ]]; then
    install_target "${AGY_SKILLS_DIR:-$HOME/.gemini/antigravity-cli/skills}"
  fi
  if command -v sync-skills >/dev/null 2>&1; then
    sync-skills --sync >/dev/null 2>&1 || true
    echo "[ok] Synchronized Antigravity skills via sync-skills --sync"
  fi
fi
