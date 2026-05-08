from __future__ import annotations

import httpx
import pytest
import respx

from albert_code.core.config import Backend, ProviderConfig
from albert_code.core.llm.quota import (
    AlbertAccountInfo,
    RouterLimit,
    fetch_albert_quotas,
    fetch_albert_quotas_detailed,
    group_limits_by_router,
    is_albert_provider,
)


def _make_provider(name: str = "albert") -> ProviderConfig:
    return ProviderConfig(
        name=name,
        api_base="http://test/v1",
        api_key_env_var="TEST_ALBERT_KEY",
        api_style="openai",
        backend=Backend.GENERIC,
    )


def test_is_albert_provider_true() -> None:
    assert is_albert_provider(_make_provider("albert")) is True


def test_is_albert_provider_false() -> None:
    assert is_albert_provider(_make_provider("mistral")) is False


def test_group_limits_by_router_pivots_correctly() -> None:
    limits = [
        RouterLimit(router=0, type="rpm", value=60),
        RouterLimit(router=0, type="tpm", value=10_000),
        RouterLimit(router=1, type="rpm", value=120),
        RouterLimit(router=1, type="rpd", value=None),
    ]
    grouped = group_limits_by_router(limits)
    assert grouped == {0: {"rpm": 60, "tpm": 10_000}, 1: {"rpm": 120, "rpd": None}}


def test_group_limits_by_router_empty() -> None:
    assert group_limits_by_router([]) == {}


def test_account_info_validates_full_payload() -> None:
    info = AlbertAccountInfo.model_validate({
        "name": "Alice",
        "email": "alice@example.gouv.fr",
        "id": "user-123",
        "limits": [
            {"router": 0, "type": "rpm", "value": 60},
            {"router": 0, "type": "tpd", "value": None},
        ],
    })
    assert info.name == "Alice"
    assert len(info.limits) == 2
    assert info.limits[0].value == 60
    assert info.limits[1].value is None


def test_account_info_validates_minimal_payload() -> None:
    info = AlbertAccountInfo.model_validate({})
    assert info.name is None
    assert info.limits == []


def test_account_info_accepts_router_id_alias() -> None:
    # Albert renamed `router` to `router_id` in /v1/me/info; both shapes
    # must continue to parse so the throttler keeps working across the
    # server-side rollout.
    info = AlbertAccountInfo.model_validate({
        "limits": [
            {"router_id": 342, "type": "rpm", "value": 500},
            {"router_id": 342, "type": "tpm", "value": None},
        ],
    })
    assert len(info.limits) == 2
    assert info.limits[0].router == 342
    assert info.limits[0].type == "rpm"
    assert info.limits[0].value == 500
    assert info.limits[1].value is None


@pytest.mark.asyncio
async def test_fetch_albert_quotas_returns_none_for_non_albert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_ALBERT_KEY", "secret")
    provider = _make_provider("mistral")
    assert await fetch_albert_quotas(provider) is None


@pytest.mark.asyncio
async def test_fetch_albert_quotas_returns_none_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_ALBERT_KEY", raising=False)
    provider = _make_provider()
    assert await fetch_albert_quotas(provider) is None


@pytest.mark.asyncio
async def test_fetch_albert_quotas_parses_response(
    monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    monkeypatch.setenv("TEST_ALBERT_KEY", "secret-token")
    route = respx_mock.get("http://test/v1/me/info").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Bob",
                "email": "bob@example.gouv.fr",
                "id": "user-42",
                "limits": [
                    {"router": 0, "type": "rpm", "value": 60},
                    {"router": 0, "type": "tpm", "value": 50_000},
                ],
            },
        )
    )

    info = await fetch_albert_quotas(_make_provider())

    assert route.called
    assert info is not None
    assert info.name == "Bob"
    assert len(info.limits) == 2
    assert info.limits[0].router == 0
    assert info.limits[0].type == "rpm"
    assert info.limits[0].value == 60
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer secret-token"


@pytest.mark.asyncio
async def test_fetch_albert_quotas_returns_none_on_http_error(
    monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    monkeypatch.setenv("TEST_ALBERT_KEY", "secret")
    respx_mock.get("http://test/v1/me/info").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )
    assert await fetch_albert_quotas(_make_provider()) is None


@pytest.mark.asyncio
async def test_fetch_albert_quotas_returns_none_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    monkeypatch.setenv("TEST_ALBERT_KEY", "secret")
    respx_mock.get("http://test/v1/me/info").mock(
        return_value=httpx.Response(200, content=b"not json")
    )
    assert await fetch_albert_quotas(_make_provider()) is None


@pytest.mark.asyncio
async def test_fetch_albert_quotas_detailed_explains_non_albert() -> None:
    info, error = await fetch_albert_quotas_detailed(_make_provider("mistral"))
    assert info is None
    assert error is not None
    assert "mistral" in error


@pytest.mark.asyncio
async def test_fetch_albert_quotas_detailed_explains_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEST_ALBERT_KEY", raising=False)
    info, error = await fetch_albert_quotas_detailed(_make_provider())
    assert info is None
    assert error is not None
    assert "TEST_ALBERT_KEY" in error


@pytest.mark.asyncio
async def test_fetch_albert_quotas_detailed_explains_http_error(
    monkeypatch: pytest.MonkeyPatch, respx_mock: respx.MockRouter
) -> None:
    monkeypatch.setenv("TEST_ALBERT_KEY", "secret")
    respx_mock.get("http://test/v1/me/info").mock(
        return_value=httpx.Response(404, json={"detail": "Not Found"})
    )
    info, error = await fetch_albert_quotas_detailed(_make_provider())
    assert info is None
    assert error is not None
    assert "404" in error
