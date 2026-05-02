"""Adaptive client-side throttling for the Albert API.

Albert exposes per-router quotas (rpm/rpd/tpm/tpd) at /v1/me/info. This
module fetches them once and slows requests down before we hit the
limit, instead of relying solely on 429 responses.

Inspired by the double-debounce in `albert-ext`
(`sources-firefox/verification/albert-debounce.js`), adapted for an
agent context: we throttle at the request boundary (not on key strokes).

Strategy (v1):
  - Maintain rolling 60s windows for requests and tokens.
  - Before each call: if `count_last_minute >= limit * THRESHOLD`,
    wait until the oldest event drops out of the window.
  - After each call: record the request and its token usage.

Out of scope here (v2):
  - Reading Retry-After on 429.
  - Surfacing throttling state to the UI.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
import logging
import time
from typing import TYPE_CHECKING

from albert_code.core.llm.quota import (
    RouterLimit,
    fetch_albert_quotas,
    is_albert_provider,
)

if TYPE_CHECKING:
    from albert_code.core.config import ProviderConfig

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60.0
THROTTLE_THRESHOLD = 0.8

# Auto-fallback parameters
FALLBACK_TRIGGER_429_COUNT = 2  # consecutive 429 needed to switch
FALLBACK_DURATION_SECONDS = 60.0  # how long the fallback stays in effect


class RollingWindow:
    """Counter of events within a rolling time window."""

    def __init__(
        self,
        window_seconds: float = WINDOW_SECONDS,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window = window_seconds
        self._clock = clock
        self._events: deque[tuple[float, int]] = deque()

    def add(self, count: int = 1) -> None:
        self._events.append((self._clock(), count))

    def total(self) -> int:
        self._evict()
        return sum(count for _, count in self._events)

    def seconds_until_next_slot(self) -> float:
        """How long to wait for the oldest event to drop out of the window."""
        self._evict()
        if not self._events:
            return 0.0
        oldest_ts, _ = self._events[0]
        return max(0.0, oldest_ts + self._window - self._clock())

    def _evict(self) -> None:
        cutoff = self._clock() - self._window
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()


class Throttler:
    """Per-provider throttler.

    Limits are loaded lazily on first `acquire()` from /v1/me/info. If
    fetching fails, throttling is disabled (the agent will rely on 429
    handling instead).
    """

    def __init__(
        self,
        provider: ProviderConfig,
        *,
        threshold: float = THROTTLE_THRESHOLD,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._provider = provider
        self._threshold = threshold
        self._clock = clock
        self._sleep = sleep or asyncio.sleep
        self._requests = RollingWindow(clock=clock)
        self._tokens = RollingWindow(clock=clock)
        self._rate_limit_events = RollingWindow(clock=clock)
        self._rpm: int | None = None
        self._tpm: int | None = None
        self._initialized = False
        # Per-primary-model auto-fallback state.
        self._consecutive_429_per_model: dict[str, int] = {}
        # primary_alias -> fallback active until (monotonic seconds, 0 if inactive)
        self._fallback_until: dict[str, float] = {}

    async def acquire(self, *, estimated_prompt_tokens: int = 0) -> float:
        """Wait until headroom is available. Returns total seconds slept."""
        await self._ensure_initialized()
        slept_total = 0.0
        while True:
            wait = self._compute_wait(estimated_prompt_tokens)
            if wait <= 0.0:
                return slept_total
            logger.info(
                "Albert throttling: sleeping %.2fs (rpm=%s/%s, tpm=%s/%s)",
                wait,
                self._requests.total(),
                self._rpm,
                self._tokens.total(),
                self._tpm,
            )
            await self._sleep(wait)
            slept_total += wait

    def record_request(
        self, *, prompt_tokens: int = 0, completion_tokens: int = 0
    ) -> None:
        self._requests.add(1)
        used = max(0, prompt_tokens) + max(0, completion_tokens)
        if used:
            self._tokens.add(used)

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        if not is_albert_provider(self._provider):
            return
        info = await fetch_albert_quotas(self._provider)
        if info is None:
            logger.debug("Throttler: no quotas available for %s", self._provider.name)
            return
        # We pick the highest positive rpm/tpm across routers (optimistic).
        # Albert's /v1/me/info returns one row per router (whisper, embeddings,
        # text models...) without telling us which router serves which model.
        # Picking the min would hold the agent back to the most restrictive
        # router (typically whisper at 10 rpm), which is wrong for text models.
        # We rely on 429 + Retry-After (record_rate_limit) as a safety net.
        self._rpm = _max_positive(info.limits, "rpm")
        self._tpm = _max_positive(info.limits, "tpm")
        logger.info(
            "Throttler initialized for %s: rpm=%s tpm=%s",
            self._provider.name,
            self._rpm,
            self._tpm,
        )

    def record_rate_limit(self, *, model_alias: str | None = None) -> None:
        """Called when the upstream returned 429.

        Logs, increments the rolling 429 window, and bumps the consecutive
        counter for the target model. Reaching FALLBACK_TRIGGER_429_COUNT
        arms the auto-fallback (queried by `should_fallback`).
        """
        self._rate_limit_events.add(1)
        recent = self._rate_limit_events.total()
        logger.warning("Rate-limited (429); recent 429 in last 60s: %d", recent)
        if model_alias is None:
            return
        self._consecutive_429_per_model[model_alias] = (
            self._consecutive_429_per_model.get(model_alias, 0) + 1
        )

    def record_success(self, *, model_alias: str | None = None) -> None:
        """Reset the consecutive-429 counter after a successful call."""
        if model_alias is None:
            return
        self._consecutive_429_per_model.pop(model_alias, None)

    def should_fallback(self, primary_alias: str) -> bool:
        """Return True if the primary model has hit the auto-fallback trigger
        recently and the fallback window is still open.
        """
        until = self._fallback_until.get(primary_alias, 0.0)
        if until > self._clock():
            return True
        if (
            self._consecutive_429_per_model.get(primary_alias, 0)
            >= FALLBACK_TRIGGER_429_COUNT
        ):
            self._fallback_until[primary_alias] = (
                self._clock() + FALLBACK_DURATION_SECONDS
            )
            self._consecutive_429_per_model[primary_alias] = 0
            return True
        return False

    def fallback_remaining_seconds(self, primary_alias: str) -> float:
        """How long the active fallback for `primary_alias` still has to run."""
        until = self._fallback_until.get(primary_alias, 0.0)
        return max(0.0, until - self._clock())

    def _compute_wait(self, estimated_prompt_tokens: int) -> float:
        waits: list[float] = []
        if self._rpm is not None:
            ceiling = max(1, int(self._rpm * self._threshold))
            if self._requests.total() >= ceiling:
                waits.append(self._requests.seconds_until_next_slot())
        if self._tpm is not None:
            ceiling = max(1, int(self._tpm * self._threshold))
            projected = self._tokens.total() + max(0, estimated_prompt_tokens)
            if projected >= ceiling:
                waits.append(self._tokens.seconds_until_next_slot())
        return max(waits, default=0.0)


def _max_positive(limits: list[RouterLimit], kind: str) -> int | None:
    """Return the most permissive (largest positive) limit of a kind across routers.

    Albert's /v1/me/info doesn't tell which router serves which model, so we
    can't pick the limit for the active model. Choosing the maximum is
    optimistic; 429 + Retry-After acts as a safety net (see record_rate_limit).
    """
    values: list[int] = []
    for limit in limits:
        if limit.type != kind:
            continue
        if limit.value is None or limit.value <= 0:
            continue
        values.append(limit.value)
    return max(values) if values else None


_throttlers: dict[str, Throttler] = {}


def get_throttler(provider: ProviderConfig) -> Throttler:
    """Return the singleton throttler for this provider (creating it on first use)."""
    if provider.name not in _throttlers:
        _throttlers[provider.name] = Throttler(provider)
    return _throttlers[provider.name]


def reset_throttlers_for_tests() -> None:
    """Clear the singleton cache. Tests only."""
    _throttlers.clear()
