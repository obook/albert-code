"""Albert API quota fetching.

Albert exposes per-router quotas (rpm/rpd/tpm/tpd) at GET /v1/me/info.
This module fetches and parses them so the UI and the future throttler
can react.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, NamedTuple

import httpx
from pydantic import AliasChoices, BaseModel, Field, field_validator

if TYPE_CHECKING:
    from albert_code.core.config import ProviderConfig

logger = logging.getLogger(__name__)

ALBERT_PROVIDER_NAME = "albert"
ALBERT_INFO_PATH = "/me/info"


class RouterLimit(BaseModel):
    """One quota row from /v1/me/info."""

    # Albert renamed `router` -> `router_id` in /v1/me/info; accept both so
    # the parser stays compatible with old and new server versions.
    model_config = {"extra": "ignore", "populate_by_name": True}

    router: int = Field(validation_alias=AliasChoices("router", "router_id"))
    type: str
    value: int | None = None


class AlbertAccountInfo(BaseModel):
    """Subset of /v1/me/info we care about."""

    model_config = {"extra": "ignore"}

    # Albert may serialize `id` as either str or int depending on the user kind.
    # We coerce to str at parse time so the rest of the code sees a uniform type.
    name: str | None = None
    email: str | None = None
    id: str | None = None
    limits: list[RouterLimit] = Field(default_factory=list)

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id_to_str(cls, value: object) -> str | None:
        if value is None:
            return None
        return str(value)


class QuotaFetchResult(NamedTuple):
    info: AlbertAccountInfo | None
    error: str | None


def is_albert_provider(provider: ProviderConfig) -> bool:
    return provider.name == ALBERT_PROVIDER_NAME


def midnight_utc_timestamp() -> int:
    """Today's 00:00 UTC as a Unix timestamp.

    Albert daily quotas (rpd/tpd) reset at this boundary, so the tpd/rpd
    gauges only need events past this point.
    """
    import datetime as dt

    return int(
        dt.datetime
        .now(dt.UTC)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )


# Server-imposed page size cap (see /v1/me/usage OpenAPI schema). Higher
# values are rejected with 422.
_USAGE_PAGE_LIMIT = 100
# Hard ceiling on the number of pages we'll fetch, to prevent a runaway
# loop if the server ever stops honouring the "fewer rows than limit
# means last page" convention. 100 pages * 100 rows = 10 000 events,
# more than enough for one day at the documented EXP tier (1000 rpd).
_USAGE_MAX_PAGES = 100


async def fetch_albert_usage(
    provider: ProviderConfig,
    *,
    since_timestamp: int | None = None,
    timeout: float = 10.0,
) -> list[dict[str, object]] | None:
    """Fetch /v1/me/usage. Returns the list of usage events, or None on failure.

    Albert returns `{object: "list", data: [...]}` with a default page
    size of 10 (cap 100). When `since_timestamp` is provided, we pass it
    as `start_time` and paginate via `offset` until the server returns a
    short page — this is required for the tpd/rpd gauges to be accurate
    once the user has done more than 10 calls in the day. Without
    `since_timestamp` the function keeps its legacy single-page
    behaviour for back-compat.
    """
    if _check_albert_preconditions(provider) is not None:
        return None
    api_key = os.getenv(provider.api_key_env_var) or ""
    url = f"{provider.api_base.rstrip('/')}/me/usage"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    all_events: list[dict[str, object]] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            offset = 0
            for _ in range(_USAGE_MAX_PAGES):
                params: dict[str, int] = {"limit": _USAGE_PAGE_LIMIT, "offset": offset}
                if since_timestamp is not None:
                    params["start_time"] = since_timestamp
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(data, list):
                    return None
                all_events.extend(data)
                if since_timestamp is None or len(data) < _USAGE_PAGE_LIMIT:
                    return all_events
                offset += len(data)
            logger.warning(
                "Albert /me/usage: pagination hit safety cap (%d pages)",
                _USAGE_MAX_PAGES,
            )
            return all_events
    except httpx.HTTPError as exc:
        logger.debug("Albert /me/usage fetch failed: %s", exc)
        return None
    except ValueError as exc:
        logger.debug("Albert /me/usage returned non-JSON: %s", exc)
        return None


def sum_prompt_tokens_today(
    usage_events: list[dict[str, object]], model_name: str
) -> int:
    """Sum prompt_tokens for `model_name` calls that happened today (UTC).

    Daily quotas reset at midnight UTC, so any event before today's
    00:00 UTC doesn't consume the running counter.
    """
    midnight_utc = midnight_utc_timestamp()
    total = 0
    for event in usage_events:
        if not isinstance(event, dict):
            continue
        if event.get("model") != model_name:
            continue
        created = event.get("created")
        if not isinstance(created, (int, float)) or created < midnight_utc:
            continue
        usage = event.get("usage") or {}
        if isinstance(usage, dict):
            tokens = usage.get("prompt_tokens", 0)
            if isinstance(tokens, (int, float)):
                total += int(tokens)
    return total


def count_requests_today(usage_events: list[dict[str, object]], model_name: str) -> int:
    """Count `model_name` calls that happened today (UTC).

    Mirror of `sum_prompt_tokens_today` for the rpd (requests per day)
    counter: each event past midnight UTC counts for one request.
    """
    midnight_utc = midnight_utc_timestamp()
    count = 0
    for event in usage_events:
        if not isinstance(event, dict):
            continue
        if event.get("model") != model_name:
            continue
        created = event.get("created")
        if not isinstance(created, (int, float)) or created < midnight_utc:
            continue
        count += 1
    return count


async def fetch_albert_quotas_detailed(
    provider: ProviderConfig, *, timeout: float = 10.0
) -> QuotaFetchResult:
    """Fetch /v1/me/info, returning (info, None) on success or (None, reason) on failure."""
    precondition_error = _check_albert_preconditions(provider)
    if precondition_error is not None:
        return QuotaFetchResult(None, precondition_error)

    api_key = os.getenv(provider.api_key_env_var) or ""
    url = f"{provider.api_base.rstrip('/')}{ALBERT_INFO_PATH}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            info = AlbertAccountInfo.model_validate(response.json())
            return QuotaFetchResult(info, None)
    except httpx.HTTPStatusError as e:
        body_excerpt = e.response.text[:200] if e.response.text else ""
        suffix = f" (body: {body_excerpt!r})" if body_excerpt else ""
        return QuotaFetchResult(
            None, f"HTTP {e.response.status_code} on GET {url}{suffix}"
        )
    except httpx.HTTPError as e:
        return QuotaFetchResult(None, f"network error on GET {url}: {e}")
    except ValueError as e:
        return QuotaFetchResult(None, f"invalid JSON from {url}: {e}")


def _check_albert_preconditions(provider: ProviderConfig) -> str | None:
    """Return None if quota fetch can proceed, else a human-readable error."""
    if not is_albert_provider(provider):
        return f"provider '{provider.name}' is not Albert"
    if not provider.api_key_env_var:
        return "provider has no api_key_env_var configured"
    if not os.getenv(provider.api_key_env_var):
        return f"environment variable {provider.api_key_env_var} is empty or unset"
    return None


async def fetch_albert_quotas(
    provider: ProviderConfig, *, timeout: float = 10.0
) -> AlbertAccountInfo | None:
    """Fetch /v1/me/info. Returns None on any failure (silent variant)."""
    info, error = await fetch_albert_quotas_detailed(provider, timeout=timeout)
    if error is not None:
        logger.debug("Albert quota fetch failed: %s", error)
    return info


async def fetch_albert_aliases(
    provider: ProviderConfig, *, timeout: float = 5.0
) -> dict[str, str] | None:
    """Fetch /v1/models and build an `{alias: canonical_id}` map.

    Albert publishes server-side aliases (e.g. `openweight-code` ->
    `Qwen/Qwen3-Coder-30B-A3B-Instruct`) in the `aliases` field of each
    model entry. Resolving them client-side lets the throttler apply
    per-model limits and lets the daily usage poller match events
    (which always carry the canonical id, not the alias).

    Returns None on any failure (silent: the rest of the system keeps
    working with the alias as opaque, just without per-model tiering).
    """
    if _check_albert_preconditions(provider) is not None:
        return None
    api_key = os.getenv(provider.api_key_env_var) or ""
    url = f"{provider.api_base.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        logger.debug("Albert /v1/models fetch failed: %s", exc)
        return None
    except ValueError as exc:
        logger.debug("Albert /v1/models returned non-JSON: %s", exc)
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return None
    mapping: dict[str, str] = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        canonical = entry.get("id")
        if not isinstance(canonical, str) or not canonical:
            continue
        for alias in entry.get("aliases") or []:
            if isinstance(alias, str) and alias:
                mapping[alias] = canonical
    return mapping


def group_limits_by_router(
    limits: list[RouterLimit],
) -> dict[int, dict[str, int | None]]:
    """Pivot the flat limits list into {router_id: {type: value}}."""
    routers: dict[int, dict[str, int | None]] = {}
    for limit in limits:
        routers.setdefault(limit.router, {})[limit.type] = limit.value
    return routers


class DocumentedTier(NamedTuple):
    rpm: int | None
    rpd: int | None
    tpm: int | None
    tpd: int | None


class DocumentedLimits(NamedTuple):
    exp: DocumentedTier
    prod: DocumentedTier


# Documented Albert tiers per model family. Hardcoded from the public docs
# (https://albert.sites.beta.gouv.fr/prices/). Kept as a reference shown next
# to the live /v1/me/info data: useful to know whether your account matches
# EXP or PROD, and to spot discrepancies. None means "unlimited per docs".
DOCUMENTED_MODEL_LIMITS: dict[str, DocumentedLimits] = {
    "openai/gpt-oss-120b": DocumentedLimits(
        exp=DocumentedTier(rpm=10, rpd=1_000, tpm=128_000, tpd=1_280_000),
        prod=DocumentedTier(rpm=50, rpd=5_000, tpm=246_000, tpd=None),
    ),
    "Qwen/Qwen3-Coder-30B-A3B-Instruct": DocumentedLimits(
        exp=DocumentedTier(rpm=50, rpd=1_000, tpm=128_000, tpd=2_460_000),
        prod=DocumentedTier(rpm=100, rpd=50_000, tpm=246_000, tpd=None),
    ),
    "mistralai/mistral-small-3.2-24b-instruct-2506": DocumentedLimits(
        exp=DocumentedTier(rpm=50, rpd=1_000, tpm=128_000, tpd=2_460_000),
        prod=DocumentedTier(rpm=100, rpd=50_000, tpm=246_000, tpd=None),
    ),
    "mistralai/ministral-3-8b-instruct-2512": DocumentedLimits(
        exp=DocumentedTier(rpm=50, rpd=1_000, tpm=128_000, tpd=2_460_000),
        prod=DocumentedTier(rpm=100, rpd=50_000, tpm=246_000, tpd=None),
    ),
}


def documented_limits_for(model_name: str) -> DocumentedLimits | None:
    """Lookup with case-insensitive match; returns None if model is unknown."""
    if model_name in DOCUMENTED_MODEL_LIMITS:
        return DOCUMENTED_MODEL_LIMITS[model_name]
    lowered = model_name.lower()
    for known, tiers in DOCUMENTED_MODEL_LIMITS.items():
        if known.lower() == lowered:
            return tiers
    return None
