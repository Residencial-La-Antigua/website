# CLAUDE.md

## Documentation structure

| File             | Audience          | Contents                                                                                                                           |
| ---------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`      | Anyone            | Mission, feature-module overview, current progress, and a pointer to where feature work is tracked.                                |
| `DEVELOPMENT.md` | Contributors      | Local setup (Docker/`uv`), migrations workflow, creating a superuser, code formatting (Ruff/Prettier), production-readiness TODOs. |
| `DEPLOYMENT.md`  | Deployers         | Env vars, dev-vs-prod DB, Gunicorn concurrency, deployment flow, deploying on Render                                               |
| `Infra-doc.md`   | Infra maintainers | Step-by-step runbook to (re)build the Azure VM from scratch                                                                        |

When deciding where to add or update documentation, use the audience column
to pick the right file.

## Naming convention

Code (models, field names, variables, etc.) is in **English**.
`verbose_name`/`verbose_name_plural` on models, and admin-facing labels, are
in **Spanish**. URL paths (`calendario/urls.py`) are also in Spanish, since
they're user-facing.

## Verify UI changes by actually driving the browser

The `run-website` skill (`.claude/skills/run-website/`) wraps a Playwright
driver for actually clicking through rendered pages. For frontend changes,
drive the real page via the `run-website` skill and look at the resulting
screenshot.

When testing, create disposable test fixtures for the interaction and clean
them up afterward. Never modify or delete the user's actual data (their real
events, confirmations, `is_active`/`is_staff` flags, etc.) as a side effect of
verification.

- **Use port 8001, never 8000** — the user's own Docker dev stack runs on
  port 8000 on this machine."
- **Manage the server by PID, never by port.** Capture `$!` right after
  backgrounding `manage.py runserver`, and kill only that PID at cleanup.
- Never leave the dev server running at the end of a task.

## Workflow

Work is broken into small, single-purpose commits with a consistent informal taxonomy. Prefixes like Feature:, Bugfix:, Style:, DB:, Doc: are used consistently to say what kind of change a commit is, even without a formal conventional-commits setup.

Epics are decomposed into numbered user stories, not necessarily implemented in numeric order - stories are sequenced by actual dependency order during planning, not by their original numbering in the epic doc. Related fixes and small polish commits get their own dedicated commits right next to the story that needed them, rather than being folded in. Separate documentation commits follow the completion of an epic.

All the granular, story-by-story work stays on the feature branch and only collapses to one commit at merge time. The main branch reads as a changelog of features/fixes, not a play-by-play.

## Git hygiene

- Before any destructive git operation, check `git status` first.
- Before force-pushing, verify with `git diff origin/<branch> <branch>
--stat` and `git merge-base` — use `--force-with-lease`, never a raw
  `--force`.
