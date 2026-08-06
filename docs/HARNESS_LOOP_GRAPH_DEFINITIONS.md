# Harness / Loop / Graph Engineering — Definitions and Provenance

This app's three panels are named **Harness Engineering**, **Loop Engineering**,
and **Graph Engineering**. Before building it, we researched the reference
article this naming was inspired by: [Anthropic — "Designing harnesses for
long-running agentic applications"](https://www.anthropic.com/engineering/harness-design-long-running-apps).
This document records exactly what that article does and does not say, so
this product's terminology is never misattributed.

## What the Anthropic article actually says

- **Harness design**: a practice for structuring how AI agents tackle long,
  complex tasks. Key ideas: decomposing work into tractable chunks (an
  "initializer agent" turns a spec into a task list), handing off context
  between agent sessions via **structured artifacts** rather than raw
  conversation history, and performing hard **context resets** (a fresh
  agent + a structured handoff) instead of relying on compaction alone, to
  avoid "context anxiety" — agents prematurely wrapping up as their context
  window fills.
- **A generator/evaluator feedback loop** (GAN-inspired): a **generator**
  agent produces work; a separate **evaluator** agent grades it using tools
  (e.g. Playwright MCP driving a real browser) against a "sprint contract"
  the two agents negotiated up front. The article is explicit about *why*
  the evaluator must be a separate agent: models asked to grade their own
  output tend to "confidently praise" it even when a human would call it
  mediocre.
- **The article never uses the term "Loop Engineering."** The closest
  concept is the generator/evaluator feedback loop described above.
- **The article never discusses "Graph Engineering," graphs, or DAG-based
  multi-agent orchestration at all.** No such concept appears in it.

## What this app means by each term

Given the above, this app's three-panel framing is **this product's own
design**, only partially grounded in the article:

| Panel | What it actually is | Relationship to the article |
|---|---|---|
| **Harness Engineering** | A fixed, sequential 18-step pipeline (secret scanning, dependency/static/security analysis, build, tests, an Ollama code review, RAG retrieval, architecture checks, report generation) run against changed files. | Matches the article's spirit of *decomposing* a large verification task into discrete, structured steps. |
| **Loop Engineering** | An iterative retry loop: run checks → on failure, send the failure details + file content to an Ollama "fix" model → back up the file → apply the candidate fix → re-run checks → keep the fix only if it strictly improved the result, else roll back → repeat until pass or a retry limit. | Directly implements the article's **generator/evaluator** pattern: the fix model is the generator, the re-run checks are the evaluator, and the backup/rollback is this app's safety mechanism for autonomously applying a generator's output. |
| **Graph Engineering** | A 16-agent DAG (see `app/pipelines/graph/agents.py`) executed with real concurrency for independent nodes, via a Router/Orchestrator that decides node order and parallel groups. Most agents wrap the *same* step implementations Harness uses; a few (Documentation Agent, Secret Detection Agent, Code Improvement Agent, Report Generation Agent, Final Verification Agent) are unique to this view. | **Not sourced from the article at all.** This is this app's own multi-agent orchestration design, included because the product spec asked for a graph-based execution model as a third, concurrency-oriented view of the same underlying checks. |

## Why this matters for how you use the app

- If you're looking for Anthropic's actual guidance on building long-running
  agent harnesses, read the source article directly — don't treat this
  app's UI labels as a paraphrase of it.
- **Harness** and **Graph** intentionally share step implementations
  (`app/pipelines/steps/*`) so the same check never has two divergent
  behaviors depending on which panel triggered it. Harness runs them
  sequentially, in the order listed in the original product spec; Graph
  runs the independent ones concurrently.
- **Loop** is the only panel that writes to your source files, and only
  ever does so with a backup taken first and an automatic rollback if the
  change didn't help.
