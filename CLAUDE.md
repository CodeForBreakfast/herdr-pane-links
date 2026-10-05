# herdr-pane-links

herdr-pane-links is a herdr plugin. It makes a link that names a herdr pane
focus that pane when the user Ctrl-clicks it. An agent running in a pane can
send its user that link instead of written directions to the pane.

## What herdr-pane-links owns

- The link format that names a pane.
- The plugin's handler, which focuses the named pane on a Ctrl-click.
- Building, testing and releasing the plugin, and its listing on the herdr
  marketplace through the `herdr-plugin` GitHub topic.

## What it does not own

- **herdr itself.** A bug or missing feature in herdr goes to the herdr
  project upstream. herdr issue #4874 is one: a Ctrl-click on a link with a
  custom scheme skips plugin link handlers, so the link is `https://`-shaped
  until herdr fixes it.
- **A user's deployment, configuration and data.** These live with that user,
  never in this repo.
