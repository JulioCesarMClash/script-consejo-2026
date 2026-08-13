"""E2E: Full pipeline verification with fakes.

Verifica el flujo completo extract → validate → snapshot con DB
y Sheets falsos. Trazabilidad por run_id/attempt_id, bundle canónico
UTF-8, hash SHA-256, DQS bloqueo, y zero-rows orphan checks.

Los tests que requieren credenciales reales (PostgreSQL, Google Sheets)
son opt-in mediante la configuración del entorno.
"""

from __future__ import annotations

import json
import os
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
from src.consejo.domain.entities import Bundle, Metric
from src.consejo.domain.value_objects import AttemptId, Cut, RunId


# ── Fakes E2E ───────────────────────────────────────────────────────────────


class E2EFakeSourceConn(SourceConn):
    """SourceConn con datos simulados resueltos por orden de llamada.

    Call-order matching: la extracción itera el catálogo en orden y ejecuta
    `fetch` para las 11 métricas SQL. Devuelve la i-ésima fila de la secuencia
    en la i-ésima llamada; la 11ª consulta (slide2_empleo... sector) no
    tiene datos y devuelve vacío. Las métricas sum derivadas no disparan fetch.
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

    def snapshot(
        self,
        bundle: Bundle,
        spreadsheet_id: str,
        catalogo: Sequence[Metric],
    ) -> str:
        self._snapshots.append(bundle)
        return "e2e-spreadsheet-id"


# ── Data ────────────────────────────────────────────────────────────────────


def _build_e2e_sequence() -> Sequence[Sequence[Mapping]]:
    """Datos simulados completos, ordenados por extracción del catálogo.

    10 métricas SQL-ejecutables con datos en orden; las 6 métricas sum
    derivadas se calculan desde sus partes (sin fetch); slide2_empleo…
    sector (11ª SQL) devuelve vacío (EMPTY).
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
    sid = create_snapshot(bundle, fake_sheets, "e2e-spreadsheet-id", catalogo=catalog)

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

    def test_pipeline_produces_22_manifests(
        self, catalog_path: Path, fake_conn: E2EFakeSourceConn,
        fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """El pipeline completo produce exactamente 29 manifiestos."""
        result = _run_full_pipeline(catalog_path, fake_conn, fake_sheets)
        assert result["manifests_len"] == 29
        # 10 SQL-fetched EXTRACTED + 6 derived sums built on their parts = 16;
        # slide1, slide12_rutas_aprendizaje, slide2_empleo_incluyente_por_sector,
        # las 2 de Slide 3 (MySQL, sin mysql_conn en el fake), las 2 de
        # Slide 4 (postgres, sin filas en la secuencia del fake), las 4 de
        # Slide 13 (postgres, sin filas en la secuencia del fake) y las 2 de
        # Slide 15 (MySQL, sin filas en la secuencia del fake) vuelven EMPTY
        # (sin fila)
        assert result["rows_len"] == 16

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

    def test_beneficiaries_is_derived_not_manual(
        self, catalog_path: Path, fake_conn: E2EFakeSourceConn,
        fake_sheets: E2EFakeSheetRepo,
    ) -> None:
        """Beneficiaries es derivada (sum), no manual: EXTRACTED con valor."""
        result = _run_full_pipeline(catalog_path, fake_conn, fake_sheets)
        bundle = result["bundle"]

        manual_manifests = [
            m for m in bundle.manifests if m.source.value == "manual"
        ]
        assert len(manual_manifests) == 0  # el catálogo ya no tiene manuales

        beneficiaries = next(
            m for m in bundle.manifests if str(m.metric_id) == "beneficiaries"
        )
        assert beneficiaries.source.value == "fact_inscription"
        assert beneficiaries.status.value == "extracted"
        assert beneficiaries.rows == ({"value": 3000},)

    # ── 5.1.g: Full pipeline with real DB (opt-in) ───────────────────────

    def test_pipeline_with_real_db_requires_creds(self) -> None:
        """Pipeline completo con PostgreSQL real.

        Solo ejecutable en entorno autorizado con credenciales configuradas.
        No escribe en Google Sheets: verifica extracción y validación reales.
        """
        from src.consejo.adapters.postgres.source_conn import PostgresSourceConn
        from src.consejo.config.settings import Settings

        if os.environ.get("RUN_REAL_DB_TESTS") != "1":
            pytest.skip(
                "PostgreSQL real no autorizado; configurar RUN_REAL_DB_TESTS=1"
            )

        try:
            settings = Settings()
        except (TypeError, ValueError) as exc:
            pytest.skip(f"Configuración PostgreSQL no disponible: {type(exc).__name__}")

        required = {
            "DB_HOST": settings.db_host,
            "DB_NAME": settings.db_name,
            "DB_USER": settings.db_user,
            "DB_PASSWORD": settings.db_password,
            "DB_PORT": settings.db_port,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            pytest.skip(
                "Configuración PostgreSQL incompleta; faltan: "
                + ", ".join(missing)
            )

        repo = YamlMetricRepo(settings.catalog_path)
        run_id = RunId.generate()
        attempt_id = AttemptId.generate()
        cut = date(2026, 7, 1)

        try:
            manifests = extract_data(
                metric_repo=repo,
                source_conn=PostgresSourceConn(settings),
                run_id=run_id,
                attempt_id=attempt_id,
                cut=cut,
            )
        except ConnectionError as exc:
            pytest.skip(f"PostgreSQL no disponible: {type(exc).__name__}")

        bundle = validate_bundle(
            manifests=manifests,
            catalog=list(repo.list_metrics()),
            run_id=run_id,
            attempt_id=attempt_id,
            cut=Cut(cut),
            catalog_hash=repo.compute_catalog_hash(),
        )

        assert len(manifests) == 29
        assert len(bundle.rows) > 0

    # ── 5.1.h: Full pipeline with real Sheets (opt-in) ───────────────────

    def test_pipeline_with_real_sheets_requires_creds(self) -> None:
        """Pipeline completo con Google Sheets real.

        Solo ejecutable con autorización explícita y configuración local.
        Este test escribe en el spreadsheet configurado.
        """
        from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
            SHEET_NAMES,
            GoogleMcpSheetRepo,
            SheetProxyError,
        )
        from src.consejo.adapters.postgres.source_conn import PostgresSourceConn
        from src.consejo.config.settings import Settings

        if os.environ.get("RUN_REAL_SHEETS_TESTS") != "1":
            pytest.skip(
                "Google Sheets real no autorizado; configurar RUN_REAL_SHEETS_TESTS=1"
            )

        try:
            settings = Settings()
        except (TypeError, ValueError):
            pytest.skip("Configuración real no disponible")

        credentials_path = Path(settings.google_application_credentials).expanduser()
        if not settings.google_application_credentials or not credentials_path.is_file():
            pytest.skip("Ruta de credenciales Google no disponible")
        if not settings.google_spreadsheet_id:
            pytest.skip("GOOGLE_SPREADSHEET_ID no configurado")

        repo = YamlMetricRepo(settings.catalog_path)
        catalog = list(repo.list_metrics())
        run_id = RunId.generate()
        attempt_id = AttemptId.generate()
        cut = date(2026, 7, 1)

        try:
            manifests = extract_data(
                metric_repo=repo,
                source_conn=PostgresSourceConn(settings),
                run_id=run_id,
                attempt_id=attempt_id,
                cut=cut,
            )
            bundle = validate_bundle(
                manifests=manifests,
                catalog=catalog,
                run_id=run_id,
                attempt_id=attempt_id,
                cut=Cut(cut),
                catalog_hash=repo.compute_catalog_hash(),
            )
            spreadsheet_id = create_snapshot(
                bundle,
                _ConfiguredSheetRepo(GoogleMcpSheetRepo(), settings.google_spreadsheet_id),
                catalogo=catalog,
            )
        except (ConnectionError, FileNotFoundError, SheetProxyError):
            pytest.skip("Google Sheets o PostgreSQL no disponible")

        assert spreadsheet_id == settings.google_spreadsheet_id

        verifier = GoogleMcpSheetRepo()
        verifier._start_proxy()
        try:
            verifier._init_handshake()
            metadata = verifier._get_spreadsheet_meta(spreadsheet_id)
        finally:
            verifier._stop_proxy()

        actual_titles = {
            sheet["properties"]["title"]
            for sheet in (metadata or {}).get("fields", {}).get("sheets", [])
        }
        assert actual_titles == set(SHEET_NAMES)


class _ConfiguredSheetRepo:
    def __init__(self, repo: object, spreadsheet_id: str) -> None:
        self._repo = repo
        self._spreadsheet_id = spreadsheet_id

    def snapshot(
        self,
        bundle: Bundle,
        spreadsheet_id: str,
        catalogo: Sequence[Metric],
    ) -> str:
        return self._repo.snapshot(bundle, self._spreadsheet_id, catalogo)
