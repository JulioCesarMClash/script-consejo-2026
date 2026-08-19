"""Tests para value objects del dominio.

Cubre creación, validación, igualdad y serialización de cada value object:
MetricId, RunId, AttemptId, HashSha256, MetricSource, Cut, FetchStatus, RunState.
"""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.consejo.domain.value_objects import (
    TERMINAL_STATES,
    AttemptId,
    Cut,
    FetchStatus,
    HashSha256,
    MetricId,
    MetricSource,
    RunId,
    RunState,
    is_terminal_state,
)


# ── MetricId ────────────────────────────────────────────────────────────────


class TestMetricId:
    def test_create_valid(self) -> None:
        mid = MetricId("registered_cpe")
        assert mid.value == "registered_cpe"
        assert str(mid) == "registered_cpe"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="vacío"):
            MetricId("")

    def test_rejects_whitespace(self) -> None:
        with pytest.raises(ValueError, match="vacío"):
            MetricId("   ")

    def test_equality(self) -> None:
        a = MetricId("foo")
        b = MetricId("foo")
        c = MetricId("bar")
        assert a == b
        assert a != c
        assert hash(a) == hash(b)

    def test_str_returns_value(self) -> None:
        assert str(MetricId("test_key")) == "test_key"


# ── RunId ───────────────────────────────────────────────────────────────────


class TestRunId:
    def test_default_generates_v4(self) -> None:
        rid = RunId()
        assert isinstance(rid.value, UUID)
        assert rid.value.version == 4

    def test_accepts_uuid_arg(self) -> None:
        u = uuid4()
        rid = RunId(value=u)
        assert rid.value == u

    def test_accepts_string_uuid(self) -> None:
        u = uuid4()
        rid = RunId(value=str(u))
        assert rid.value == u

    def test_rejects_non_v4(self) -> None:
        with pytest.raises(ValueError, match="UUID v4"):
            RunId(value=UUID("00000000-0000-0000-0000-000000000000"))

    def test_generate_classmethod(self) -> None:
        rid = RunId.generate()
        assert rid.value.version == 4

    def test_equality(self) -> None:
        u = uuid4()
        a = RunId(value=u)
        b = RunId(value=u)
        assert a == b
        assert hash(a) == hash(b)

    def test_str_returns_uuid_string(self) -> None:
        u = uuid4()
        assert str(RunId(value=u)) == str(u)


# ── AttemptId ───────────────────────────────────────────────────────────────


class TestAttemptId:
    def test_default_generates_v4(self) -> None:
        aid = AttemptId()
        assert isinstance(aid.value, UUID)
        assert aid.value.version == 4

    def test_accepts_uuid_arg(self) -> None:
        u = uuid4()
        aid = AttemptId(value=u)
        assert aid.value == u

    def test_accepts_string_uuid(self) -> None:
        u = uuid4()
        aid = AttemptId(value=str(u))
        assert aid.value == u

    def test_rejects_non_v4(self) -> None:
        with pytest.raises(ValueError, match="UUID v4"):
            AttemptId(value=UUID("00000000-0000-0000-0000-000000000000"))

    def test_generate_classmethod(self) -> None:
        aid = AttemptId.generate()
        assert aid.value.version == 4

    def test_equality(self) -> None:
        u = uuid4()
        a = AttemptId(value=u)
        b = AttemptId(value=u)
        assert a == b
        assert hash(a) == hash(b)

    def test_str_returns_uuid_string(self) -> None:
        u = uuid4()
        assert str(AttemptId(value=u)) == str(u)


# ── HashSha256 ──────────────────────────────────────────────────────────────


class TestHashSha256:
    def test_create_from_valid_hex(self) -> None:
        h = "a" * 64
        hs = HashSha256(h)
        assert hs.value == h
        assert str(hs) == h

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="vacío"):
            HashSha256("")

    def test_rejects_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="64 caracteres"):
            HashSha256("abc123")

    def test_rejects_non_hex(self) -> None:
        with pytest.raises(ValueError, match="hexadecimal"):
            HashSha256("g" * 64)

    def test_from_bytes(self) -> None:
        data = b"hello dqs"
        hs = HashSha256.from_bytes(data)
        assert len(hs.value) == 64
        # Reproducible
        assert HashSha256.from_bytes(data) == hs

    def test_from_str(self) -> None:
        data = "canonical bundle"
        hs = HashSha256.from_str(data)
        assert len(hs.value) == 64
        assert HashSha256.from_str(data) == hs

    def test_equality(self) -> None:
        a = HashSha256("a" * 64)
        b = HashSha256("a" * 64)
        c = HashSha256("b" * 64)
        assert a == b
        assert a != c
        assert hash(a) == hash(b)


# ── MetricSource ────────────────────────────────────────────────────────────


class TestMetricSource:
    def test_values(self) -> None:
        assert MetricSource.DIM_USER.value == "dim_user"
        assert MetricSource.FACT_INSCRIPTION.value == "fact_inscription"
        assert MetricSource.MANUAL.value == "manual"

    def test_from_string(self) -> None:
        assert MetricSource("dim_user") == MetricSource.DIM_USER
        assert MetricSource("fact_inscription") == MetricSource.FACT_INSCRIPTION
        assert MetricSource("manual") == MetricSource.MANUAL


# ── Cut ─────────────────────────────────────────────────────────────────────


class TestCut:
    def test_create_valid_date(self) -> None:
        c = Cut(date(2026, 7, 1))
        assert c.value == date(2026, 7, 1)

    def test_accepts_iso_string_in_constructor(self) -> None:
        c = Cut(value="2026-01-15")  # type: ignore[arg-type]
        assert c.value == date(2026, 1, 15)

    def test_from_iso(self) -> None:
        c = Cut.from_iso("2026-07-01")
        assert c.value == date(2026, 7, 1)
        assert c.isoformat() == "2026-07-01"

    def test_str_returns_iso(self) -> None:
        c = Cut(date(2026, 7, 1))
        assert str(c) == "2026-07-01"

    def test_rejects_future(self) -> None:
        far_future = date(2099, 12, 31)
        with pytest.raises(ValueError, match="futuro"):
            Cut(far_future)

    def test_equality(self) -> None:
        a = Cut(date(2026, 7, 1))
        b = Cut(date(2026, 7, 1))
        c = Cut(date(2026, 8, 1))
        assert a == b
        assert a != c


# ── FetchStatus ─────────────────────────────────────────────────────────────


class TestFetchStatus:
    def test_values(self) -> None:
        assert FetchStatus.EMPTY.value == "empty"
        assert FetchStatus.EXTRACTED.value == "extracted"
        assert FetchStatus.FAILED.value == "failed"


# ── RunState ────────────────────────────────────────────────────────────────


class TestRunState:
    def test_all_states_defined(self) -> None:
        expected = {
            "extracting",
            "extracted",
            "validating",
            "ready_for_review",
            "blocked",
            "failed",
            "superseded",
            "published",
        }
        actual = {s.value for s in RunState}
        assert actual == expected

    def test_terminal_states(self) -> None:
        terminal = {
            RunState.BLOCKED,
            RunState.FAILED,
            RunState.SUPERSEDED,
            RunState.PUBLISHED,
        }
        assert set(TERMINAL_STATES) == terminal

    def test_is_terminal_state(self) -> None:
        assert is_terminal_state(RunState.BLOCKED) is True
        assert is_terminal_state(RunState.PUBLISHED) is True
        assert is_terminal_state(RunState.EXTRACTING) is False
        assert is_terminal_state(RunState.READY_FOR_REVIEW) is False
