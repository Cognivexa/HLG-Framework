# Architecture

## Layers

```
app/
  config/      settings persistence (JSON under %LOCALAPPDATA%\HLGFramework), constants
  core/        multi-provider LLM layer, file watcher, project context, event bus, logging,
               background worker pool, pipeline controller (incl. auto-chain), dashboard
               metrics, autostart
    llm/       LLMProvider implementations: ollama_local, ollama_remote, gemini, openai,
               anthropic, huggingface — registry.py + llm_client.py is the facade every
               pipeline calls through
  security/    secret_scanner.py (offline regex+entropy), dependency_scanner.py (pip-audit)
  analysis/    static_analysis.py (ruff), build_runner.py (compileall), test_runner.py (pytest)
  rag/         embeddings.py (chunking), vector_store.py (Chroma), ingestion.py (loaders)
  pipelines/
    base.py        Step / StepResult / PipelineContext / PipelineRunner shared by all three panels
    steps/          ONE real implementation per capability, reused by Harness and Graph alike
    harness/        the 21-step pipeline — independent steps run concurrently (see below)
    loop/           the iterative retry/fix loop + file backup/rollback
    graph/          the 16-agent DAG: agents.py (registry), orchestrator.py (router),
                     graph_executor.py (concurrent execution)
  export/      clean_copy.py — exports a project to Downloads once the full chain passes
  reports/     report_generator.py + json/html/pdf writers + run history index
  notifications/ tray toast notifications driven by the same event bus
  plugins/     PluginStep extension point + loader (see examples/plugins/)
  web/         server.py (WebMirrorServer: FastAPI + WebSocket) + static/index.html —
               the read-only browser mirror of the live event bus
  ui/          PySide6 main window, tray icon, one widget per tab, theme, issue sidebar
```

## The event bus (`app/core/events.py`)

A single `EventBus` (Qt `QObject` with signals) is the only channel between
background threads and the UI:

- `StepEvent` — one pipeline step's status changed (pending/running/success/failed/skipped),
  carrying `data` (e.g. `{"locations": [...]}`) for the Issue Sidebar's jump-to-line
- `PipelineEvent` — a whole run started/completed/failed/**blocked** (blocked = a later
  stage in the auto-chain that can't run because an earlier one didn't pass)
- `GraphNodeEvent` — a DAG node's status changed (drives the live graph view)
- `FileChangeEvent` — the watcher detected a debounced file change (created/modified/
  renamed/deleted/git_changed/build_output_changed — see `core/file_watcher.py`)
- `LogEvent` — a log line, mirrored into the in-app Log Viewer
- `ollama_status_changed`, `report_ready`, `clean_copy_ready` — misc status signals
- `memory_gate_decided` — the memory gate's verdict on one Loop fix (run_id, remembered?, lesson)

Qt automatically marshals these across threads: a background pipeline
thread emits a signal, and any UI widget connected to it receives the call
on the main thread, safely.

## The multi-provider LLM layer (`app/core/llm/`)

Every pipeline calls `PipelineContext.llm_client: LLMClient` — never a
provider directly. `LLMClient.chat(provider_id, model, ...)` /
`.embed(...)` / `.list_models(...)` look up that provider's stored API key
(`AppSettings.api_keys`) and dispatch to the matching `LLMProvider`
implementation. `AppSettings.models` stores a `(provider, model)` pair per
pipeline (`harness_review_*`, `loop_fix_*`, `graph_review_*`,
`rag_embedding_*`), set independently on each tab via
`ui/widgets/provider_model_selector.py`. `ollama_local` wraps the original,
still fully-offline `OllamaClient`; `ollama_remote` is the same wire
protocol against a user-supplied host; the cloud providers
(gemini/openai/anthropic/huggingface) are plain `requests`-based REST
clients. Anthropic has no embeddings endpoint, so it's excluded from the
RAG embedding provider dropdown specifically (`registry.EMBEDDING_CAPABLE_PROVIDER_IDS`).

`LLMProvider.chat(..., on_token=None)` accepts an optional per-chunk
callback. Only the two Ollama providers actually stream (via
`OllamaClient.chat_stream`, Ollama's newline-delimited-JSON protocol); the
cloud providers accept the parameter for interface uniformity but call it
once with the full response. Loop Engineering's fix-generation call uses
this to emit throttled (~150ms) `StepEvent` updates with the growing
response, which is what makes the model appear to "type" live in the UI.

`ProviderModelSelectorWidget` (one per Harness/Loop/Graph/RAG tab) listens
for `bus.api_keys_changed` (Settings saved a key/host) and
`bus.ollama_status_changed` (the app's periodic local-Ollama health check)
so a model list that was empty because a key wasn't entered yet, or Ollama
hadn't finished starting, fills in on its own — no manual Refresh needed.
Fetch results also carry the provider id they were requested for, so a
slow response for a provider the user has since switched away from can't
land late and overwrite a newer selection.

## The Loop approval gate (`app/pipelines/loop/fix_approval.py`)

Loop runs on a background thread, but a human must approve every fix before
it's written. `request_approval()` emits `bus.fix_proposed` (carrying old
vs. proposed content per file) and then blocks that thread on a
`threading.Event` — real blocking, not polling — until `resolve_approval()`
is called from the `FixReviewDialog`'s Accept/Reject handler on the main
thread, or a 10-minute timeout elapses (treated as reject). Both live in
this module specifically so the concurrency primitive stays out of the
pipeline logic. Tests and automation bypass the wait entirely via
`set_headless_auto_approve()` — production code must never call it.

## The browser mirror (`app/web/server.py`)

`WebMirrorServer` is a FastAPI app serving one static page
(`web/static/index.html`) plus a `/ws` WebSocket, run on a background thread
with its own asyncio event loop (`main.py` starts it and opens a browser tab
on launch, gated by `AppSettings.web_dashboard_enabled`). Its constructor
connects a `_broadcast` lambda to every signal on `bus` that matters for a
live view (`step_updated`, `pipeline_updated`, `graph_node_updated`,
`log_emitted`, `file_changed`, `ollama_status_changed`, `clean_copy_ready`,
`memory_gate_decided`); each firing is appended to an in-memory history
(capped at 400) and, once the server thread has actually started
(`asyncio.run_coroutine_threadsafe` onto its loop), pushed to every connected
client. A freshly-connecting browser tab first replays the history so it
never misses events that happened before it opened. This is deliberately
read-only and additive: nothing sent from the browser changes any state, and
the desktop UI's own signal connections are completely unaffected by whether
the mirror is enabled.

## Memory and Eval — connecting existing subsystems, not duplicating them

Both tabs are presentation layers over data that already exists elsewhere,
not new stores:

- **Memory tab** (`ui/widgets/memory_widget.py`): semantic memory is
  `RagStore.list_sources()` (the same RAG knowledge base used in
  `rag_retrieval`); episodic memory is `reports/history.list_runs()`;
  procedural memory is the installed plugin steps
  (`plugins/loader.get_registry()`).
- **Memory gate** (`pipelines/loop/memory_gate.py`): after Loop Engineering
  resolves every failure (i.e. `iteration > 0` and `current_failures == 0`),
  the configured fix model is asked one more question — is this lesson
  generalizable, or specific to this one fix? A "yes" gets embedded and
  stored in the RAG store under a `learned-fix::<run_id>` source, feeding
  future `rag_retrieval` steps; either way the decision is recorded via
  `app/core/memory_log.py` and broadcast as `bus.memory_gate_decided`. This
  runs after Loop has already succeeded and is wrapped in a broad
  `try/except` in `loop_pipeline.py` specifically so it can never turn an
  otherwise-successful run into a failure.
- **Eval tab** (`ui/widgets/eval_widget.py`): every Harness step is already
  either a deterministic check or an LLM-as-judge call —
  `dashboard_metrics.DETERMINISTIC_STEP_IDS` / `LLM_JUDGE_STEP_IDS` classify
  the same step results the Dashboard and browser mirror already show, split
  into two columns, next to a release-gate banner driven by Graph's
  `PipelineEvent` (`completed` → passed, `failed`/`blocked` → blocked).

## Why Harness and Graph never diverge

`app/pipelines/steps/*.py` holds exactly one implementation per capability
(secret scan, build check, test run, AI review, ...). `harness_pipeline.py`
declares `HARNESS_STEPS` with a `depends_on` per step (mirroring Graph's
dependency edges) and `PipelineRunner` executes independent ones
concurrently via the same DAG-execution model `graph_executor.py` uses —
the Harness tab still shows all 21 steps in their original fixed order
(`PipelineRunner.announce()` pre-populates every row as "pending" up front),
but multiple can show "running" at once. `graph/agents.py` wraps the *same*
step functions as `GraphNode`s. The only behavioral difference between the
two panels is how they're organized (a flat dependency list vs. an explicit
agent DAG) — never what a given check does.

## The auto-chain (`app/core/pipeline_controller.py`)

On a file save: Harness runs. If it passes, Graph runs automatically next
(read-only, always safe). If it fails and "auto_loop_on_failure" is off,
the chain stops and the Loop/Graph tabs show a "blocked" `PipelineEvent`
explaining why. If auto-loop is on, Loop attempts a fix; Graph then runs
only if Loop resolved every failure. If Graph then approves
(`final_verification` succeeds), `app/export/clean_copy.py` exports the
project to Downloads and the "Copy Clean Project" tab picks up
`bus.clean_copy_ready`. Manual "Run Now" buttons on every tab work
independently of this chain at any time.

## The Dashboard (`app/core/dashboard_metrics.py`)

A 2-second `QTimer` calls `build_snapshot()`, which reads CPU/memory via
`psutil`, queue/running counts from `PipelineController`, and — from the
most recent run's `report.json` (see `reports/history.py`) — security/
quality scores (pass-rate over the security- and quality-relevant step
subsets), build/test status, the latest AI decision text, and a derived
overall health label. `DashboardWidget` also tracks live "Currently
Running" state directly from `PipelineEvent`s on the bus.

## Threading model

- UI runs on the Qt main thread only.
- `watchdog.Observer` runs its own thread; each file event is debounced
  per-file (`AppSettings.debounce_seconds`, default 0.8s) before it reaches
  the event bus.
- `PipelineController` adds a second, per-project debounce window
  (`AppSettings.pipeline_batch_window_ms`, default 800ms) so several
  near-simultaneous file saves become one pipeline run, and never runs two
  Harness pipelines for the same project concurrently — new changes queue
  until the current run ends.
- Every pipeline run executes in `QThreadPool` via `run_in_background`
  (`app/core/pipeline_worker.py`), so the UI is never blocked, including
  during LLM HTTP calls. Within a single Harness/Graph run, independent
  steps/nodes additionally run concurrently on their own `ThreadPoolExecutor`
  (capped at 8 workers) — see "Why Harness and Graph never diverge" above.

## Extending the app

- **New Harness/Graph step**: add a function to `pipelines/steps/`, wire it
  into `HARNESS_STEPS` (with the right `depends_on`) and/or `build_agent_graph()`.
- **Third-party step without touching the core app**: drop a `.py` file
  defining `register(registry)` into
  `%LOCALAPPDATA%\HLGFramework\plugins\installed\` — see
  `examples/plugins/todo_scanner_plugin.py`. It's appended to every Harness
  run automatically.
- **New LLM provider**: implement `LLMProvider` in `core/llm/`, add it to
  `registry.PROVIDERS`. It immediately appears in every tab's Provider
  dropdown with no other changes.
- **New language ecosystem** (currently Python-only): add adapters in
  `analysis/` and `security/` following the existing pattern — each step
  wrapper in `pipelines/steps/` would dispatch to the right adapter based on
  `ProjectContext` (see `core/project_context.py`), which already detects
  the presence of Python build files as the seam for that dispatch.
