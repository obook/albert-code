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
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from albert_code.core.config import ProviderConfig

logger = logging.getLogger(__name__)

ALBERT_PROVIDER_NAME = "albert"
ALBERT_INFO_PATH = "/me/info"


class RouterLimit(BaseModel):
    """One quota row from /v1/me/info."""

    model_config = {"extra": "ignore"}

    router: int
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


def group_limits_by_router(
    limits: list[RouterLimit],
) -> dict[int, dict[str, int | None]]:
    """Pivot the flat limits list into {router_id: {type: value}}."""
    routers: dict[int, dict[str, int | None]] = {}
    for limit in limits:
        routers.setdefault(limit.router, {})[limit.type] = limit.value
    return routers
