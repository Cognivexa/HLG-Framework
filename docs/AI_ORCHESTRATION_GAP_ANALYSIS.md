# AI Engineering Orchestration Platform — Gap Analysis

This is Phase 1-2 of the target spec's own process (Section 67: Inspect → Architecture
Gap Analysis) for turning this app into a "one prompt → autonomous orchestration"
platform. It maps every capability the target spec asks for against what the codebase
actually does today, cites the real files/functions, and calls a verdict per item:

- **Already correct** — matches the target concept; keep as-is.
- **Needs refactor** — the mechanism/pattern is right and reusable, but scope/shape needs to change.
- **New subsystem** — does not exist in any form; this is greenfield work.

No code changes were made producing this document — it's the map the later phases (3-15
in the target spec) execute against, so those phases don't proceed on guesswork.

## Executive summary

The good news: three of this codebase's actual strongest subsystems are exactly the
three the target spec cares most about getting right, and they're already close to
correct:

- **Loop Engineering** (fix → verify → rollback with stall-based termination) is the
  single item closest to the target across the entire spec — the existing design
  (`app/pipelines/loop/loop_pipeline.py`) already does execute→observe→validate→diagnose→fix→re-execute
  with genuine evidence-based stopping, not a fixed iteration count.
- **Build/test verification is already evidence-based**, never trusting a model's
  self-report — `app/pipelines/steps/build_steps.py`/`test_steps.py` wrap real
  subprocess output.
- **The runtime model-fallback mechanism** (`app/core/llm_client.py`) is a genuinely
  working, visible, persisted fallback system already — a real asset to extend, not
  rebuild.
- **Document ingestion** (PDF/DOCX/TXT/MD/website/git-clone → chunk → embed → retrieve)
  already works end-to-end in `app/rag/`.

The bad news: the actual *product-vision centerpiece* — "one prompt decides what's
needed" — does not exist in any form. There is no Planner, no Intent Engine, no
acceptance-criteria concept, no dynamic per-task Graph, no Context Engineering layer
distinct from RAG, no web search, no deep research, no browser automation, no
tool-auto-discovery, and no model-driven tool-orchestration. Today's "Graph Engineering"
and "Harness Engineering" are a **fixed, always-identical 16-node/21-step verification
pipeline** that runs the same way for every file save — genuinely good at what it does,
but architecturally the opposite of "the planner decides what this task needs."

Multi-project isolation is also **not real today** — RAG knowledge, report history, and
model configuration are global/shared across every monitored project, only tagged with
a project-path string, not partitioned.

## Master gap table

| # | Target capability | Verdict | Current state (file:function) |
|---|---|---|---|
| 1 | Planner / Intent Engine (prompt → requirements → acceptance criteria → capability decision) | **New subsystem** | Does not exist. Only trigger today is `bus.file_changed` (`pipeline_controller.py:151`) |
| 2 | Single Auto Run master toggle orchestrating the whole flow | **Needs refactor** | `AppSettings.auto_run_enabled` (`settings.py:89-95`) only gates loop-auto-fire + auto-apply within the fixed chain |
| 3 | Centralized `ExecutionState` object | **New subsystem** | State is fragmented across `PipelineController`'s dicts and per-call closure args (`attempt`/`stall`/`prev_failures`) |
| 4 | Expanded event bus (PROMPT_RECEIVED...TASK_CANCELLED) | **Needs refactor** | `EventBus` has 13 signals today (`events.py:81-98`); mechanism generalizes, just needs more signals + correlation IDs |
| 5 | Stop/Pause/Resume an in-flight autonomous run | **New subsystem** | Only file-*monitoring* pause exists (`tray.py`); no cancellation token anywhere in `pipeline_worker.py` |
| 6 | Safe-failure with structured evidence (max time, repeated-error, stuck-state) | **Needs refactor** | Stall-based give-up already exists (`pipeline_controller.py:_stall_step`) but is message-text only, no max-wall-clock dimension |
| 7 | Human-approval gate for dangerous ops | **Needs refactor** | `bus.fix_proposed` exists but is narrow (Loop fixes only) and **bypassed entirely when Auto Run is on** — see decision #1 below |
| 8 | 10 model providers (HF, Ollama×2, Gemini, OpenRouter, Anthropic, Groq, SambaNova, Cerebras, NVIDIA NIM) | **Needs refactor (mostly additive)** | 6 exist today (5 overlap); the 5 missing all speak the same OpenAI-compatible `/chat/completions` shape already implemented twice (`openai.py`, `huggingface.py`) — cheap to add via a shared base class |
| 9 | 7 independent model roles (Planner/Research/Coding/Testing/Security/Review/General) | **New subsystem** | Today: 4 fixed pipeline-stage pairs + one panel list (`settings.py:PipelineModelChoice`) |
| 10 | Capability-aware automatic model selection | **New subsystem** | Today: pure heuristic string-matching (`registry.py:looks_embedding_only`), no capability metadata anywhere |
| 11 | LOCAL vs REMOTE labeling per provider/model | **Trivial addition** | Only implicit via display-name convention; no `is_local` field exists |
| 12 | Visible, persisted model fallback on runtime failure | **Already mostly correct** | Real, working system (`llm_client.py:_chat_with_fallback`) — gaps: opt-in only, no embedding fallback |
| 13 | RAG is conditional (Planner decides if needed) | **Needs refactor** | Always runs unconditionally today; **its results aren't even consumed by any other step** (`ai_steps.py:rag_knowledge_retrieval`) |
| 14 | Context Engineering as an explicit layer distinct from RAG | **Does not exist** | Every call site (`ai_steps.py`) does its own ad hoc local context gather; `with_skills()` is the closest thing but is a fixed always-on prepend |
| 15 | Document ingestion (PDF/DOCX/TXT/MD/URL) with visible progress | **Already mostly works** | Real end-to-end pipeline in `app/rag/ingestion.py`; gaps are metadata richness + per-document progress UI |
| 16 | Web search (query → sources → relevance → extraction) | **Total greenfield** | Zero search-engine code anywhere in the repo |
| 17 | Deep research (multi-query, cross-source synthesis) | **Total greenfield** | No research-plan concept anywhere |
| 18 | Controlled browser-automation tool layer | **Total greenfield** | Only fire-and-forget `webbrowser.open()` calls for humans to view pages; no read-back/navigation control |
| 19 | Dynamic, Planner-built per-task Graph | **Does not exist** | `orchestrator.route()` always returns the same fixed 16-node graph regardless of trigger (`agents.py:36-67`) |
| 20 | Harness as a permission/policy engine per agent role | **Conceptually different today** | Today's "Harness" is a fixed QA/verification pipeline, not an authorization layer — these are two different concepts sharing one name |
| 21 | Loop Engineering (execute→observe→validate→diagnose→fix→re-execute, stall-based stop) | **Already correct** | `loop_pipeline.py` already implements this faithfully — the strongest match to target in the whole spec |
| 22 | Tool auto-discovery (task decides which tools it needs) | **Does not exist** | Every step is unconditionally wired into the fixed pipeline; `Step.skip_if` exists but is for dependency-caching, not relevance |
| 23 | LangChain-style tool orchestration (model decides to call a tool) | **Does not exist** | Every "tool call" today is a hardcoded Python function call; no model ever chooses among available tools |
| 24 | Concurrency safety for parallel file writes | **Latent gap** | No file-level locking in `PipelineRunner`/`graph_executor`; not yet triggered since today's parallel nodes are all read-only |
| 25 | Automatic test *generation* (not just running existing tests) | **Does not exist** | Only a non-LLM placeholder-file scaffold exists (`architecture_fix.py:write_missing_scaffolding`); Loop's fix loop can't originate new files by name today |
| 26 | Build verification uses real tool output only | **Already correct** | `build_steps.py`/`test_steps.py` wrap real subprocess output; AI Code Review never substitutes for this evidence |
| 27 | Evidence-based acceptance criteria (prompt → explicit checklist) | **Does not exist** | "Done" is inferred ad hoc (`all StepResult.status != "failed"`); no criteria artifact anywhere |
| 28 | Severity classification (Critical/High/Medium/Low) with blocking distinction | **Does not exist** | `StepResult.status` is only success/failed/skipped; no severity field anywhere |
| 29 | Structured error objects (type, source, affected files, suggested action) | **Partial** | `StepResult.data` already carries file/line locations for some steps (secrets/quality); inconsistent, no fixed schema, missing for build/test |
| 30 | Animated UI driven only by real execution events | **Already correct** | Confirmed no fake progress anywhere — `GraphViewWidget`/`DashboardWidget`/`HowItWorksWidget` are pure bus-event listeners; the only gap is literal motion/easing, not authenticity |
| 31 | Live human-readable activity log | **Partial** | Infrastructure (event bus, list widgets) exists; narrative content (e.g. "6 chunks retrieved") isn't emitted by most steps |
| 32 | Stop/Pause/Resume + expanded tray (Stop Task, View Current Project) | **Does not exist** | Tray has exactly: Show Dashboard, Pause *Monitoring*, Quit — no in-flight run control at all |
| 33 | Multi-project isolated state (RAG/history/config) | **Does not exist (falsely assumed today)** | One global Chroma collection, one flat history JSON, one global `PipelineModelChoice` — all shared across every monitored project, tagged only by a path string |
| 34 | Git integration (diffs, conflicts, agent-attributed changes) | **Does not exist** | Only informational `.git/HEAD`-write detection (`file_watcher.py`); zero diff/commit/branch code anywhere |
| 35 | Project-level checkpoint/rollback | **Does not exist** | Only per-file backup scoped to files Loop itself touches (`backup.py`); no whole-project snapshot before an autonomous run |

## Decisions needed before Phase 3+ starts coding

These aren't engineering tasks — they're product calls the gap analysis surfaced that
change what gets built:

1. **Auto Run vs. mandatory approval gates.** Today's Auto Run is explicitly documented
   as "no prompts, ever" (`settings.py` docstring), and it already bypasses Loop's own
   fix-approval flow. The target spec wants dangerous operations to *always* gate
   regardless. These directly conflict — decide whether Auto Run governs routine
   fixes only, with destructive ops always gating regardless of the toggle.
2. **Is OpenAI in or out?** It's implemented and used today (including as a fallback
   candidate) but is absent from the target's 10-provider list. Removing it is a
   breaking change for anyone with it saved in `config.json`.
3. **Role-based model config migration.** Moving from 4 fixed pipeline-stage pairs to 7
   independent roles needs an explicit mapping (is Harness-review → Review role?
   Loop-fix → Coding role?) and a `config.json` migration path, not just new code.
4. **RAG/history/config project isolation: partition or tag-and-filter?** Partitioning
   (separate Chroma collections/history files per project) is cleaner but a bigger
   change than adding a project filter to existing shared stores.
5. **Should checkpoints be git-based?** Git-based checkpointing (commit before an
   autonomous run) is the more natural mechanism but assumes every monitored project
   is already a git repo — that's never validated today and isn't a safe assumption to
   bake in silently.
6. **Capability-aware model selection: maintained table or name-convention inference?**
   Real per-model capability metadata isn't reliably available from most provider
   APIs — decide whether this app ships/maintains a curated table (goes stale) or
   infers from model-name conventions (unreliable) or skips true capability-awareness
   for now and keeps today's heuristic.

## Recommended phase order

Ordered by dependency (each phase's foundation must exist before the next is safe to
build) and by risk (cheap, additive, isolated wins first):

**Phase A — Cheap wins, no architecture change** (items 8, 11, 12 partial)
Add 3-5 new OpenAI-compatible providers (Groq/OpenRouter/Cerebras/SambaNova/NVIDIA NIM)
via a shared base class reusing `openai.py`'s pattern; add LOCAL/REMOTE labeling; extend
the existing fallback mechanism to embeddings and more call sites. Low risk, directly
answers several of the spec's explicit asks, no behavioral change to anything working.

**Phase B — Foundation** (items 3, 4)
Centralized `ExecutionState` + expanded event bus with correlation IDs. Every later
phase depends on this existing first. Highest-risk item flagged: thread-safety of a
shared mutable object touched by background workers — needs its own design pass before
coding (likely: workers only ever emit events with immutable payloads; a single
UI-thread-owned object applies them, never mutated directly from a worker thread).

**Phase C — The actual product vision** (items 1, 9, 27)
Planner/Intent Engine + role-based model config + acceptance-criteria schema. This is
what turns "one prompt" into a real decision instead of always running the same fixed
chain. Depends on Phase B's ExecutionState to record requirements/criteria/decisions
somewhere real.

**Phase D — Dynamic execution** (items 19, 20, 22, 23)
Planner-built per-task Graph, tool auto-discovery, model-driven tool orchestration, and
reframing Harness as a real permission layer. Depends on Phase C's Planner existing to
emit anything for the Graph to execute. This is the largest, highest-risk phase — the
gap analysis flagged a real hang risk (`base.py`'s dependency-satisfaction loop makes
silent zero progress on an unsatisfiable graph rather than erroring) that needs a
watchdog before dynamic graphs go live.

**Phase E — Depth** (items 13, 14, 16, 17, 25, 28, 29)
Wire RAG conditionally (and actually consume its results downstream — today it's
computed and discarded), build the Context Engineering assembly layer, add web
search/deep research, severity classification, structured errors, and real test
generation.

**Phase F — Platform hardening** (items 5, 7, 32, 33, 34, 35, 18)
Stop/Pause/Resume + tray expansion, resolve the Auto-Run/approval-gate conflict from
decision #1, multi-project isolation, git integration, project checkpoints, and browser
automation last — it's the highest-blast-radius capability (arbitrary site
interaction, credential exposure risk) and least urgent relative to the rest.

## What this document is not

This is not an implementation plan for any single phase — each phase above still needs
its own design pass (and, per the process that produced last session's retry-logic and
provider-fallback work, its own plan-mode review) before code changes. Treat this as
the map; the next conversation should pick one phase and go through Explore → Design →
Implement → Verify for that phase specifically, not attempt all six at once.
