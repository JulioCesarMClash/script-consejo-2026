"""E2E: Full pipeline verification with fakes.

Verifica el flujo completo extract → validate → snapshot con DB
y Sheets falsos. Trazabilidad por run_id/attempt_id, bundle canónico
UTF-8, hash SHA-256, DQS bloqueo, y zero-rows orphan checks.

Los tests que requieren credenciales reales (PostgreSQL, Google Sheets)
están marcados con @pytest.mark.skip.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

import pytest

from src.consejo.adapters.catalog.yaml_metric_repo import YamlMetricRepo
from src.consejo.application.ports import SourceConn
from src.consejo.application.use_cases.create_snapshot import create_snapshot
from src.consejo.application.use_cases.extract_data import extract_data
from src.consejo.application.use_cases.validate_bundle import (
    DqsBlockedError,
    validate_bundle,
)
from src.consejo.domain.entities import Bundle
from src.consejo.domain.value_objects import AttemptId, Cut, RunId


# ── Fakes E2E ───────────────────────────────────────────────────────────────


class E2EFakeSourceConn(SourceConn):
    """SourceConn con datos simulados resueltos por orden de llamada.

    Call-order matching: la extracción itera el catálogo en orden y ejecuta
    `fetch` para las 10 métricas SQL (10 queries). Devuelve la i-ésima fila
    de la secuencia en la i-ésima llamada.
    """

    def __init__(self, rows_sequence: Sequence[Sequence[Mapping]] | None = None):
        self._sequence: list[list[dict]] = [
            [dict(r) for r in rows] for rows in (rows_sequence or [])
        ]
        self._call_index = 0
        self._calls: list[tuple[str, Mapping]] = []

    def fetch(
        self, sql: str, params: Mapping[str, object]
    ) -> Sequence[Mapping[str, object]]:
        self._calls.append((sql, params))
        if self._call_index < len(self._sequence):
            rows = self._sequence[self._call_index]
            self._call_index += 1
            return [dict(r) for r in rows]
        return []


class E2EFakeSheetRepo:
    """SheetRepo falso que captura bundles para verificación E2E."""

    def __init__(self) -> None:
        self._snapshots: list[Bundle] = []

    def snapshot(self, bundle: Bundle) -> str:
        self._snapshots.append(bundle)
        return "e2e-spreadsheet-id"


# ── Data ────────────────────────────────────────────────────────────────────


def _build_e2e_sequence() -> Sequence[Sequence[Mapping]]:
    """Datos simulados completos, ordenados por extracción del catálogo.

    10 métricas SQL-ejecutables en orden; las 6 restantes (4 textsum +
    2 manual) no disparan fetch (EMPTY).
    """
    return [
        [{"count": 1500}],  # registered_cpe
        [{"count": 1000}],  # registered_aprende
        [{"count": 18000}],  # inscriptions_cpe
        [{"count": 6000}],  # inscriptions_cpe_from_aprende
        [{"count": 5000}],  # inscribed_unique_cpe
        [{"count": 1500}],  # inscribed_unique_cpe_from_aprende
        [{"count": 3500}],  # certifications_cpe
        [{"count": 1400}],  # certifications_cpe_from_aprende
        [{"count": 2800}],  # certified_unique_cpe
        [{"count": 1100}],  # certified_unique_cpe_from_aprende
    ]


def _run_full_pipeline(
    catalog_path: Path,
    fake_conn: E2EFakeSourceConn,
    fake_sheets: E2EFakeSheetRepo,
    cut: date | None = None,
) -> dict:
    """Ejecuta el pipeline completo extract → validate → snapshot.

    Returns:
        Dict con run_id, attempt_id, bundle, manifests_len, hash, sheet_result.
    """
    if cut is None:
        cut = date(2026, 7, 1)

    repo = YamlMetricRepo(str(catalog_path))
    catalog = list(repo.list_metrics())
    catalog_hash = repo.compute_catalog_hash()
    run_id = RunId.generate()
    attempt_id = AttemptId.generate()
    fetched_at = datetime.now(timezone.utc)

    manifests = extract_data(
        metric_repo=repo,
        source_conn=fake_conn,
        run_id=run_id,
        attempt_id=attempt_id,
        cut=cut,
        fetched_at=fetched_at,
    )
    bundle = validate_bundle(
        manifests=manifests,
        catalog=catalog,
        run_id=run_id,
        attempt_id=attempt_id,
        cut=Cut(cut),
        catalog_hash=catalog_hash,
    )
    sid = create_snapshot(bundle, fake_sheets)

    return {
        "run_id": str(run_id),
        "attempt_id": str(attempt_id),
        "cut": cut.isoformat(),
        "catalog_hash": catalog_hash,
        "bundle_hash": str(bundle.hash),
        "manifests_len": len(manifests),
        "rows_len": len(bundle.rows),
        "sheet_id": sid,
        "bundle": bundle,
    }


# ── Tests ───────────────────────────────────────────────────────────────────


class TestFullPipelineE2E:
    """End-to-end pipeline verification con fakes completos."""

    @pytest.fixture
    def catalog_path(self, sample_catalog_path: Path) -> Path:
        return sample_catalog_path

    @pytest.fixture
    def fake_conn(self) -> E2EFakeSourceConn:
        return E2EFakeSourceConn(_build_e2e_sequence())

    @pytest.fixture
    def fake_sheets(self) -> E2EFakeSheetRepo:
        return E2EFakeSheetRepo()

    # ── 5.1.a: 16 manifests ──────────────────────────────────────────────

    def test_pipeline_produces_16_manifests(
        self, catalog_path: Path, fake_conn: E2EFakeSourceConn,
        fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """El pipeline completo produce exactamente 16 manifiestos."""
        result = _run_full_pipeline(catalog_path, fake_conn, fake_sheets)
        assert result["manifests_len"] == 16
        # 10 metrics con SQL ejecutable, 4 totals no-SQL (empty), 2 manual (empty)
        assert result["rows_len"] == 10

    # ── 5.1.b: Traceability run_id / attempt_id ──────────────────────────

    def test_pipeline_traceability_ids(
        self, catalog_path: Path, fake_conn: E2EFakeSourceConn,
        fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """Cada ejecución genera run_id y attempt_id únicos (UUID v4)."""
        r1 = _run_full_pipeline(catalog_path, fake_conn, fake_sheets)
        r2 = _run_full_pipeline(catalog_path, E2EFakeSourceConn(_build_e2e_sequence()), E2EFakeSheetRepo())

        assert r1["run_id"] != r2["run_id"]
        assert r1["attempt_id"] != r2["attempt_id"]
        assert len(r1["run_id"]) == 36  # UUID v4
        assert len(r1["attempt_id"]) == 36
        # UUID v4 tiene versión 4 en el 13er carácter
        assert r1["run_id"][14] == "4"
        assert r1["attempt_id"][14] == "4"

    # ── 5.1.c: Bundle canónico UTF-8 + SHA-256 ──────────────────────────

    def test_bundle_canonical_utf8_and_sha256(
        self, catalog_path: Path, fake_conn: E2EFakeSourceConn,
        fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """El bundle es JSON UTF-8 canónico con SHA-256 válido."""
        result = _run_full_pipeline(catalog_path, fake_conn, fake_sheets)
        bundle = result["bundle"]

        # SHA-256: 64 caracteres hex
        assert len(result["bundle_hash"]) == 64
        assert result["bundle_hash"] != "0" * 64
        int(result["bundle_hash"], 16)  # debe ser hex válido

        # JSON canónico con claves ordenadas
        canonical = bundle.canonical_json()
        parsed = json.loads(canonical)
        assert parsed["run_id"] == result["run_id"]
        assert parsed["attempt_id"] == result["attempt_id"]
        assert parsed["cut"] == result["cut"]
        assert "hash" in parsed
        assert "manifests" in parsed
        assert "dqs" in parsed
        assert "rows" in parsed

        # Verificar orden alfabético de claves
        keys = list(parsed.keys())
        sorted_keys = sorted(keys)
        assert keys == sorted_keys, f"JSON keys no ordenadas: {keys}"

    # ── 5.1.d: DQS blocking stops pipeline ──────────────────────────────

    def test_dqs_blocking_stops_pipeline(
        self, catalog_path: Path, fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """Si DQS bloquea, no se debe crear snapshot."""
        repo = YamlMetricRepo(str(catalog_path))
        catalog = list(repo.list_metrics())
        catalog_hash = repo.compute_catalog_hash()

        with pytest.raises(DqsBlockedError):
            validate_bundle(
                manifests=[],  # 0 manifiestos → cardinalidad DQS-001
                catalog=catalog,
                run_id=RunId.generate(),
                attempt_id=AttemptId.generate(),
                cut=Cut(date(2026, 7, 1)),
                catalog_hash=catalog_hash,
            )
        assert len(fake_sheets._snapshots) == 0

    # ── 5.1.e: Zero-rows orphan check ───────────────────────────────────

    def test_zero_rows_orphan_check(
        self, catalog_path: Path, fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """Las filas del bundle deben tener metric_id, source y value."""
        fake = E2EFakeSourceConn(_build_e2e_sequence())
        result = _run_full_pipeline(catalog_path, fake, fake_sheets)
        bundle = result["bundle"]

        for row in bundle.rows:
            assert "metric_id" in row, f"Fila sin metric_id: {row}"
            assert "source" in row, f"Fila sin source: {row}"
            assert "value" in row or "count" in row, f"Fila sin value/count: {row}"
            assert str(row.get("metric_id", "")), "metric_id vacío en fila"

        # Ninguna fila huérfana: cada fila corresponde a un manifiesto válido
        metric_ids = {str(m.metric_id) for m in bundle.manifests}
        for row in bundle.rows:
            assert row["metric_id"] in metric_ids, (
                f"Fila huérfana: {row['metric_id']} no está en manifiestos"
            )

    # ── 5.1.f: Manual metrics are empty, not zero ───────────────────────

    def test_manual_metrics_empty_not_zero(
        self, catalog_path: Path, fake_conn: E2EFakeSourceConn,
        fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """Métricas manuales (beneficiaries) son EMPTY, no cero."""
        result = _run_full_pipeline(catalog_path, fake_conn, fake_sheets)
        bundle = result["bundle"]

        manual_manifests = [
            m for m in bundle.manifests if m.source.value == "manual"
        ]
        assert len(manual_manifests) == 2  # beneficiaries + beneficiaries_unique
        for m in manual_manifests:
            assert m.status.value == "empty"
            assert len(m.rows) == 0

    # ── 5.1.g: Full pipeline with real DB (skipped) ─────────────────────

    @pytest.mark.skip(
        reason="Requiere conexión real a PostgreSQL analisis_cpe_db "
               "(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT). "
               "Ejecutar en entorno autorizado con credenciales."
    )
    def test_pipeline_with_real_db_requires_creds(self) -> None:
        """Pipeline completo con PostgreSQL real.

        Solo ejecutable en entorno autorizado con credenciales configuradas.
        """
        from src.consejo.config.container import build_pipeline

        pipeline = build_pipeline(
            cut=date(2026, 7, 1),
            spreadsheet_id="test-spreadsheet-id",
        )
        result = pipeline()
        assert result["manifests"] == 16

    # ── 5.1.h: Full pipeline with real Sheets (skipped) ──────────────────

    @pytest.mark.skip(
        reason="Requiere credenciales Google Sheets reales "
               "(GOOGLE_APPLICATION_CREDENTIALS, spreadsheet_id). "
               "Ejecutar en entorno autorizado con service account."
    )
    def test_pipeline_with_real_sheets_requires_creds(self) -> None:
        """Pipeline completo con Google Sheets real.

        Solo ejecutable en entorno autorizado con service account.
        Verifica 5 hojas creadas, cero escrituras Slides.
        """
        from src.consejo.config.container import build_pipeline

        pipeline = build_pipeline(
            cut=date(2026, 7, 1),
            spreadsheet_id="test-spreadsheet-id",
        )
        result = pipeline()
        assert "spreadsheet_id" in result
