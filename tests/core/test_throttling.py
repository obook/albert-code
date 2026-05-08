from __future__ import annotations

import httpx
import pytest
import respx

from albert_code.core.config import Backend, ProviderConfig
from albert_code.core.llm.throttling import (
    RollingWindow,
    Throttler,
    get_throttler,
    reset_throttlers_for_tests,
)


def _make_provider(name: str = "albert") -> ProviderConfig:
    return ProviderConfig(
        name=name,
        api_base="http://test/v1",
        api_key_env_var="TEST_KEY",
        api_style="openai",
        backend=Backend.GENERIC,
    )


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestRollingWindow:
    def test_total_after_adds(self) -> None:
        clock = FakeClock()
        window = RollingWindow(window_seconds=60.0, clock=clock)
        window.add(1)
        window.add(5)
        assert window.total() == 6

    def test_evicts_old_events(self) -> None:
        clock = FakeClock()
        window = RollingWindow(window_seconds=60.0, clock=clock)
        window.add(10)
        clock.advance(30)
        window.add(5)
        clock.advance(31)  # first event is now > 60s old
        assert window.total() == 5

    def test_seconds_until_next_slot_empty(self) -> None:
        clock = FakeClock()
        window = RollingWindow(window_seconds=60.0, clock=clock)
        assert window.seconds_until_next_slot() == 0.0

    def test_seconds_until_next_slot_recent_event(self) -> None:
        clock = FakeClock()
        window = RollingWindow(window_seconds=60.0, clock=clock)
        window.add(1)
        clock.advance(10)
        assert window.seconds_until_next_slot() == pytest.approx(50.0)


class TestThrottler:
    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        reset_throttlers_for_tests()

    @pytest.mark.asyncio
    async def test_acquire_no_op_for_non_albert(self) -> None:
        provider = _make_provider("mistral")
        throttler = Throttler(provider)
        slept = await throttler.acquire()
        assert slept == 0.0

    @pytest.mark.asyncio
    async def test_acquire_no_op_when_quotas_unavailable(
        self, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "secret")
        respx_mock.get("http://test/v1/me/info").mock(
            return_value=httpx.Response(500, json={"error": "boom"})
        )
        respx_mock.get("http://test/v1/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        throttler = Throttler(_make_provider())
        slept = await throttler.acquire()
        assert slept == 0.0

    @pytest.mark.asyncio
    async def test_acquire_sleeps_when_rpm_threshold_reached(
        self, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "secret")
        respx_mock.get("http://test/v1/me/info").mock(
            return_value=httpx.Response(
                200, json={"limits": [{"router": 0, "type": "rpm", "value": 10}]}
            )
        )
        respx_mock.get("http://test/v1/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        clock = FakeClock()
        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            clock.advance(seconds)

        throttler = Throttler(
            _make_provider(), threshold=0.8, clock=clock, sleep=fake_sleep
        )

        # Saturate the window: 8 calls = exactly the 80% threshold
        for _ in range(8):
            throttler.record_request()

        slept = await throttler.acquire()
        assert sleep_calls, "expected at least one sleep call"
        assert slept > 0.0

    @pytest.mark.asyncio
    async def test_acquire_skips_sleep_below_threshold(
        self, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "secret")
        respx_mock.get("http://test/v1/me/info").mock(
            return_value=httpx.Response(
                200, json={"limits": [{"router": 0, "type": "rpm", "value": 100}]}
            )
        )
        respx_mock.get("http://test/v1/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        throttler = Throttler(_make_provider(), sleep=fake_sleep)
        for _ in range(5):
            throttler.record_request()

        slept = await throttler.acquire()
        assert slept == 0.0
        assert sleep_calls == []

    @pytest.mark.asyncio
    async def test_records_token_usage(
        self, monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
    ) -> None:
        monkeypatch.setenv("TEST_KEY", "secret")
        respx_mock.get("http://test/v1/me/info").mock(
            return_value=httpx.Response(
                200, json={"limits": [{"router": 0, "type": "tpm", "value": 100}]}
            )
        )
        respx_mock.get("http://test/v1/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        clock = FakeClock()
        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            clock.advance(seconds)

        throttler = Throttler(_make_provider(), clock=clock, sleep=fake_sleep)

        await throttler.acquire()

        # 90 tokens = 90% of 100 -> above 80% threshold
        throttler.record_request(prompt_tokens=60, completion_tokens=30)

        await throttler.acquire()
        assert sleep_calls, "expected throttling on tokens"

    def test_get_throttler_returns_singleton(self) -> None:
        p1 = _make_provider("albert")
        p2 = _make_provider("albert")
        assert get_throttler(p1) is get_throttler(p2)

    def test_get_throttler_per_provider(self) -> None:
        a = get_throttler(_make_provider("albert"))
        b = get_throttler(_make_provider("mistral"))
        assert a is not b


class TestThrottlerAutoFallback:
    """Two consecutive 429 must arm the auto-fallback for the model;
    a successful call must reset the counter; an inactive provider must
    never fall back; the fallback expires after FALLBACK_DURATION_SECONDS.
    """

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        reset_throttlers_for_tests()

    def test_one_429_does_not_trigger_fallback(self) -> None:
        clock = FakeClock()
        throttler = Throttler(_make_provider(), clock=clock)
        throttler.record_rate_limit(model_alias="albert-code")
        assert throttler.should_fallback("albert-code") is False

    def test_two_429_trigger_fallback(self) -> None:
        clock = FakeClock()
        throttler = Throttler(_make_provider(), clock=clock)
        throttler.record_rate_limit(model_alias="albert-code")
        throttler.record_rate_limit(model_alias="albert-code")
        assert throttler.should_fallback("albert-code") is True

    def test_fallback_only_for_failing_model(self) -> None:
        clock = FakeClock()
        throttler = Throttler(_make_provider(), clock=clock)
        throttler.record_rate_limit(model_alias="albert-code")
        throttler.record_rate_limit(model_alias="albert-code")
        assert throttler.should_fallback("albert-code") is True
        assert throttler.should_fallback("albert-large") is False

    def test_success_resets_counter(self) -> None:
        clock = FakeClock()
        throttler = Throttler(_make_provider(), clock=clock)
        throttler.record_rate_limit(model_alias="albert-code")
        throttler.record_success(model_alias="albert-code")
        throttler.record_rate_limit(model_alias="albert-code")
        # Only one consecutive 429 left after the reset
        assert throttler.should_fallback("albert-code") is False

    def test_fallback_expires_after_duration(self) -> None:
        clock = FakeClock()
        throttler = Throttler(_make_provider(), clock=clock)
        throttler.record_rate_limit(model_alias="albert-code")
        throttler.record_rate_limit(model_alias="albert-code")
        assert throttler.should_fallback("albert-code") is True

        clock.advance(61.0)
        assert throttler.should_fallback("albert-code") is False

    def test_fallback_remaining_seconds(self) -> None:
        clock = FakeClock()
        throttler = Throttler(_make_provider(), clock=clock)
        throttler.record_rate_limit(model_alias="albert-code")
        throttler.record_rate_limit(model_alias="albert-code")
        throttler.should_fallback("albert-code")  # arm
        assert throttler.fallback_remaining_seconds("albert-code") == pytest.approx(
            60.0
        )
        clock.advance(20.0)
        assert throttler.fallback_remaining_seconds("albert-code") == pytest.approx(
            40.0
        )


class TestThrottlerLimitType:
    """`record_rate_limit` accepts an optional `limit_type` ("tpm" / "rpm"
    / "tpd" / "rpd") so the agent loop can name the tripped quota when
    arming the auto-fallback. This suite locks in storage, retrieval, and
    cleanup semantics.
    """

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        reset_throttlers_for_tests()

    def test_record_then_read_back(self) -> None:
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias="albert-code", limit_type="tpm")
        assert throttler.last_limit_type("albert-code") == "tpm"

    def test_unknown_alias_returns_none(self) -> None:
        throttler = Throttler(_make_provider(), clock=FakeClock())
        assert throttler.last_limit_type("never-seen") is None

    def test_omitting_limit_type_does_not_store(self) -> None:
        # Backward compat: existing call sites that don't pass limit_type
        # must not poison the dict (would surface as a stale type from a
        # previous 429 in the worst case, but here it stays None).
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias="albert-code")
        assert throttler.last_limit_type("albert-code") is None

    def test_record_success_clears_limit_type(self) -> None:
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias="albert-code", limit_type="tpd")
        throttler.record_success(model_alias="albert-code")
        assert throttler.last_limit_type("albert-code") is None

    def test_latest_value_wins(self) -> None:
        # Two consecutive 429 with different quota types - the agent loop
        # arms the fallback after the second; the user should see the
        # most recent quota that tripped.
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias="albert-code", limit_type="tpm")
        throttler.record_rate_limit(model_alias="albert-code", limit_type="rpm")
        assert throttler.last_limit_type("albert-code") == "rpm"

    def test_per_model_isolation(self) -> None:
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias="albert-code", limit_type="tpm")
        throttler.record_rate_limit(model_alias="albert-large", limit_type="rpd")
        assert throttler.last_limit_type("albert-code") == "tpm"
        assert throttler.last_limit_type("albert-large") == "rpd"


_QWEN = "Qwen/Qwen3-Coder-30B-A3B-Instruct"


class TestThrottlerSaturateOn429:
    """A 429 with a tpm/rpm reason saturates the matching rolling window
    so the bottom-bar gauge reflects what the server saw. Daily quota
    limits (tpd/rpd) live in /v1/me/usage and are NOT touched here.
    """

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        reset_throttlers_for_tests()

    def test_tpm_429_saturates_token_window(self) -> None:
        # Qwen documented EXP tier: tpm = 128_000.
        throttler = Throttler(_make_provider(), clock=FakeClock())
        snap_before = throttler.usage_snapshot(model_name=_QWEN)
        assert snap_before.tpm_used == 0
        throttler.record_rate_limit(model_alias=_QWEN, limit_type="tpm")
        snap_after = throttler.usage_snapshot(model_name=_QWEN)
        assert snap_after.tpm_used == 128_000
        # rpm is untouched.
        assert snap_after.rpm_used == 0

    def test_rpm_429_saturates_request_window(self) -> None:
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias=_QWEN, limit_type="rpm")
        snap = throttler.usage_snapshot(model_name=_QWEN)
        assert snap.rpm_used == 50  # Qwen EXP rpm
        assert snap.tpm_used == 0

    def test_tpd_429_does_not_touch_rolling_windows(self) -> None:
        # Daily quotas surface via /v1/me/usage; the rolling 60s window
        # is irrelevant for them. We must not poison the gauge with a
        # tpd 429.
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias=_QWEN, limit_type="tpd")
        snap = throttler.usage_snapshot(model_name=_QWEN)
        assert snap.tpm_used == 0
        assert snap.rpm_used == 0

    def test_saturation_decays_with_rolling_window(self) -> None:
        # The injected events sit in the rolling window like real usage,
        # so they fade naturally as the 60s window slides — mirroring
        # the server's per-minute bucket draining.
        clock = FakeClock()
        throttler = Throttler(_make_provider(), clock=clock)
        throttler.record_rate_limit(model_alias=_QWEN, limit_type="tpm")
        assert throttler.usage_snapshot(model_name=_QWEN).tpm_used == 128_000
        clock.advance(61.0)
        assert throttler.usage_snapshot(model_name=_QWEN).tpm_used == 0

    def test_no_saturation_when_limit_unknown(self) -> None:
        # Unknown model + uninitialised account-wide _tpm => nothing to
        # saturate against; must stay quiet rather than crash.
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(
            model_alias="completely-unknown-model", limit_type="tpm"
        )
        snap = throttler.usage_snapshot(model_name="completely-unknown-model")
        assert snap.tpm_used == 0


_GPT_OSS = "openai/gpt-oss-120b"


class TestThrottlerPerModelWindows:
    """The rolling rpm/tpm windows are split per canonical model id so a
    model switch (manual via /config or auto-fallback) doesn't mix the
    old model's recent traffic into the new model's gauge — that bug
    used to surface as "tpm 100k/128k" right after switching to a fresh
    model that had made no calls yet.
    """

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        reset_throttlers_for_tests()

    def test_record_request_isolated_per_model(self) -> None:
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_request(
            prompt_tokens=10_000, completion_tokens=200, model_name=_QWEN
        )
        qwen = throttler.usage_snapshot(model_name=_QWEN)
        gpt = throttler.usage_snapshot(model_name=_GPT_OSS)
        assert qwen.tpm_used == 10_200
        assert qwen.rpm_used == 1
        assert gpt.tpm_used == 0
        assert gpt.rpm_used == 0

    def test_429_saturation_isolated_per_model(self) -> None:
        # A 429 on Qwen must not poison gpt-oss-120b's gauge.
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler.record_rate_limit(model_alias=_QWEN, limit_type="tpm")
        assert throttler.usage_snapshot(model_name=_QWEN).tpm_used == 128_000
        assert throttler.usage_snapshot(model_name=_GPT_OSS).tpm_used == 0

    def test_alias_resolves_to_same_window_as_canonical(self) -> None:
        # Calls via the alias and via the canonical id must share a
        # single window, otherwise the gauge would split a single
        # model's traffic across two buckets.
        throttler = Throttler(_make_provider(), clock=FakeClock())
        throttler._alias_to_canonical = {"openweight-code": _QWEN}
        throttler.record_request(
            prompt_tokens=5_000, completion_tokens=0, model_name="openweight-code"
        )
        throttler.record_request(
            prompt_tokens=3_000, completion_tokens=0, model_name=_QWEN
        )
        snap = throttler.usage_snapshot(model_name=_QWEN)
        assert snap.tpm_used == 8_000
        assert snap.rpm_used == 2
