# HLG Framework

**H**arness / **L**oop / **G**raph Engineering — a local Windows desktop app
(PySide6) plus a live browser mirror that watches Python projects and
automatically runs AI-assisted verification, an autonomous fix loop, and a
concurrent multi-agent review. It lives in the system tray and re-analyzes
just the files you change, not the whole project, on every save.

Every pipeline can use **local Ollama** (fully offline), **Ollama's own
cloud models** (`ollama.com`, same API, one extra key), or a cloud provider
(Google Gemini, OpenAI, Anthropic, HuggingFace) — pick a Provider + Model
right on each tab, or set one **Auto Run** toggle and let it run itself.

## Screenshots

> _Add a few PNGs to `docs/screenshots/` (e.g. `dashboard.png`,
> `harness-tab.png`, `graph-dag.png`, `web-mirror.png`) and they'll render
> here:_
>
> `![Dashboard](docs/screenshots/dashboard.png)`
> `![Graph Engineering DAG](docs/screenshots/graph-dag.png)`
> `![Live web mirror](docs/screenshots/web-mirror.png)`

## The three engines, chained automatically

- **Harness Engineering** — an 18-step check (independent steps run
  concurrently): secret/API-key/password/private-key scanning, dependency
  and static analysis, a security scan, build verification, unit/
  integration tests, an AI code review, RAG knowledge retrieval, an
  architecture check, and a generated report. Runs on every save.
- **Loop Engineering** — on failure, asks your configured model for a fix
  (streamed live, token by token, for Ollama). With **Auto Run off**, you
  review each proposed file individually — Accept some, Reject others, in
  the same round — before anything is written (backed up first, and rolled
  back automatically if it didn't actually help). With **Auto Run on**,
  fixes apply immediately, no prompts. Missing project scaffolding
  (`tests/`, `requirements.txt`, `README.md`) is generated deterministically
  — no model call needed for that part.
- **Graph Engineering** — the same checks as a multi-agent DAG, executed
  with real concurrency via a router/orchestrator. Runs automatically once
  Harness (and Loop, if it ran) passes.

With **Auto Run on**, a failed Harness check auto-triggers Loop, Loop's fix
is applied without asking, Harness is re-checked fresh, and the whole round
repeats — up to a configurable retry limit — until it actually reaches a
clean, passing state, instead of leaving a stale "Failed" status as the last
thing recorded. With **Auto Run off**, every write asks first, file by file.

Once the full chain passes for a project, a clean, tested copy is
automatically exported to your Downloads folder — see the **Copy Clean
Project** tab.

## AI Prompt Timeline

Every single model call the app makes — Harness's AI code review, Loop's
fix generation, Graph's agents, the memory gate — passes through one shared
facade, which means every one of them is observable. The **live web
mirror** (below) shows them in a collapsible right-hand drawer: agent name,
provider/model, live "running" status, elapsed time, and the actual prompt
and result text, expandable per entry. Nothing is hidden — if you want to
know exactly what the app just asked a model to do and what it got back,
it's there in real time.

## Live web mirror

On startup, the app opens a **live, read-only mirror of itself in your
browser** (`http://127.0.0.1:8765` by default) — the same Harness/Loop/Graph
events, animated in real time, plus the AI Prompt Timeline above, so you can
watch the whole system work without the desktop window in focus. Disable it
or change the port in Settings; reopen it any time from the **Dashboard**
tab's "Open in Browser" button.

See [`docs/HARNESS_LOOP_GRAPH_DEFINITIONS.md`](docs/HARNESS_LOOP_GRAPH_DEFINITIONS.md)
for exactly which parts of this naming come from Anthropic's harness-design
article and which are this project's own design — that distinction is kept
explicit rather than implied.

## Also included

A live Dashboard (CPU/memory, queue/job counts, security and quality
scores, overall health); an Issue Sidebar that classifies any failed step
and can jump straight to the file:line in VS Code; a local RAG knowledge
base fed by files, folders, websites, or git repos; a **Memory** tab
covering semantic (RAG + memory-gate lessons), episodic (run history), and
procedural (installed plugin steps) memory; an **Eval** tab splitting every
check into deterministic (pytest/ruff/pip-audit) vs. LLM-as-judge; JSON/
HTML/PDF reports with run history; desktop notifications; a plugin
extension point; and an optional Windows autostart toggle.

## Quick start

```
run.bat
```

See [`docs/INSTALL.md`](docs/INSTALL.md) for prerequisites and first-run
steps, [`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md) to verify Harness,
Loop, and Graph yourself against a small example project with two
intentional issues, and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for
how the code is organized and how to extend it.

## Current scope

This build's first pass gives **Python projects** full, real integration
(pytest, ruff, pip-audit, compileall) end-to-end across all three panels.
Other language ecosystems have a documented extension seam
(`docs/ARCHITECTURE.md` → "Extending the app") but no adapter yet.

## Tests

```
pytest tests/
```

## Developer

Ahsan Saeed
