"""E2E: Validación de idempotencia del pipeline.

Verifica que reejecutar con mismo cut + misma data produce hash idéntico,
no duplica filas en hoja Datos, y distintos attempt_id generan hashes
diferentes.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence
from unittest.mock import patch

import pytest

from src.consejo.adapters.catalog.yaml_metric_repo import YamlMetricRepo
from src.consejo.application.ports import SourceConn
from src.consejo.application.use_cases.create_snapshot import create_snapshot
from src.consejo.application.use_cases.extract_data import extract_data
from src.consejo.application.use_cases.validate_bundle import validate_bundle
from src.consejo.domain.entities import Bundle
from src.consejo.domain.value_objects import AttemptId, Cut, RunId


# ── Fakes ───────────────────────────────────────────────────────────────────


class IdempotentFakeSourceConn(SourceConn):
    """SourceConn con datos determinísticos resueltos por orden de llamada.

    Call-order matching garantiza idempotencia: misma secuencia de filas →
    mismo bundle → mismo hash.
    """

    def __init__(self, rows_sequence: Sequence[Sequence[Mapping]] | None = None):
        self._sequence: list[list[dict]] = [
            [dict(r) for r in rows] for rows in (rows_sequence or [])
        ]
        self._call_index = 0

    def fetch(
        self, sql: str, params: Mapping[str, object]
    ) -> Sequence[Mapping[str, object]]:
        if self._call_index < len(self._sequence):
            rows = self._sequence[self._call_index]
            self._call_index += 1
            return [dict(r) for r in rows]
        return []


class IdempotentFakeSheetRepo:
    """SheetRepo falso que captura bundles recibidos."""

    def __init__(self) -> None:
        self._snapshots: list[Bundle] = []

    def snapshot(self, bundle: Bundle) -> str:
        self._snapshots.append(bundle)
        return "idempotent-spreadsheet-id"


def _build_idempotent_sequence() -> Sequence[Sequence[Mapping]]:
    """Datos fijos y determinísticos, ordenados por extracción del catálogo.

    10 métricas SQL-ejecutables en orden. La misma secuencia siempre →
    mismo bundle → hash estable (idempotencia).
    """
    return [
        [{"count": 1500}],  # registered_cpe
        [{"count": 900}],  # registered_aprende
        [{"count": 18000}],  # inscriptions_cpe
        [{"count": 6000}],  # inscriptions_cpe_from_aprende
        [{"count": 5000}],  # inscribed_unique_cpe
        [{"count": 1500}],  # inscribed_unique_cpe_from_aprende
        [{"count": 3500}],  # certifications_cpe
        [{"count": 1400}],  # certifications_cpe_from_aprende
        [{"count": 2800}],  # certified_unique_cpe
        [{"count": 1100}],  # certified_unique_cpe_from_aprende
    ]


def _execute_pipeline_fixed(
    catalog_path: Path,
    run_id: RunId,
    attempt_id: AttemptId,
    cut: date,
    fetched_at: datetime,
) -> Bundle:
    """Ejecuta el pipeline con identificadores y tiempo fijos para idempotencia."""
    repo = YamlMetricRepo(str(catalog_path))
    catalog = list(repo.list_metrics())
    catalog_hash = repo.compute_catalog_hash()
    fake_conn = IdempotentFakeSourceConn(_build_idempotent_sequence())

    # Freeze datetime.now() para que freshness_hours sea determinístico
    frozen_now = fetched_at.replace(tzinfo=timezone.utc)
    with patch(
        "src.consejo.application.use_cases.extract_data.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = frozen_now
        mock_dt.timezone = timezone

        manifests = extract_data(
            metric_repo=repo,
            source_conn=fake_conn,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=cut,
            fetched_at=fetched_at,
        )
    return validate_bundle(
        manifests=manifests,
        catalog=catalog,
        run_id=run_id,
        attempt_id=attempt_id,
        cut=Cut(cut),
        catalog_hash=catalog_hash,
    )


# ── Tests ───────────────────────────────────────────────────────────────────


class TestIdempotencyE2E:
    """Validación de idempotencia del pipeline end-to-end."""

    @pytest.fixture
    def catalog_path(self, sample_catalog_path: Path) -> Path:
        return sample_catalog_path

    # ── 5.2.a: Mismo cut + misma data → hash idéntico ────────────────────

    def test_same_cut_same_data_identical_hash(
        self, catalog_path: Path,
    ) -> None:
        """Mismo attempt_id + misma data → hash idéntico en cada ejecución."""
        run_id = RunId.generate()
        attempt_id = AttemptId.generate()
        cut = date(2026, 7, 1)
        fetched_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

        b1 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )
        b2 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )

        assert str(b1.hash) == str(b2.hash), (
            f"Hash no idéntico: {str(b1.hash)} != {str(b2.hash)}"
        )
        assert len(str(b1.hash)) == 64
        assert str(b1.hash) != "0" * 64

    # ── 5.2.b: Reejecución no duplica filas ─────────────────────────────

    def test_reexecution_does_not_duplicate_rows(
        self, catalog_path: Path,
    ) -> None:
        """Reejecutar con mismo attempt_id no duplica filas en Datos."""
        run_id = RunId.generate()
        attempt_id = AttemptId.generate()
        cut = date(2026, 7, 1)
        fetched_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

        repo = YamlMetricRepo(str(catalog_path))

        # Primera ejecución: crear snapshot
        sheets1 = IdempotentFakeSheetRepo()
        b1 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )
        create_snapshot(b1, sheets1)
        assert len(sheets1._snapshots) == 1
        rows_first = len(b1.rows)

        # Segunda ejecución: mismo attempt_id, misma data
        sheets2 = IdempotentFakeSheetRepo()
        b2 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )
        create_snapshot(b2, sheets2)

        # Mismas filas, no duplicadas
        assert len(b2.rows) == rows_first, (
            f"Filas duplicadas: {len(b2.rows)} != {rows_first}"
        )

        # El contenido debe ser idéntico línea por línea
        for i, (r1_val, r2_val) in enumerate(
            zip(b1.rows, b2.rows, strict=True)
        ):
            assert r1_val == r2_val, (
                f"Fila {i} difiere: {r1_val} != {r2_val}"
            )

    # ── 5.2.c: Distinto attempt_id → hash diferente ─────────────────────

    def test_different_attempt_id_different_hash(
        self, catalog_path: Path,
    ) -> None:
        """Nuevo attempt_id con misma data produce hash diferente."""
        run_id = RunId.generate()
        cut = date(2026, 7, 1)
        fetched_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

        aid1 = AttemptId.generate()
        aid2 = AttemptId.generate()

        b1 = _execute_pipeline_fixed(
            catalog_path, run_id, aid1, cut, fetched_at
        )
        b2 = _execute_pipeline_fixed(
            catalog_path, run_id, aid2, cut, fetched_at
        )

        assert str(b1.hash) != str(b2.hash), (
            "Distintos attempt_id deben producir hashes diferentes"
        )
        assert len(str(b1.hash)) == 64
        assert len(str(b2.hash)) == 64

    # ── 5.2.d: Bundle canónico estable ───────────────────────────────────

    def test_bundle_json_stable_across_runs(
        self, catalog_path: Path,
    ) -> None:
        """El JSON canónico del bundle es determinístico con misma data."""
        run_id = RunId.generate()
        attempt_id = AttemptId.generate()
        cut = date(2026, 7, 1)
        fetched_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

        b1 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )
        b2 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )

        json1 = b1.canonical_json()
        json2 = b2.canonical_json()

        assert json1 == json2, "Bundle JSON no es estable entre ejecuciones"

        parsed = json.loads(json1)
        assert parsed["attempt_id"] == str(attempt_id)
        assert parsed["run_id"] == str(run_id)
        assert parsed["cut"] == cut.isoformat()

    # ── 5.2.e: Fuente vacía no es cero en idempotencia ──────────────────

    def test_empty_source_not_zero_preserves_idempotency(
        self, catalog_path: Path,
    ) -> None:
        """Métricas manuales vacías no afectan la idempotencia."""
        run_id = RunId.generate()
        attempt_id = AttemptId.generate()
        cut = date(2026, 7, 1)
        fetched_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

        b1 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )
        b2 = _execute_pipeline_fixed(
            catalog_path, run_id, attempt_id, cut, fetched_at
        )

        assert str(b1.hash) == str(b2.hash)

        # Métricas manuales deben estar empty en ambas ejecuciones
        manual1 = [m for m in b1.manifests if m.source.value == "manual"]
        manual2 = [m for m in b2.manifests if m.source.value == "manual"]
        assert len(manual1) == len(manual2)
        for m1, m2 in zip(manual1, manual2, strict=True):
            assert m1.status.value == m2.status.value == "empty"
            assert len(m1.rows) == len(m2.rows) == 0

    # ── 5.2.f: Idempotencia con DB real (skipped) ───────────────────────

    @pytest.mark.skip(
        reason="Requiere conexión real a PostgreSQL analisis_cpe_db. "
               "Ejecutar en entorno autorizado con credenciales para "
               "verificar idempotencia con datos reales de BD."
    )
    def test_idempotency_with_real_db_requires_creds(self) -> None:
        """Idempotencia con PostgreSQL real (skipped).

        Verifica que mismo cut + misma data real → hash idéntico.
        """
        ...
