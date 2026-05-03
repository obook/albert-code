"""Bottom-bar widget showing the live Albert API quota usage.

Shows a compact "rpm USED/LIMIT - tpm USED/LIMIT" string for the
active Albert model, refreshed periodically from the rolling 60s
counters maintained by the Throttler.

The data is local to this albert-code process: it cannot account for
calls made by other clients sharing the same Albert key (e.g. a web
albert-cli running for a classroom on the same teacher key). For a
richer view including documented daily tiers, use the /rpm and
/quota slash commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from albert_code.cli.textual_ui.widgets.no_markup_static import NoMarkupStatic

if TYPE_CHECKING:
    from albert_code.core.llm.throttling import UsageSnapshot


# At or above this fraction of the limit, the widget switches to a
# warning style (yellow) ; above DANGER, to a danger style (red).
WARNING_RATIO = 0.8
DANGER_RATIO = 0.95


class QuotaDisplay(NoMarkupStatic):
    """Compact rpm/tpm gauge for the bottom bar."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.can_focus = False

    def clear(self) -> None:
        """Hide the widget (e.g. when the active provider is not Albert)."""
        self.remove_class("quota-warning")
        self.remove_class("quota-danger")
        self.update("")

    def update_from_snapshot(self, snap: UsageSnapshot | None) -> None:
        """Refresh the displayed gauge from a Throttler snapshot.

        If the snapshot has no rpm limit (Albert quotas not yet fetched
        or unknown model tier), the widget hides itself. The snapshot
        is captured under the throttler's lock and reflects the rolling
        60-second window at this instant. The rpd/tpd part appears as
        soon as the periodic /v1/me/usage refresh has populated them.
        """
        if snap is None or snap.rpm_limit is None:
            self.clear()
            return

        # Per-minute window (always shown).
        parts = [f"rpm {snap.rpm_used}/{snap.rpm_limit}"]
        if snap.tpm_limit is not None:
            parts.append(
                f"tpm {_compact_tokens(snap.tpm_used)}/{_compact_tokens(snap.tpm_limit)}"
            )

        # Per-day window (shown only when /v1/me/usage has been polled and
        # the documented tier carries an rpd/tpd cap).
        if snap.rpd_used is not None and snap.rpd_limit is not None:
            parts.append(f"rpd {snap.rpd_used}/{snap.rpd_limit}")
        if snap.tpd_used is not None and snap.tpd_limit is not None:
            parts.append(
                f"tpd {_compact_tokens(snap.tpd_used)}/{_compact_tokens(snap.tpd_limit)}"
            )

        self.update("[" + " ".join(parts) + "]")

        # Pick the strongest signal across all four counters to colour the
        # line: any one being close to its cap deserves attention.
        ratios = [_ratio(snap.rpm_used, snap.rpm_limit)]
        if snap.tpm_limit is not None:
            ratios.append(_ratio(snap.tpm_used, snap.tpm_limit))
        if snap.rpd_used is not None and snap.rpd_limit:
            ratios.append(_ratio(snap.rpd_used, snap.rpd_limit))
        if snap.tpd_used is not None and snap.tpd_limit:
            ratios.append(_ratio(snap.tpd_used, snap.tpd_limit))
        ratio = max(ratios)

        self.set_class(ratio >= DANGER_RATIO, "quota-danger")
        self.set_class(WARNING_RATIO <= ratio < DANGER_RATIO, "quota-warning")


def _ratio(used: int, limit: int | None) -> float:
    if not limit or limit <= 0:
        return 0.0
    return min(1.0, max(0.0, used / limit))


def _compact_tokens(value: int) -> str:
    """Format a token count compactly (3500 -> 3.5k, 128000 -> 128k)."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 100_000:
        return f"{value // 1_000}k"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    return str(value)
