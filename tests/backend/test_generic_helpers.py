from __future__ import annotations

import pytest

from albert_code.core.llm.backend.generic import parse_limit_type


class TestParseLimitType:
    """`parse_limit_type` extracts the quota family from a 429 body so the
    auto-fallback chat message can name which limit tripped. The function
    is regex-based and fragile by nature: this suite locks in the wordings
    Albert is known to use, plus the precedence rules that prevent
    "tokens per day" from being misclassified as `tpm`.
    """

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("Server: 128000 input tokens per minute exceeded (remaining: 0).", "tpm"),
            ("Server: 50 requests per minute exceeded (remaining: 0).", "rpm"),
            ("Server: 2460000 input tokens per day exceeded (remaining: 0).", "tpd"),
            ("Server: 5000 requests per day exceeded (remaining: 0).", "rpd"),
        ],
    )
    def test_recognises_albert_wordings(self, body: str, expected: str) -> None:
        assert parse_limit_type(body) == expected

    def test_returns_none_on_empty_body(self) -> None:
        assert parse_limit_type("") is None

    def test_returns_none_when_no_quota_keyword(self) -> None:
        # If Albert ever changes the wording, the fallback chat message
        # will still render correctly - just without the "(tpm: ...)"
        # suffix - rather than crashing.
        assert parse_limit_type("Quota exceeded.") is None
        assert parse_limit_type("HTTP 429 Too Many Requests") is None

    def test_per_day_takes_precedence_over_per_minute(self) -> None:
        # The substring "tokens per minute" doesn't appear in "tokens per
        # day", but the order of checks matters if both keywords coexist
        # in a future composite message. Lock in tpd-before-tpm.
        body = (
            "Daily and per-minute limits: 1000 tokens per day, 100 tokens per minute."
        )
        assert parse_limit_type(body) == "tpd"

    def test_case_insensitive(self) -> None:
        assert parse_limit_type("TOKENS PER MINUTE EXCEEDED") == "tpm"
        assert parse_limit_type("Requests Per Day Exceeded") == "rpd"
