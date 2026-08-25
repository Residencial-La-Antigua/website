---
name: run-website
description: Build, run, and drive the Residencial La Antigua Django website. Use when asked to start the site, run its tests, or take a screenshot of / click through its UI (e.g. the calendar).
---

Django + vanilla JS site. Start the dev server, then drive the rendered
pages via `.claude/skills/run-website/driver.mjs`. All paths below are
relative to the repo root.

## Setup

One-time, to install the driver's own dependencies:

```bash
cd .claude/skills/run-website
npm install
npx playwright install chromium   # downloads/caches the browser binary
```

## Run (agent path)

Use port **8001**, not 8000.

Start the dev server, capturing its PID (don't rely on "something
answers on the port" as your readiness/liveness signal — see Gotchas
for why), then pipe commands to the driver over stdin, one per line:

```bash
PORT=8001
if lsof -ti:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ABORT: port $PORT is already in use by something else." >&2
  exit 1
fi

uv run manage.py runserver 127.0.0.1:$PORT &
SERVER_PID=$!
for i in $(seq 1 20); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "ABORT: server process died before becoming ready" >&2; exit 1
  fi
  curl -sf http://127.0.0.1:$PORT/accounts/login/ >/dev/null && break
  sleep 0.5
done

cd .claude/skills/run-website
BASE_URL=http://127.0.0.1:$PORT node driver.mjs <<'EOF'
login carl.sagan smoketest-pass-123
nav /calendario/
wait-for #year-select
text .fc-toolbar-title
click .fc-next-button
wait-for text=Hoy
screenshot after-next
console
quit
EOF
```

Screenshots land in `.claude/skills/run-website/screenshots/<name>.png`
(or `<counter>.png` if no name is given).

There should be two seeded, known-password test accounts locally:

1. Regular User: `carl.sagan` / `smoketest-pass-123` (`is_staff=False`).
2. Admin User: `admin` / `123queso` (`is_staff=True`, `is_superuser=True`)

Driver commands:

| command                      | what it does                                                |
| ---------------------------- | ----------------------------------------------------------- |
| `nav <path-or-url>`          | goto `BASE_URL` + path, or an absolute URL                  |
| `login <user> <pass>`        | fills and submits the Django login form                     |
| `wait-for <selector>`        | waits for a selector (Playwright syntax — `text=Hoy` works) |
| `click <selector>`           |                                                             |
| `fill <selector> <value...>` |                                                             |
| `select <selector> <value>`  | for `<select>` elements, e.g. the calendar's year picker    |
| `press <key>`                |                                                             |
| `text <selector>`            | prints `textContent`                                        |
| `value <selector>`           | prints the input/select value                               |
| `eval <js>`                  | runs JS in the page, prints the JSON result                 |
| `screenshot [name]`          | saves to `screenshots/<name-or-counter>.png`                |
| `console`                    | prints collected `console.error`/`pageerror` lines          |
| `quit` / `exit`              | closes the browser                                          |

Stop the server when done — kill the captured PID, never "whatever's on the port":

```bash
kill "$SERVER_PID" 2>/dev/null
```

---

## Gotchas

- **`npx playwright ...` alone can't run a custom script.** `npx -p
playwright node script.js` looks like it should make `require("playwright")`
  resolve, but it doesn't set `NODE_PATH` for the subprocess — confirmed
  both with a plain `node -e` subprocess and with `npx -p playwright -c
'...'`, both fail with `Cannot find module 'playwright'`. The fix used
  here is the scoped local `npm install` in Setup, not a `npx`-only
  invocation.
- **Never manage the dev server by port — manage it by PID.** An
  earlier version of this skill started the server with
  `manage.py runserver 127.0.0.1:8000 &`, checked readiness by polling
  `curl` against the port, and stopped it with
  `lsof -ti:8000 -sTCP:LISTEN | xargs -r kill`. On a machine where 8000
  was already occupied, `runserver` silently failed to bind, the
  `curl` check happily passed against the _other_ thing already
  listening there, and the "cleanup" step killed that other process
  instead. Fixed by: using port 8001 instead of the contested 8000;
  capturing `$!` right after backgrounding and checking
  `kill -0 "$SERVER_PID"` during the readiness loop (so a dead process
  fails loudly instead of the loop quietly passing because someone
  else answered); aborting up front if the target port is already
  occupied instead of proceeding anyway; and killing only the captured
  PID at cleanup, never "whatever is on the port."
- **Driver commands must run strictly sequentially.** Node's `readline`
  fires `"line"` for every buffered line almost immediately when stdin
  is a heredoc, not one at a time as each async handler completes. An
  earlier version of `driver.mjs` awaited each command inside the `line`
  handler directly, which let `quit` close the browser while earlier
  commands (e.g. a `screenshot`) were still in flight, throwing "Target
  page, context or browser has been closed". Fixed by chaining every
  command onto one promise (`chain = chain.then(...)`) instead of
  awaiting per-handler.

## Troubleshooting

- **`Error: Cannot find module 'playwright'`**: you're running
  `driver.mjs` from somewhere other than `.claude/skills/run-website/`,
  or skipped `npm install` in Setup. `require`/`import` resolution is
  relative to the driver's own location.
- **Driver prints `ERR page.click: ... Timeout ... exceeded`**: the
  selector didn't match anything visible — usually means either the
  page didn't finish loading (`wait-for` something first) or you're not
  logged in (unauthenticated requests to `/calendario/eventos/` return
  `401` JSON, not a redirect, so the page can look blank rather than
  bouncing to `/accounts/login/`).
