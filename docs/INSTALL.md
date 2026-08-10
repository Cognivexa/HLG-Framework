# Installation

## Prerequisites

- Windows 10/11
- Python 3.10+ on PATH (tested on 3.14)
- **Either** [Ollama](https://ollama.com) installed and running locally
  (`ollama serve`, or the Ollama desktop app) — pull at least one chat
  model and one embedding model, e.g.:
  ```
  ollama pull llama3.1
  ollama pull nomic-embed-text
  ```
  **or** an API key for one of the cloud providers (Google Gemini, OpenAI,
  Anthropic, HuggingFace) entered in Settings — no local model required in
  that case. Local Ollama is the default and needs no key.
- Optional: the VS Code CLI (`code`) on PATH, so the Issue Sidebar's "Open
  in VS Code" button can jump straight to a failing line.
- Optional, for full functionality on monitored projects: `git` on PATH
  (for RAG git-repo ingestion). Each monitored *project* should have its
  own virtual environment with `pytest` installed if you want real unit
  test results — the app runs tests inside the project's own environment,
  not its own.

## Setup

```
cd HLG-Framework
run.bat
```

`run.bat` creates a `.venv`, installs `requirements.txt`, and launches the
app. Subsequent runs reuse the same `.venv`.

To run without the batch file:

```
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app
```

## First run

1. The app opens on the **Dashboard** tab and shows an "Ollama: connected /
   not detected" banner plus live CPU/memory and job metrics.
2. If you're using a cloud provider, enter its API key once in **Settings**
   → "Cloud Provider API Keys". Then on each of the Harness / Loop / Graph /
   RAG tabs, use that tab's own **Provider** + **Model** dropdowns — models
   populate automatically once a provider is selected (and a key present,
   if it needs one).
3. On **Dashboard**, click **Add Project Folder…** and pick a Python
   project. It starts being watched immediately — recursively, debounced,
   only re-analyzing files you actually changed.
4. Save a `.py` file in that project and watch the **Harness Engineering**
   tab light up step by step (independent steps run concurrently). Click any
   failed step to open the Issue Sidebar and jump to it in VS Code.
5. If Harness passes, **Graph Engineering** runs automatically next. If it
   fails, **Loop Engineering** only runs automatically if you enable
   **Auto Run** in Settings or on the Dashboard (off by default, since it
   writes to your files) — otherwise the Loop/Graph tabs show a clear
   "blocked" status naming exactly what failed. Both also have their own
   manual "Run Now" button at any time. New to these three concepts? Open
   the **How It Works** tab first.
6. Once the full chain passes for a project, check the **Copy Clean
   Project** tab — a clean, tested copy is auto-exported to Downloads.

See [`TESTING_GUIDE.md`](TESTING_GUIDE.md) for a hands-on walkthrough using
a small example project with two intentional issues.

## Data locations

Everything the app persists lives under:

```
%LOCALAPPDATA%\HLGFramework\
  config.json        settings
  logs\               rotating app log
  rag_store\          Chroma vector database
  reports\<run_id>\   report.json / report.html / report.pdf per run
  history\index.json  run history index
  plugins\installed\  drop .py plugin files here
```

(Renamed from `%LOCALAPPDATA%\HarnessEngineering\` — a one-time, one-way
copy runs automatically on first launch after upgrading, so nothing is
lost.)

By default (the "Ollama (Local)" provider on every tab) nothing leaves this
machine — all AI calls go to your local Ollama server at the host configured
in Settings (default `http://127.0.0.1:11434`). If you explicitly select a
cloud provider on a tab — including Ollama's own cloud models at
`ollama.com` — that pipeline's calls go to that provider's API using the key
you entered in Settings.

## Packaging as a standalone .exe

Not included in this pass by design (see the project plan) — running from
source with `run.bat` was the agreed first milestone. PyInstaller packaging
is a mechanical follow-up once the feature set is stable, e.g.:

```
pip install pyinstaller
pyinstaller --name HLGFramework --windowed --onedir -m app
```
