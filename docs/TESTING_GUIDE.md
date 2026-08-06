# Testing Guide — verify Harness, Loop, and Graph Engineering yourself

This walks through `examples/test_project/`, a tiny project with two
intentional problems, so you can watch all three engines work on real
issues rather than trusting the description alone.

## What's in the test project

`examples/test_project/calculator.py` has:

1. **A hardcoded password** (`DB_PASSWORD = "SuperSecret123!"`) — a real
   security issue Harness's secret scanner and ruff-based security scan
   both catch.
2. **A logic bug in `subtract`** — it adds instead of subtracting — with a
   failing test in `tests/test_calculator.py` that proves it.

## Setup

1. Copy `examples/test_project/` to somewhere outside this repo, e.g.
   `Desktop\HarnessTestProject` — you don't want the platform watching its
   own example files.
2. In the app's **Settings** tab, enter at least one API key or make sure
   Ollama is running locally, then go set a model on each tab you'll use
   (Harness, Loop, Graph each have their own Provider + Model dropdowns
   right on the tab).
3. On the **Dashboard** tab, click **Add Project Folder…** and select your
   copy of the test project. Monitoring starts immediately.
4. A browser tab should have opened automatically to `http://127.0.0.1:8765`
   — a live, read-only mirror of the same events you'll see in the desktop
   app below. Keep it open side by side; every step in Harness/Loop/Graph
   below animates there too, in real time.

## Step 1 — watch Harness Engineering catch the problems

Open `calculator.py` in any editor, make a trivial edit (add a blank line
is enough), and save. Switch to the **Harness Engineering** tab: within a
second or two you'll see all 18 steps light up, with several running
concurrently. Expect:

- `Scan for API keys` / `Detect passwords` — ❌ (the hardcoded password)
- `Security vulnerability scan` — ❌ (ruff's S105 rule, same issue)
- `Unit test execution` — ❌ (the `subtract` bug)
- Everything else — ✅ or skipped

**Click any ❌ row.** The Issue Sidebar on the right classifies it
("Security issue" / "Unit test failure" / ...), shows the full detail, and
lists the exact file:line — click **Open in VS Code** to jump straight
there.

Because Harness failed, Graph Engineering does **not** run yet — the Graph
tab will show "blocked — Harness Engineering must pass first" (only if
"Automatically run Loop Engineering..." in Settings is off; see next step).

## Step 2 — watch Loop Engineering propose, and review, a fix

In **Settings**, check "Automatically run Loop Engineering after a failed
Harness run" and save. Re-save `calculator.py` (or click **Run Loop
Engineering Now** on the **Loop Engineering** tab for an on-demand run
instead of waiting for the auto-chain).

Watch the Loop tab: it sends the failures + file content to your configured
fix model, and you'll see the response appear live, token by token, as the
model writes it. Once it's done, **a dialog pops up showing a diff** — the
password's old vs. proposed new line, `subtract`'s old vs. proposed new
line — with **Accept** / **Reject** buttons. Nothing is written to your
file until you click one:

- **Accept** — backs up `calculator.py`, applies the change, and re-runs
  the checks. If it didn't actually help, it's automatically rolled back
  from backup and Loop tries again (up to the retry limit in Settings).
- **Reject** — nothing is written; the model is asked to try a different
  approach next iteration.

Accept it, and you should see the password replaced with an
environment-variable lookup and `subtract` corrected to `a - b`, with the
loop stopping once `unit_tests` and `security_scan` both pass.

Right after that, a `memory_gate` row appears: the fix model is asked
whether the lesson from this fix generalizes to other code. Check the
**Memory** tab — if it judged "yes", you'll see a new entry under Semantic
memory (`learned-fix::<run_id>`) and a "Remembered: …" line under Memory
gate decisions; if "no" (or no RAG embedding model is configured), you'll
see why under Memory gate decisions instead. Either way, nothing here is
guessed — it's the same model call, verified live.

## Step 3 — watch Graph Engineering approve the clean result

Once Loop resolves everything, **Graph Engineering** runs automatically
next. Its tab shows the 16-agent DAG live — independent agents (security,
build, docs, RAG, Ollama review, ...) go "running" concurrently rather than
one at a time, ending in `final_verification: APPROVED — all checks passed.`

## Step 4 — check the clean-copy export

Open the **Copy Clean Project** tab. A timestamped copy of your test
project should now be listed, already exported to your Downloads folder,
confirming it's clean and tested. Click **Open Folder** to see it.

## Step 5 — check the Eval tab

Open the **Eval** tab: the same Harness step results, split into
Deterministic checks (pytest/ruff/pip-audit) on the left and LLM-as-judge
calls (AI code review, architecture validation, Graph's final verification)
on the right, with a Release gate banner that flips to PASSED once Graph
approves — the same moment the clean copy gets exported.

## Optional: Reports and RAG

- The **Reports** tab lists every run (Harness/Loop/Graph) with pass/fail
  counts; click one and **Open Report Folder** to see the generated
  JSON/HTML/PDF.
- The **RAG** tab lets you add a knowledge source (try a `.md` file with a
  coding standard like "never hardcode secrets") and then re-run Harness —
  the `RAG knowledge retrieval` step will surface it.
