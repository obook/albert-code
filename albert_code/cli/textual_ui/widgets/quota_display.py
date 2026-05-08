"""Bottom-bar widget showing the live Albert API quota usage.

Shows a compact "rpm USED/LIMIT - tpm USED/LIMIT" string for the
active Albert model, refreshed periodically from the rolling 60s
counters maintained by the Throttler.

The data is local to this albert-code process: it cannot account for
calls made by other clients sharing the same Albert key (e.g. a web
albert-cli running for a classroom on the same teacher key). For a
richer view including documented daily tiers, use the /rpm and
/quota slash commands.

Each counter is coloured independently: only the one that actually
crossed its threshold turns yellow/red, so the user can tell at a
glance which quota is the bottleneck (e.g. tpm saturated while rpm
is fine).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.text import Text

from albert_code.cli.textual_ui.widgets.no_markup_static import NoMarkupStatic

if TYPE_CHECKING:
    from albert_code.core.llm.throttling import UsageSnapshot


# At or above this fraction of the limit, the counter switches to a
# warning style (yellow) ; above DANGER, to a danger style (red bold).
WARNING_RATIO = 0.8
DANGER_RATIO = 0.95

WARNING_STYLE = "yellow"
DANGER_STYLE = "bold red"

# Thresholds for compact token formatting (3500 -> 3.5k, 128000 -> 128k, 2.5M -> 2.5M).
_THOUSAND = 1_000
_HUNDRED_THOUSAND = 100_000
_MILLION = 1_000_000


class QuotaDisplay(NoMarkupStatic):
    """Compact rpm/tpm gauge for the bottom bar."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.can_focus = False

    def clear(self) -> None:
        """Hide the widget (e.g. when the active provider is not Albert)."""
        self.update("")

    def update_from_snapshot(self, snap: UsageSnapshot | None) -> None:
        """Refresh the displayed gauge from a Throttler snapshot.

        If the snapshot has no rpm limit (Albert quotas not yet fetched
        or unknown model tier), the widget hides itself. Each counter is
        coloured against its own ratio so the offending quota is
        immediately visible — colouring the whole line on `max(ratios)`
        used to mislead users into blaming the first counter (rpm)
        whatever was actually saturated.
        """
        text = build_quota_text(snap)
        if text is None:
            self.clear()
            return
        self.update(text)


def build_quota_text(snap: UsageSnapshot | None) -> Text | None:
    """Build the styled gauge text from a snapshot, or None when nothing to show."""
    if snap is None or snap.rpm_limit is None:
        return None

    text = Text()
    _append_counter(
        text,
        "rpm",
        str(snap.rpm_used),
        str(snap.rpm_limit),
        _ratio(snap.rpm_used, snap.rpm_limit),
    )
    if snap.tpm_limit is not None:
        text.append(" ")
        _append_counter(
            text,
            "tpm",
            _compact_tokens(snap.tpm_used),
            _compact_tokens(snap.tpm_limit),
            _ratio(snap.tpm_used, snap.tpm_limit),
        )

    if snap.rpd_used is not None and snap.rpd_limit is not None:
        text.append(" ")
        _append_counter(
            text,
            "rpd",
            str(snap.rpd_used),
            str(snap.rpd_limit),
            _ratio(snap.rpd_used, snap.rpd_limit),
        )
    if snap.tpd_used is not None and snap.tpd_limit is not None:
        text.append(" ")
        _append_counter(
            text,
            "tpd",
            _compact_tokens(snap.tpd_used),
            _compact_tokens(snap.tpd_limit),
            _ratio(snap.tpd_used, snap.tpd_limit),
        )
    return text


def _counter_style(ratio: float) -> str:
    if ratio >= DANGER_RATIO:
        return DANGER_STYLE
    if ratio >= WARNING_RATIO:
        return WARNING_STYLE
    return ""


def _append_counter(
    text: Text, label: str, used: str, limit: str, ratio: float
) -> None:
    text.append(f"{label} {used}/{limit}", style=_counter_style(ratio))


def _ratio(used: int, limit: int | None) -> float:
    if not limit or limit <= 0:
        return 0.0
    return min(1.0, max(0.0, used / limit))


def _compact_tokens(value: int) -> str:
    """Format a token count compactly (3500 -> 3.5k, 128000 -> 128k)."""
    if value >= _MILLION:
        return f"{value / _MILLION:.1f}M"
    if value >= _HUNDRED_THOUSAND:
        return f"{value // _THOUSAND}k"
    if value >= _THOUSAND:
        return f"{value / _THOUSAND:.1f}k".replace(".0k", "k")
    return str(value)
