#!/bin/sh
set -eu

REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEST_SH=${TEST_SH:-sh}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
FAILED=0

check() {
  description=$1
  shift
  if "$@"; then
    printf 'ok    %s\n' "$description"
  else
    printf 'FAIL  %s\n' "$description"
    FAILED=1
  fi
}

installer() {
  home=$1
  shift
  HOME="$home" AGENTS_CORE_SOURCE="${CORE_SOURCE:-$REPO/AGENTS.md}" "$TEST_SH" "$REPO/install.sh" "$@" > "$home.log" 2>&1
}

new_home() {
  home="$WORK/$1"
  mkdir -p "$home"
  printf '%s' "$home"
}

count_of() { grep -c -F -- "$1" "$2" || true; }
is_link_to_shared() { [ -L "$1" ] && [ "$(readlink "$1")" = "$2/.agents/AGENTS.md" ]; }
same_text() { [ "$(cat "$1")" = "$(cat "$2")" ]; }
absent() { [ ! -e "$1" ] && [ ! -L "$1" ]; }

H=$(new_home fresh)
mkdir -p "$H/.claude" "$H/.codex"
installer "$H" install
check "fresh install writes the shared file" test -f "$H/.agents/AGENTS.md"
check "fresh install wraps the core in one block" test "$(count_of 'agents-core:begin' "$H/.agents/AGENTS.md")" = 1
check "fresh install links Claude Code" is_link_to_shared "$H/.claude/CLAUDE.md" "$H"
check "fresh install links Codex" is_link_to_shared "$H/.codex/AGENTS.md" "$H"
check "tools that are not installed get no file" absent "$H/.qwen"
cp "$H/.agents/AGENTS.md" "$WORK/first.md"
installer "$H" update
check "a second run changes nothing" same_text "$H/.agents/AGENTS.md" "$WORK/first.md"
check "a second run records each link once" test "$(wc -l < "$H/.agents/.agents-core-links" | tr -d ' ')" = 2
installer "$H" uninstall
check "uninstall removes the links it made" absent "$H/.claude/CLAUDE.md"
check "uninstall removes the shared file when nothing else is in it" absent "$H/.agents"

H=$(new_home opencode)
mkdir -p "$H/.config/opencode"
installer "$H" install
check "install links opencode" is_link_to_shared "$H/.config/opencode/AGENTS.md" "$H"

H=$(new_home more-tools)
mkdir -p "$H/.pi/agent" "$H/.vibe" "$H/.copilot" "$H/.config/crush" "$H/.config/zed" "$H/qwen-home"
QWEN_HOME="$H/qwen-home" installer "$H" install
check "install links Pi" is_link_to_shared "$H/.pi/agent/AGENTS.md" "$H"
check "install links Mistral Vibe" is_link_to_shared "$H/.vibe/AGENTS.md" "$H"
check "install links Copilot CLI" is_link_to_shared "$H/.copilot/copilot-instructions.md" "$H"
check "install links the shared config file Crush and Amp read" is_link_to_shared "$H/.config/AGENTS.md" "$H"
check "install links Zed" is_link_to_shared "$H/.config/zed/AGENTS.md" "$H"
check "install honours QWEN_HOME" is_link_to_shared "$H/qwen-home/AGENTS.md" "$H"

H=$(new_home no-crush)
mkdir -p "$H/.config/opencode"
installer "$H" install
check "the shared config file is linked only when Crush or Amp is installed" absent "$H/.config/AGENTS.md"

H=$(new_home personal)
mkdir -p "$H/.agents" "$H/.claude"
printf '## Mine\n\n- No comments.\n' > "$H/.agents/AGENTS.md"
cp "$H/.agents/AGENTS.md" "$WORK/mine.md"
installer "$H" install
check "an existing file is backed up" same_text "$H/.agents/AGENTS.md.before-agents-core" "$WORK/mine.md"
check "the personal text is kept above the core" test "$(head -n 3 "$H/.agents/AGENTS.md")" = "$(cat "$WORK/mine.md")"
check "the core comes last" test "$(tail -n 1 "$H/.agents/AGENTS.md")" = "<!-- agents-core:end -->"
installer "$H" update
check "updating keeps the personal text exactly once" test "$(count_of '## Mine' "$H/.agents/AGENTS.md")" = 1
CORE_HEADING=$(head -n 1 "$REPO/AGENTS.md")
check "the installed file holds the core heading" test "$(count_of "$CORE_HEADING" "$H/.agents/AGENTS.md")" = 1
printf 'New core text.\n' > "$WORK/core2.md"
CORE_SOURCE="$WORK/core2.md" installer "$H" update
check "updating replaces the core text" test "$(count_of 'New core text.' "$H/.agents/AGENTS.md")" = 1
check "updating removes the old core text" test "$(count_of "$CORE_HEADING" "$H/.agents/AGENTS.md")" = 0
{ printf '<!-- agents-core:begin -->\nOld core.\n<!-- agents-core:end -->\n\n'; cat "$WORK/mine.md"; } > "$H/.agents/AGENTS.md"
installer "$H" update
check "updating moves a core written above the personal text below it" test "$(head -n 3 "$H/.agents/AGENTS.md")" = "$(cat "$WORK/mine.md")"
installer "$H" uninstall
check "uninstall gives the personal file back unchanged" same_text "$H/.agents/AGENTS.md" "$WORK/mine.md"

H=$(new_home foreign)
mkdir -p "$H/.claude"
printf 'my own rules\n' > "$H/.claude/CLAUDE.md"
installer "$H" install
check "a tool's own instruction file is left alone" test "$(cat "$H/.claude/CLAUDE.md")" = "my own rules"
check "a file that was left alone is not recorded" test ! -s "$H/.agents/.agents-core-links"

H=$(new_home prelinked)
mkdir -p "$H/.agents" "$H/.claude"
ln -s "$H/.agents/AGENTS.md" "$H/.claude/CLAUDE.md"
installer "$H" install
installer "$H" uninstall
check "a link the user made before is not removed" test -L "$H/.claude/CLAUDE.md"

H=$(new_home dry)
mkdir -p "$H/.claude"
installer "$H" install --dry-run
check "a dry run creates nothing" absent "$H/.agents"
check "a dry run links nothing" absent "$H/.claude/CLAUDE.md"

H=$(new_home piped)
mkdir -p "$H/.codex"
(cd "$WORK" && HOME="$H" AGENTS_CORE_URL="file://$REPO/AGENTS.md" "$TEST_SH" -s -- install < "$REPO/install.sh" > "$H.log" 2>&1)
check "piped into sh, it fetches the core from the URL" test "$(count_of 'agents-core:begin' "$H/.agents/AGENTS.md")" = 1
check "piped into sh, it links the tools it finds" is_link_to_shared "$H/.codex/AGENTS.md" "$H"
(cd "$WORK" && HOME="$H" "$TEST_SH" -s -- uninstall < "$REPO/install.sh" > "$H.log" 2>&1)
check "piped uninstall leaves nothing behind" absent "$H/.agents"

exit "$FAILED"
