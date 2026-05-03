"""Persistent record of the last terminal 429 (daily quota exhausted).

Lets the next albert-code launch warn the user *before* the first call:
if Qwen3-Coder TPD was exhausted at 22:30 UTC and you reopen at 08:00 UTC,
the daily counter has not reset yet and the very first request will 429.

Stored as a tiny JSON file in ALBERT_CODE_HOME so it survives restarts
and machine reboots. Cross-process (other Albert clients on the same
account) is not detected here - that's what option A (live /me/usage
estimation) covers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import datetime as dt
import json
import logging

from albert_code.core.paths.global_paths import THROTTLE_STATE_FILE

logger = logging.getLogger(__name__)

# Daily quota windows on Albert reset at midnight UTC. We never want to
# show a stale "TPD exhausted" warning past the next reset.
_RESET_HOUR_UTC = 0


@dataclass(frozen=True)
class TerminalQuotaEvent:
    model_name: str
    reason: str
    body_excerpt: str
    recorded_at_iso: str  # UTC ISO8601

    @property
    def recorded_at(self) -> dt.datetime:
        return dt.datetime.fromisoformat(self.recorded_at_iso)


def save_terminal_quota_event(
    model_name: str, reason: str, body_text: str | None
) -> None:
    """Persist the last 429 daily-quota event. Best-effort, never raises."""
    payload = TerminalQuotaEvent(
        model_name=model_name,
        reason=reason,
        body_excerpt=(body_text or "")[:300],
        recorded_at_iso=dt.datetime.now(dt.UTC).isoformat(),
    )
    try:
        path = THROTTLE_STATE_FILE.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(payload), indent=2), encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not persist throttle state: %s", exc)


def load_terminal_quota_event() -> TerminalQuotaEvent | None:
    """Read the persisted 429 event. Returns None if absent or malformed."""
    try:
        text = THROTTLE_STATE_FILE.path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.debug("Could not read throttle state: %s", exc)
        return None
    try:
        data = json.loads(text)
        return TerminalQuotaEvent(
            model_name=data["model_name"],
            reason=data["reason"],
            body_excerpt=data.get("body_excerpt", ""),
            recorded_at_iso=data["recorded_at_iso"],
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.debug("Throttle state file is malformed: %s", exc)
        return None


def is_event_still_relevant(
    event: TerminalQuotaEvent, *, now: dt.datetime | None = None
) -> bool:
    """A daily-quota 429 stays relevant until the next midnight UTC after it."""
    now = now or dt.datetime.now(dt.UTC)
    recorded = event.recorded_at
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=dt.UTC)
    next_reset = (recorded + dt.timedelta(days=1)).replace(
        hour=_RESET_HOUR_UTC, minute=0, second=0, microsecond=0
    )
    return now < next_reset


def clear_terminal_quota_event_for_model(model_name: str) -> None:
    """Remove the persisted file if it concerns `model_name`.

    Called on a successful call. Only clears state for the same model the
    user just exercised - a successful call on `albert-large` shouldn't
    silence a still-valid `albert-code` warning.
    """
    event = load_terminal_quota_event()
    if event is None:
        return
    if event.model_name != model_name:
        return
    try:
        THROTTLE_STATE_FILE.path.unlink(missing_ok=True)
    except OSError as exc:
        logger.debug("Could not clear throttle state: %s", exc)
