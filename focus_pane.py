"""Focus the herdr pane named by a clicked pane link.

A link is https://herdr.invalid/pane/<pane-id>, or
https://herdr.invalid/<host>/<session>/pane/<pane-id> for one that names the
host and herdr session the pane is in.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK_PATH = re.compile(r"/(?:(?P<host>[^/]+)/(?P<session>[^/]+)/)?pane/(?P<pane_id>[^/]+)")
NOTICE_PATIENCE_SECONDS = 5


def request(method, params):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.connect(os.environ["HERDR_SOCKET_PATH"])
        conn.sendall(json.dumps({"id": "pane-links", "method": method, "params": params}).encode() + b"\n")
        return json.loads(conn.makefile().readline())


def parse_link(url):
    """Return the link's pane_id, host and session, with host and session None for a bare pane link."""
    match = LINK_PATH.fullmatch(urlsplit(url).path)
    if not match:
        return None
    return {key: unquote(value) if value else None for key, value in match.groupdict().items()}


def own_host():
    """The name the user gave this machine, in a one-line `host` file in the plugin's config dir."""
    try:
        return (Path(os.environ["HERDR_PLUGIN_CONFIG_DIR"]) / "host").read_text().strip() or None
    except FileNotFoundError:
        return None


def own_session():
    listing = subprocess.run(
        [os.environ.get("HERDR_BIN_PATH", "herdr"), "session", "list", "--json"],
        capture_output=True, text=True, check=True,
    )
    socket_path = os.environ["HERDR_SOCKET_PATH"]
    return next((s["name"] for s in json.loads(listing.stdout)["sessions"] if s["socket_path"] == socket_path), None)


def main():
    url = os.environ.get("HERDR_PLUGIN_CLICKED_URL", "")
    link = parse_link(url)
    if not link:
        print(f"not a pane link: {url!r}", file=sys.stderr)
        return 1
    pane_id = link["pane_id"]

    if link["host"] is not None:
        here = {"host": own_host(), "session": own_session()}
        elsewhere = {"host": link["host"], "session": link["session"]}
        if here != elsewhere:
            notice = show_notice(
                "Pane is in another herdr",
                f"Pane {pane_id} is in herdr session {elsewhere['session']} on {elsewhere['host']}. "
                f"This is session {here['session']} on {here['host'] or 'a host with no name set'}.",
            )
            print(json.dumps({"elsewhere": elsewhere, "notice": notice}), file=sys.stderr)
            return 1

    response = request("pane.focus", {"pane_id": pane_id})
    if "error" not in response:
        return 0

    notice = show_notice("No such herdr pane", f"Nothing to focus: pane {pane_id} does not exist. The link may be stale.")
    print(json.dumps({"error": response["error"], "notice": notice}), file=sys.stderr)
    return 1


def show_notice(title, body):
    """herdr refuses a notification sent within a second of another one, so retry until it is taken."""
    deadline = time.monotonic() + NOTICE_PATIENCE_SECONDS
    while True:
        result = request("notification.show", {"title": title, "body": body}).get("result", {})
        if result.get("reason") != "rate_limited" or time.monotonic() > deadline:
            return result
        time.sleep(0.5)


if __name__ == "__main__":
    sys.exit(main())
