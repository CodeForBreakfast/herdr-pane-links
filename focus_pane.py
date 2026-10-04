"""Focus the herdr pane named by a clicked https://herdr.invalid/pane/<pane-id> link."""

import json
import os
import socket
import sys
import time
from urllib.parse import unquote, urlsplit

LINK_PREFIX = "/pane/"
NOTICE_PATIENCE_SECONDS = 5


def request(method, params):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.connect(os.environ["HERDR_SOCKET_PATH"])
        conn.sendall(json.dumps({"id": "pane-links", "method": method, "params": params}).encode() + b"\n")
        return json.loads(conn.makefile().readline())


def pane_id_from(url):
    path = urlsplit(url).path
    return unquote(path[len(LINK_PREFIX):]) if path.startswith(LINK_PREFIX) else ""


def main():
    url = os.environ.get("HERDR_PLUGIN_CLICKED_URL", "")
    pane_id = pane_id_from(url)
    if not pane_id:
        print(f"not a pane link: {url!r}", file=sys.stderr)
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
