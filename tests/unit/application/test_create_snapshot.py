"""Tests unitarios para create_snapshot — delegación a SheetRepo."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Sequence

import pytest

from src.consejo.application.ports import SheetRepo
from src.consejo.application.use_cases.create_snapshot import create_snapshot
from src.consejo.domain.entities import Bundle, DqsIssue, Metric, SourceManifest
from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    FetchStatus,
    HashSha256,
    MetricId,
    MetricSource,
    RunId,
)


# ── Fakes ──────────────────────────────────────────────────────────────────


class FakeSheetRepo:
    """SheetRepo falso que registra llamadas."""

    def __init__(self) -> None:
        self.snapshot_calls: list[tuple[Bundle, str, Sequence[Metric]]] = []

    def snapshot(
        self,
        bundle: Bundle,
        spreadsheet_id: str,
        catalogo: Sequence[Metric],
    ) -> str:
        self.snapshot_calls.append((bundle, spreadsheet_id, catalogo))
        return "fake-spreadsheet-id"


# ── Builders ───────────────────────────────────────────────────────────────


_EMPTY_CATALOG: list[Metric] = []


def _make_bundle(
    dqs_issues: list[DqsIssue] | None = None,
    hash_val: str | None = None,
) -> Bundle:
    return Bundle(
        run_id=RunId.generate(),
        attempt_id=AttemptId.generate(),
        cut=Cut(date(2026, 7, 1)),
        catalog_hash="a" * 64,
        manifests=(),
        rows=(),
        dqs=tuple(dqs_issues or []),
        hash=HashSha256(hash_val) if hash_val else HashSha256("f" * 64),
    )


# ── Tests ──────────────────────────────────────────────────────────────────


class TestCreateSnapshot:
    """Tests para el caso de uso create_snapshot."""

    def test_delegates_to_sheet_repo(self):
        repo = FakeSheetRepo()
        bundle = _make_bundle()
        catalogo = [
            Metric(
                id=MetricId("registered_cpe"),
                name="Registrados CPE",
                key="registered_cpe",
                source=MetricSource.DIM_USER,
                formula="",
                db_mapping="dim_user",
                platform_scope=["CPE"],
            )
        ]
        result = create_snapshot(
            bundle, repo, "spread-123", catalogo=catalogo
        )

        assert result == "fake-spreadsheet-id"
        assert len(repo.snapshot_calls) == 1
        assert repo.snapshot_calls[0][0] is bundle
        assert repo.snapshot_calls[0][1] == "spread-123"
        assert repo.snapshot_calls[0][2] is catalogo

    def test_blocks_on_dqs_blocker(self):
        """Bundle con blocker DQS no debe llamar a SheetRepo."""
        repo = FakeSheetRepo()
        issues = [
            DqsIssue(
                obligation=1,
                code="DQS-001-CARDINALITY",
                severity="blocker",
                message="Faltan manifiestos",
            ),
        ]
        bundle = _make_bundle(dqs_issues=issues)

        with pytest.raises(ValueError, match="blocker"):
            create_snapshot(bundle, repo, "spread-123", catalogo=_EMPTY_CATALOG)

        assert len(repo.snapshot_calls) == 0

    def test_allows_warnings(self):
        """Bundle con warnings (no blockers) debe permitir snapshot."""
        repo = FakeSheetRepo()
        issues = [
            DqsIssue(
                obligation=3,
                code="DQS-003-EMPTY_SOURCE",
                severity="warning",
                message="Fuente vacía",
            ),
        ]
        bundle = _make_bundle(dqs_issues=issues)

        result = create_snapshot(bundle, repo, "spread-123", catalogo=_EMPTY_CATALOG)
        assert result == "fake-spreadsheet-id"
        assert len(repo.snapshot_calls) == 1

    def test_allows_empty_dqs(self):
        """Bundle sin issues DQS debe ejecutar snapshot normalmente."""
        repo = FakeSheetRepo()
        bundle = _make_bundle()
        result = create_snapshot(bundle, repo, "spread-123", catalogo=_EMPTY_CATALOG)
        assert result == "fake-spreadsheet-id"

    def test_passes_correct_bundle_to_repo(self):
        repo = FakeSheetRepo()
        bundle = _make_bundle(hash_val="e" * 64)
        create_snapshot(bundle, repo, "spread-123", catalogo=_EMPTY_CATALOG)

        called = repo.snapshot_calls[0][0]
        assert called.run_id == bundle.run_id
        assert called.attempt_id == bundle.attempt_id
        assert str(called.hash) == "e" * 64

    def test_error_message_includes_blocker_codes(self):
        repo = FakeSheetRepo()
        issues = [
            DqsIssue(obligation=1, code="DQS-001", severity="blocker",
                     message="A"),
            DqsIssue(obligation=2, code="DQS-002", severity="blocker",
                     message="B"),
        ]
        bundle = _make_bundle(dqs_issues=issues)

        with pytest.raises(ValueError) as exc:
            create_snapshot(bundle, repo, "spread-123", catalogo=_EMPTY_CATALOG)

        assert "DQS-001" in str(exc.value)
        assert "DQS-002" in str(exc.value)
        assert "2 blocker" in str(exc.value)
