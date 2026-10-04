#!/usr/bin/env bash
# Drives the link handler through a throwaway herdr server with its own config
# and state, so the herdr you are sitting in is never touched. A Ctrl-click
# reaches the server as a pane.link.activate request; this sends that request.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
for var in $(compgen -e | grep '^HERDR_' || true); do unset "$var"; done
SCRATCH=$(mktemp -d)
export XDG_CONFIG_HOME=$SCRATCH/config XDG_STATE_HOME=$SCRATCH/state

SOCKET=$(herdr session list --json | jq -r '.sessions[] | select(.default) | .socket_path')
case $SOCKET in "$SCRATCH"/*) ;; *) echo "refusing: socket $SOCKET is not the throwaway server's" >&2; exit 1 ;; esac

herdr server >"$SCRATCH/server.log" 2>&1 &
SERVER_PID=$!
teardown() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  rm -rf "$SCRATCH"
}
trap teardown EXIT

for _ in $(seq 50); do [ -S "$SOCKET" ] && break; sleep 0.1; done
export HERDR_SOCKET_PATH=$SOCKET

request() {
  (cd "$ROOT" && python3 -B -c 'import json, sys, focus_pane
print(json.dumps(focus_pane.request(sys.argv[1], json.loads(sys.argv[2]))))' "$@")
}
focused_pane() { herdr api snapshot | jq -r '.result.snapshot.focused_pane_id'; }
fail() { echo "FAIL: $*" >&2; exit 1; }

herdr plugin link "$ROOT" >/dev/null

herdr workspace create --cwd "$SCRATCH" --label clicker --focus >/dev/null
herdr workspace create --cwd "$SCRATCH" --label target --no-focus >/dev/null
CLICKER=$(herdr pane list | jq -r '.result.panes[] | select(.workspace_id == "w1") | .pane_id' | head -1)
TARGET_TAB=$(herdr tab create --workspace w2 --no-focus | jq -r '.result.root_pane.pane_id')

# Prints a link on its own row of the clicker pane, then Ctrl-clicks it.
click_link() {
  local url=$1 marker=$RANDOM$RANDOM
  herdr pane run "$CLICKER" "clear; printf '%s\n' '$marker $url'" >/dev/null
  local row=""
  for _ in $(seq 100); do
    row=$(herdr pane read "$CLICKER" --source visible --format text --raw |
      awk -v line="$marker $url" '{ sub(/[[:space:]]+$/, "") } $0 == line { print NR - 1; exit }')
    [ -n "$row" ] && break
    sleep 0.1
  done
  [ -n "$row" ] || fail "link for $url never reached the screen"
  request pane.link.activate "{\"pane_id\":\"$CLICKER\",\"viewport_row\":$row,\"col\":$((${#marker} + 10))}"
}

wait_for_plugin_exit() {
  for _ in $(seq 50); do
    herdr plugin log list --plugin codeforbreakfast.pane-links --limit 1 |
      jq -e '.result.logs[0] | select(.finished_unix_ms != null)' && return
    sleep 0.1
  done
  fail "plugin action never finished"
}

echo "a link to a pane in another workspace focuses it"
click_link "https://herdr.invalid/pane/$TARGET_TAB" | jq -e '.result.handled == true' >/dev/null ||
  fail "herdr did not route the link to the plugin"
for _ in $(seq 50); do [ "$(focused_pane)" = "$TARGET_TAB" ] && break; sleep 0.1; done
[ "$(focused_pane)" = "$TARGET_TAB" ] || fail "focus is on $(focused_pane), not $TARGET_TAB"

herdr workspace focus w1 >/dev/null
herdr pane list | jq -e --arg p "$CLICKER" '.result.panes[] | select(.pane_id == $p) | .focused' >/dev/null

echo "a link to a missing pane focuses nothing and says so"
click_link "https://herdr.invalid/pane/w9:p9" | jq -e '.result.handled == true' >/dev/null ||
  fail "herdr did not route the stale link to the plugin"
wait_for_plugin_exit | jq -e '.stderr | contains("pane_not_found")' >/dev/null ||
  fail "plugin did not report the missing pane"
[ "$(focused_pane)" = "$CLICKER" ] || fail "focus moved to $(focused_pane)"

echo "a link the plugin does not own is left to herdr"
click_link "https://example.com/pane/$TARGET_TAB" | jq -e '.result.handled == false' >/dev/null ||
  fail "the plugin claimed a link that is not its own"

echo "PASS"
