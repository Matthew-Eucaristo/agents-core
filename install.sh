#!/bin/sh
set -eu

SOURCE_URL="${AGENTS_CORE_URL:-https://raw.githubusercontent.com/Matthew-Eucaristo/agents-core/main/AGENTS.md}"
SHARED_DIR="$HOME/.agents"
SHARED_FILE="$SHARED_DIR/AGENTS.md"
MANIFEST="$SHARED_DIR/.agents-core-links"
BEGIN="<!-- agents-core:begin -->"
END="<!-- agents-core:end -->"

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

link_targets() {
  cat <<EOF
$HOME/.claude/CLAUDE.md
${CODEX_HOME:-$HOME/.codex}/AGENTS.md
$HOME/.gemini/AGENTS.md
$HOME/.qwen/AGENTS.md
${GROK_HOME:-$HOME/.grok}/AGENTS.md
$CONFIG_HOME/kilo/AGENTS.md
$CONFIG_HOME/zed/AGENTS.md
EOF
}

COMMAND="install"
DRY_RUN=0
for argument in "$@"; do
  case "$argument" in
    install|update) COMMAND="install" ;;
    uninstall|status) COMMAND="$argument" ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "usage: install.sh [install|update|uninstall|status] [--dry-run]" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }

run() {
  if [ "$DRY_RUN" -eq 1 ]; then say "would run: $*"; else "$@"; fi
}

points_at_shared() {
  [ -L "$1" ] && [ "$(readlink "$1")" = "$SHARED_FILE" ]
}

fetch_core() {
  script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || true)
  if [ -n "${AGENTS_CORE_SOURCE:-}" ]; then
    cat "$AGENTS_CORE_SOURCE"
  elif [ -n "$script_dir" ] && [ -f "$script_dir/AGENTS.md" ] && [ -f "$script_dir/install.sh" ]; then
    cat "$script_dir/AGENTS.md"
  else
    curl -fsSL "$SOURCE_URL"
  fi
}

without_block() {
  awk -v begin="$BEGIN" -v end="$END" '
    $0 == begin { skipping = 1; next }
    $0 == end { skipping = 0; next }
    !skipping { lines[++count] = $0 }
    END {
      first = 1
      while (first <= count && lines[first] ~ /^[[:space:]]*$/) first++
      last = count
      while (last >= first && lines[last] ~ /^[[:space:]]*$/) last--
      for (i = first; i <= last; i++) print lines[i]
    }
  ' "$1"
}

write_shared() {
  core_file=$1
  rest_file=$2
  target=$(mktemp)
  {
    say "$BEGIN"
    cat "$core_file"
    say "$END"
    if [ -s "$rest_file" ]; then
      say ""
      cat "$rest_file"
    fi
  } > "$target"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "would write: $SHARED_FILE ($(wc -l < "$target" | tr -d ' ') lines)"
    rm -f "$target"
  else
    mkdir -p "$SHARED_DIR"
    cat "$target" > "$SHARED_FILE"
    rm -f "$target"
  fi
}

install_core() {
  core_file=$(mktemp)
  rest_file=$(mktemp)
  fetch_core > "$core_file"
  if [ ! -s "$core_file" ]; then
    say "could not read the core rules; nothing changed" >&2
    rm -f "$core_file" "$rest_file"
    exit 1
  fi
  if [ -f "$SHARED_FILE" ]; then
    if grep -qxF "$BEGIN" "$SHARED_FILE"; then
      without_block "$SHARED_FILE" > "$rest_file"
      say "updating the core rules in $SHARED_FILE; your own text below them is kept"
    else
      backup="$SHARED_FILE.before-agents-core"
      if [ ! -e "$backup" ]; then run cp "$SHARED_FILE" "$backup"; fi
      cat "$SHARED_FILE" > "$rest_file"
      say "adding the core rules above your existing $SHARED_FILE (copy saved as $backup)"
    fi
  else
    say "creating $SHARED_FILE"
  fi
  write_shared "$core_file" "$rest_file"
  rm -f "$core_file" "$rest_file"
}

link_tools() {
  link_targets | while IFS= read -r target; do
    [ -d "$(dirname -- "$target")" ] || continue
    if points_at_shared "$target"; then
      say "ok: $target already points at the shared file"
    elif [ -e "$target" ] || [ -L "$target" ]; then
      say "kept: $target is your own file; merge it by hand if you want this tool to use the shared file"
    else
      run ln -s "$SHARED_FILE" "$target"
      if [ "$DRY_RUN" -eq 0 ]; then say "$target" >> "$MANIFEST"; fi
      say "linked: $target"
    fi
  done
  manual_steps
}

manual_steps() {
  if [ -d "$HOME/.gemini" ]; then say "Gemini CLI: add \"context\": {\"fileName\": [\"GEMINI.md\", \"AGENTS.md\"]} to ~/.gemini/settings.json"; fi
  if [ -d "$CONFIG_HOME/amp" ]; then say "Amp: put the single line @~/.agents/AGENTS.md in $CONFIG_HOME/amp/AGENTS.md"; fi
  if [ -d "$HOME/.kiro" ]; then say "Kiro: copy $SHARED_FILE to ~/.kiro/steering/AGENTS.md (it ignores links)"; fi
  if [ -d "$HOME/.cursor" ]; then say "Cursor: paste the rules into Settings > Rules > User Rules"; fi
  if [ -f "$HOME/.aider.conf.yml" ]; then say "Aider: add 'read: ~/.agents/AGENTS.md' to ~/.aider.conf.yml"; fi
}

uninstall_all() {
  if [ -f "$MANIFEST" ]; then
    while IFS= read -r target; do
      if points_at_shared "$target"; then
        run rm "$target"
        say "unlinked: $target"
      fi
    done < "$MANIFEST"
    run rm "$MANIFEST"
  fi
  if [ -f "$SHARED_FILE" ] && grep -qxF "$BEGIN" "$SHARED_FILE"; then
    rest_file=$(mktemp)
    without_block "$SHARED_FILE" > "$rest_file"
    if [ -s "$rest_file" ]; then
      if [ "$DRY_RUN" -eq 1 ]; then
        say "would remove the core rules from $SHARED_FILE and keep your own text"
      else
        cat "$rest_file" > "$SHARED_FILE"
        say "removed the core rules from $SHARED_FILE; your own text is kept"
      fi
    else
      run rm "$SHARED_FILE"
      say "removed $SHARED_FILE"
    fi
    rm -f "$rest_file"
  else
    say "no core rules found in $SHARED_FILE"
  fi
  if [ "$DRY_RUN" -eq 0 ] && [ -d "$SHARED_DIR" ]; then rmdir "$SHARED_DIR" 2>/dev/null || true; fi
}

show_status() {
  if [ -f "$SHARED_FILE" ] && grep -qxF "$BEGIN" "$SHARED_FILE"; then
    say "core rules: installed in $SHARED_FILE"
  else
    say "core rules: not installed"
  fi
  link_targets | while IFS= read -r target; do
    if points_at_shared "$target"; then
      say "linked: $target"
    elif [ -e "$target" ]; then
      say "own file: $target"
    fi
  done
}

case "$COMMAND" in
  install) install_core; link_tools ;;
  uninstall) uninstall_all ;;
  status) show_status ;;
esac
