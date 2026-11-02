# herdr-pane-links

A [herdr](https://herdr.dev) plugin that lets you Ctrl-click a link to focus a
herdr pane. An agent running in a pane can send its user a link to that pane
instead of written directions to it.

## The link

```text
https://herdr.invalid/pane/<pane-id>
```

`<pane-id>` is the pane's herdr id, the value of `HERDR_PANE_ID` inside the
pane, such as `wT9:p1`. A process in a pane builds its own link like this:

```bash
echo "https://herdr.invalid/pane/$HERDR_PANE_ID"
```

Print the link as plain text, with whitespace or the end of the line after it.
herdr ends a link at the first whitespace and drops trailing punctuation such
as a full stop.

Ctrl-clicking the link anywhere in herdr focuses the named pane, switching
workspace and tab if needed. If the pane no longer exists, focus stays where
it was and herdr shows a "No such herdr pane" notification. herdr shows that
notification only when `ui.toast.delivery = "herdr"` is set in its config,
which is not the default. It queues behind any notifications already waiting,
so it can take a few seconds to appear.

A plain click, and a Ctrl-click on any other link, behave exactly as they do
without the plugin.

## A link that names its host and session

A pane id means something only inside the herdr server that gave it. Each
herdr session runs its own server, and the same id can name different panes in
two sessions or on two machines. A link that may be clicked somewhere else,
such as one sent to a phone, can name the host and the herdr session as well:

```text
https://herdr.invalid/<host>/<session>/pane/<pane-id>
```

`<session>` is the herdr session's name, as `herdr session list` shows it, such
as `default`. `<host>` is a name you give the machine. Set it in a file named
`host` in the plugin's config directory:

```bash
echo thinkpad >"$(herdr plugin config-dir codeforbreakfast.pane-links)/host"
```

A Ctrl-click on such a link focuses the pane when the host and session are the
ones the click happened in. Otherwise focus stays where it was, and herdr shows
a "Pane is in another herdr" notification that names the link's host and
session. Without a `host` file, every link that names a host shows that
notification.

The `.invalid` host never resolves, so the link fails harmlessly if it is
clicked outside herdr. The link is `https://` rather than a custom scheme
because of herdr issue #4874: herdr skips plugin link handlers for a Ctrl-click
on a custom-scheme link.

## How long a link stays good

- **A pane id survives a herdr server restart.** herdr saves and restores it.
- **A pane id is never reused inside its workspace.** Once the pane closes,
  its link reports that the pane does not exist.
- **Moving a pane to another workspace gives it a new id.** herdr keeps
  answering to the old id while the moved pane's process lives, but send a
  fresh link after a move.
- **A workspace id can come back after a restart.** If the newest workspace is
  closed and the server then restarts, the next new workspace reuses its id.
  An old link into the closed workspace can then name a pane in the new one.

## Install

The plugin needs herdr 0.9.3 or later and `python3`, on Linux or macOS.

```bash
herdr plugin install CodeForBreakfast/herdr-pane-links
```

To run it from a local checkout instead:

```bash
herdr plugin link /path/to/herdr-pane-links
```

The plain link needs no configuration. A link that names its host needs
the `host` file described above. Check that herdr has picked the plugin up:

```bash
herdr plugin list
```

## Testing

`tests/e2e.sh` drives the link handler through a throwaway herdr server with
its own config and state directories, so the herdr you are working in is left
alone. It needs `jq`, and `script` from util-linux to attach a herdr client.

```bash
tests/e2e.sh
```
