"""Cross-thread human-approval gate for Loop Engineering's proposed fixes.

Loop runs on a background thread (via run_in_background) and, per user
choice, must now pause before writing any candidate fix until the user
decides — file by file — which of the proposed changes to actually apply.
The background thread calls `request_approval(...)`, which emits
`bus.fix_proposed` and blocks on a threading.Event; the UI calls
`resolve_approval(...)` when the user responds (from inside the dialog's
button handler), which unblocks it.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from app.core.events import bus
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT_SECONDS = 600  # don't hang forever if the user walks away — treated as reject-all


@dataclass
class FixProposal:
    run_id: str
    step_id: str
    iteration: int
    files: dict[str, dict[str, str]] = field(default_factory=dict)  # path -> {"old": ..., "new": ...}


class _PendingApproval:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.approved_files: dict[str, bool] = {}


_pending: dict[str, _PendingApproval] = {}
_lock = threading.Lock()

# Testing/automation seam only: bypasses the UI wait entirely when set to a
# bool (applied to every file in the proposal). Production code must never
# call this — real runs always wait for a human. None (the default) means
# "wait for the real UI".
_headless_auto_approve: bool | None = None


def set_headless_auto_approve(accept: bool | None) -> None:
    global _headless_auto_approve
    _headless_auto_approve = accept


def request_approval(
    proposal: FixProposal, timeout: float = DEFAULT_TIMEOUT_SECONDS, auto_apply: bool = False
) -> dict[str, bool]:
    """Blocks the calling (background) thread until the user decides, file
    by file, which proposed changes to apply — or `timeout` elapses (every
    file treated as rejected). Returns {file_path: approved}.

    `auto_apply=True` (the "Auto Run" setting) skips the UI round-trip
    entirely — no `fix_proposed` event is emitted, so no review dialog ever
    opens, and every proposed file is approved immediately."""
    if auto_apply:
        return dict.fromkeys(proposal.files, True)
    if _headless_auto_approve is not None:
        bus.fix_proposed.emit(proposal)
        return dict.fromkeys(proposal.files, _headless_auto_approve)

    pending = _PendingApproval()
    key = f"{proposal.run_id}:{proposal.step_id}"
    with _lock:
        _pending[key] = pending

    bus.fix_proposed.emit(proposal)

    got_response = pending.event.wait(timeout)
    with _lock:
        _pending.pop(key, None)

    if not got_response:
        logger.warning("Fix approval for %s timed out after %ss — treating as rejected.", key, timeout)
        return dict.fromkeys(proposal.files, False)
    return pending.approved_files


def resolve_approval(run_id: str, step_id: str, approved_files: dict[str, bool]) -> None:
    key = f"{run_id}:{step_id}"
    with _lock:
        pending = _pending.get(key)
    if pending is None:
        logger.warning("No pending fix approval found for %s (already resolved or timed out?)", key)
        return
    pending.approved_files = approved_files
    pending.event.set()
