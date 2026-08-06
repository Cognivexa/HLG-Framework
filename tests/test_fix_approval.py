"""Tests for the cross-thread human-approval handshake Loop Engineering uses
before writing any fix (app.pipelines.loop.fix_approval). Approval is now
per-file — the user can accept some proposed files and reject others in the
same round — so `request_approval`/`resolve_approval` exchange
{file_path: approved} dicts rather than a single overall bool."""
from __future__ import annotations

import threading
import time

import pytest

from app.pipelines.loop.fix_approval import (
    FixProposal,
    request_approval,
    resolve_approval,
    set_headless_auto_approve,
)

_FILES = {"a.py": {"old": "old", "new": "new"}}
_MULTI_FILES = {"a.py": {"old": "old-a", "new": "new-a"}, "b.py": {"old": "old-b", "new": "new-b"}}


@pytest.fixture(autouse=True)
def _reset_headless_override():
    yield
    set_headless_auto_approve(None)  # never leak an override into other tests


def test_request_approval_blocks_until_resolved():
    proposal = FixProposal(run_id="run-1", step_id="apply_fix_1", iteration=1, files=_FILES)
    result_holder = {}

    def worker():
        result_holder["approved"] = request_approval(proposal, timeout=5)

    thread = threading.Thread(target=worker)
    thread.start()

    time.sleep(0.2)
    assert "approved" not in result_holder  # still blocked

    resolve_approval("run-1", "apply_fix_1", {"a.py": True})
    thread.join(timeout=5)

    assert result_holder["approved"] == {"a.py": True}


def test_request_approval_rejected():
    proposal = FixProposal(run_id="run-2", step_id="apply_fix_1", iteration=1, files=_FILES)
    result_holder = {}

    def worker():
        result_holder["approved"] = request_approval(proposal, timeout=5)

    thread = threading.Thread(target=worker)
    thread.start()
    time.sleep(0.1)
    resolve_approval("run-2", "apply_fix_1", {"a.py": False})
    thread.join(timeout=5)

    assert result_holder["approved"] == {"a.py": False}


def test_request_approval_partial_approval_per_file():
    proposal = FixProposal(run_id="run-partial", step_id="apply_fix_1", iteration=1, files=_MULTI_FILES)
    result_holder = {}

    def worker():
        result_holder["approved"] = request_approval(proposal, timeout=5)

    thread = threading.Thread(target=worker)
    thread.start()
    time.sleep(0.1)
    resolve_approval("run-partial", "apply_fix_1", {"a.py": True, "b.py": False})
    thread.join(timeout=5)

    assert result_holder["approved"] == {"a.py": True, "b.py": False}


def test_request_approval_times_out_as_rejected():
    proposal = FixProposal(run_id="run-3", step_id="apply_fix_1", iteration=1, files=_MULTI_FILES)
    approved = request_approval(proposal, timeout=0.2)
    assert approved == {"a.py": False, "b.py": False}


def test_headless_auto_approve_bypasses_wait():
    set_headless_auto_approve(True)
    proposal = FixProposal(run_id="run-4", step_id="apply_fix_1", iteration=1, files=_MULTI_FILES)

    start = time.monotonic()
    approved = request_approval(proposal, timeout=30)
    elapsed = time.monotonic() - start

    assert approved == {"a.py": True, "b.py": True}
    assert elapsed < 1  # never actually waited


def test_auto_apply_bypasses_wait_and_approves_everything():
    proposal = FixProposal(run_id="run-auto", step_id="apply_fix_1", iteration=1, files=_MULTI_FILES)

    start = time.monotonic()
    approved = request_approval(proposal, timeout=30, auto_apply=True)
    elapsed = time.monotonic() - start

    assert approved == {"a.py": True, "b.py": True}
    assert elapsed < 1


def test_resolve_approval_for_unknown_key_is_a_noop():
    resolve_approval("nonexistent-run", "nonexistent-step", {"a.py": True})  # must not raise


def test_concurrent_proposals_use_independent_keys():
    proposal_a = FixProposal(run_id="run-a", step_id="apply_fix_1", iteration=1, files=_FILES)
    proposal_b = FixProposal(run_id="run-b", step_id="apply_fix_1", iteration=1, files=_FILES)
    results = {}

    def worker(name, proposal):
        results[name] = request_approval(proposal, timeout=5)

    t_a = threading.Thread(target=worker, args=("a", proposal_a))
    t_b = threading.Thread(target=worker, args=("b", proposal_b))
    t_a.start()
    t_b.start()
    time.sleep(0.2)

    resolve_approval("run-b", "apply_fix_1", {"a.py": False})
    resolve_approval("run-a", "apply_fix_1", {"a.py": True})
    t_a.join(timeout=5)
    t_b.join(timeout=5)

    assert results == {"a": {"a.py": True}, "b": {"a.py": False}}
