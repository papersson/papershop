# screenshot-pane

A Claude Code mod that shows every screenshot Claude takes in a pane beside the transcript. You see what Claude sees while it checks its own work. You can flip to the previous version of the same page, and point Claude at a shot with one key.

Tested with Claude Code 2.1.287 in Ghostty on macOS.

## What it picks up

- `agent-browser screenshot`, with or without a path, after any `cd` in the same command.
- `screencapture` with an output path.
- Any image file Claude reads with the Read tool.

The pane remembers the page from the last `agent-browser open` and shows it in the header. Each shot is copied into `~/.cache/screenshot-pane/<session>/`, so a later screenshot to the same path can't change an older entry. Copies older than a week are removed when a session starts.

## Using it

The pane opens by itself on the first screenshot. If you close it, it stays closed and new shots show a toast instead. `/screenshots` opens it again and `/screenshots clear` empties the list.

Press ctrl+x then tab to give the pane the keyboard, then:

| Key | Does |
| --- | --- |
| `h` / `l` | previous / next screenshot |
| `b` | flip to the previous shot of the same page, and back |
| `c` | put `[screenshot #N of page: path]` into your prompt, so your comment goes to Claude anchored to that shot |
| `o` | open the shot in your image viewer |

## Settings

Set these in `/plugin` → Installed → screenshot-pane, or under `pluginConfigs` in `settings.json`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `autoOpen` | `true` | Open the pane on a new screenshot. Off: a toast tells you instead. |
| `history` | `50` | Screenshots kept per session. |
| `cellRatio` | `2.4` | How many times taller a terminal cell is than it is wide. Raise it if pictures look squashed, lower it if they look stretched. |

## Where it draws

Pictures need a terminal with the kitty graphics protocol, such as Ghostty, kitty or WezTerm, and not inside tmux. Elsewhere, and in the Desktop app, the pane lists the shots and `o` opens them. Only PNG is drawn.

Screenshots that browser MCP tools return inside their results, rather than as files, are not picked up yet.

## What it can do

A mod runs with your permissions, so here is what `claude plugin validate` reports for this one:

```
hooks: session.start, command.run{command=screenshots}, ui.close, tool.call{tool=Bash},
       tool.call{tool=Read}, ui.render{component=Pane, requestId=screenshots}
calls: $.clock.now, $.command.register, $.env.get, $.fs.read, $.fs.stat, $.process.run,
       $.prompt.fill, $.session.cwd, $.session.id, $.state.get, $.state.set, $.ui.open,
       $.ui.panes, $.ui.resolve, $.ui.toast
env reads: HOME
```

It never changes a tool call. It watches Bash and Read results and reads image files. It runs only `mkdir`, `cp`, `find` on its own cache folder, and `open` or `xdg-open`.

## Develop

```
claude plugin validate ./screenshot-pane
claude plugin test ./screenshot-pane
claude --plugin-dir ./screenshot-pane
```
