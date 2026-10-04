"""Focus the herdr pane named by a clicked https://herdr.invalid/pane/<pane-id> link."""

import json
import os
import socket
import sys
from urllib.parse import unquote, urlsplit

LINK_PREFIX = "/pane/"


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

    request("notification.show", {
        "title": "No such herdr pane",
        "body": f"Nothing to focus: pane {pane_id} does not exist. The link may be stale.",
    })
    print(json.dumps(response["error"]), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
