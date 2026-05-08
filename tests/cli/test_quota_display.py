from __future__ import annotations

from albert_code.cli.textual_ui.widgets.quota_display import (
    DANGER_STYLE,
    WARNING_STYLE,
    _counter_style,
    _ratio,
    build_quota_text,
)
from albert_code.core.llm.throttling import UsageSnapshot


def _snapshot(
    *,
    rpm_used: int = 0,
    rpm_limit: int | None = 50,
    tpm_used: int = 0,
    tpm_limit: int | None = 128_000,
    rpd_used: int | None = None,
    rpd_limit: int | None = None,
    tpd_used: int | None = None,
    tpd_limit: int | None = None,
) -> UsageSnapshot:
    return UsageSnapshot(
        provider="albert",
        model_name="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        window_seconds=60,
        rpm_limit=rpm_limit,
        rpm_used=rpm_used,
        tpm_limit=tpm_limit,
        tpm_used=tpm_used,
        debounce_seconds=1.2,
        blocked_for=0.0,
        limit_source="documented EXP tier",
        rpd_limit=rpd_limit,
        rpd_used=rpd_used,
        tpd_limit=tpd_limit,
        tpd_used=tpd_used,
    )


def test_counter_style_thresholds() -> None:
    assert _counter_style(0.0) == ""
    assert _counter_style(0.79) == ""
    assert _counter_style(0.80) == WARNING_STYLE
    assert _counter_style(0.94) == WARNING_STYLE
    assert _counter_style(0.95) == DANGER_STYLE
    assert _counter_style(1.5) == DANGER_STYLE


def test_ratio_handles_missing_or_zero_limit() -> None:
    assert _ratio(5, None) == 0.0
    assert _ratio(5, 0) == 0.0
    assert _ratio(50, 100) == 0.5
    assert _ratio(200, 100) == 1.0


def test_only_saturated_counter_carries_warning_style() -> None:
    # Mirrors the user-reported case: rpm fine, tpm saturated. Previously
    # the entire line turned warning, leading users to blame rpm. Now only
    # the offending span carries the style.
    text = build_quota_text(
        _snapshot(rpm_used=4, rpm_limit=10, tpm_used=108_000, tpm_limit=128_000)
    )
    assert text is not None
    assert text.plain == "rpm 4/10 tpm 108k/128k"
    # Healthy counters carry no Span (Rich only emits one when a style
    # is set), saturated counters carry the warning span.
    styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
    assert "rpm 4/10" not in styled
    assert styled["tpm 108k/128k"] == WARNING_STYLE


def test_danger_threshold_marks_counter_as_red() -> None:
    text = build_quota_text(
        _snapshot(rpm_used=5, rpm_limit=50, tpm_used=123_000, tpm_limit=128_000)
    )
    assert text is not None
    styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
    assert styled["tpm 123k/128k"] == DANGER_STYLE
    assert "rpm 5/50" not in styled


def test_returns_none_when_no_rpm_limit() -> None:
    assert build_quota_text(_snapshot(rpm_limit=None)) is None
