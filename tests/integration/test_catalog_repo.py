"""Tests de integración para YamlMetricRepo con catálogo real.

Verifica que el catálogo YAML se lea correctamente, exponga 16 métricas,
identifique correctamente las plataformas y fuentes manuales.
"""

from pathlib import Path

import pytest

from src.consejo.adapters.catalog.yaml_metric_repo import YamlMetricRepo
from src.consejo.domain.value_objects import MetricSource


@pytest.fixture
def catalog_repo(sample_catalog_path: Path) -> YamlMetricRepo:
    """Repositorio que apunta al catálogo real."""
    return YamlMetricRepo(str(sample_catalog_path))


class TestCatalogRepo:
    """Verifica la lectura del catálogo YAML real."""

    def test_returns_20_metrics(self, catalog_repo: YamlMetricRepo) -> None:
        metrics = list(catalog_repo.list_metrics())
        assert len(metrics) == 29

    def test_metrics_have_unique_keys(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        keys = [m.key for m in metrics]
        assert len(keys) == len(set(keys))

    def test_no_manual_metrics_in_catalog(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        manual = [m for m in metrics if m.source == MetricSource.MANUAL]
        assert len(manual) == 0  # beneficiaries ya no es manual, es derivada
        beneficiaries = next(m for m in metrics if m.key == "beneficiaries")
        assert beneficiaries.source == MetricSource.FACT_INSCRIPTION

    def test_beneficiaries_unique_is_automatic_sum(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metric = next(
            m for m in catalog_repo.list_metrics()
            if m.key == "beneficiaries_unique"
        )

        assert metric.source == MetricSource.FACT_INSCRIPTION
        assert metric.formula.startswith(
            "inscribed_unique_cpe + inscribed_unique_cpe_from_aprende"
        )

    def test_finds_dim_user_metrics(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        dim_user = [m for m in metrics if m.source == MetricSource.DIM_USER]
        assert len(dim_user) == 7
        dim_keys = {m.key for m in dim_user}
        assert dim_keys == {
            "registered_cpe",
            "registered_aprende",
            "registered_total",
            "slide3_capacitate_carso",
            "slide3_academica_labs",
            "slide4_cultura_salud_aprende",
            "slide15_mario_molina_vistas",
        }

    def test_mysql_metrics_have_db_source_mysql(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        mysql = [m for m in metrics if m.key in {
            "slide3_capacitate_carso",
            "slide3_academica_labs",
        }]
        assert len(mysql) == 2
        for m in mysql:
            assert m.db_source == "mysql"
            assert m.db_mapping.strip().startswith("SELECT")
            # Slide 3 usa ventanas FIJAS de tres columnas, sin period_start/end.
            assert "%(period_start)s" not in m.db_mapping
            assert "%(period_end)s" not in m.db_mapping
            assert '"2025"' in m.db_mapping
            assert '"sep2026"' in m.db_mapping
            assert '"base_dic2026"' in m.db_mapping
            assert "'2025-01-01'" in m.db_mapping
            assert "'2026-08-02'" in m.db_mapping
            assert "'2026-08-01'" in m.db_mapping and "'2027-01-01'" in m.db_mapping

    def test_postgres_metrics_have_db_source_postgres(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        postgres = [m for m in metrics if m.key in {
            "slide4_aprende_seguridad_vial",
            "slide4_cultura_salud_aprende",
        }]
        assert len(postgres) == 2
        for m in postgres:
            assert m.db_source == "postgres"
            assert m.db_mapping.strip().startswith("SELECT")
            # Slide 4 usa ventanas FIJAS de cuatro columnas, sin period_start/end.
            assert "%(period_start)s" not in m.db_mapping
            assert "%(period_end)s" not in m.db_mapping
            assert '"2024"' in m.db_mapping
            assert '"sep2025"' in m.db_mapping
            assert '"dic2025"' in m.db_mapping
            assert '"acumulado"' in m.db_mapping
            assert "'2024-01-01'" in m.db_mapping
            assert "'2025-10-01'" in m.db_mapping

    def test_finds_fact_inscription_metrics(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        fact = [
            m
            for m in metrics
            if m.source == MetricSource.FACT_INSCRIPTION
        ]
        assert len(fact) == 22  # 17 previas + slide12_rutas_aprendizaje + 4 slide13_penitenciarios_* + 1 slide15_mario_molina_inscripciones

    def test_platform_scope_cpe(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        cpe = [m for m in metrics if "cpe" in m.platform_scope]
        assert len(cpe) == 18  # 18 de 27 incluyen cpe; las 2 MySQL, 2 slide4, 4 slide13 y registered_aprende no

    def test_metric_has_db_mapping(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        for m in metrics:
            assert m.db_mapping, f"{m.key} debería tener db_mapping"

    def test_sum_type_metrics_have_textual_mapping(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Métricas tipo sum ('A + B') no deberían tener db_mapping SQL."""
        metrics = list(catalog_repo.list_metrics())
        sum_keys = {
            "registered_total",
            "inscriptions_cpe_total",
            "certifications_cpe_total",
            "certified_unique_cpe_total",
            "beneficiaries_unique",
        }
        for m in metrics:
            if m.key in sum_keys:
                db = m.db_mapping.strip()
                assert not db.upper().startswith(
                    "SELECT"
                ), f"{m.key} no debe ser SQL ejecutable"

    def test_all_metrics_have_name(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        for m in metrics:
            assert m.name, f"{m.key} debería tener name"

    def test_grain_is_inferred(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        for m in metrics:
            assert m.grain, f"{m.key} debería tener grain inferido"
            assert m.grain != "desconocido", (
                f"{m.key} tiene grain desconocido"
            )

    def test_catalog_hash_is_stable(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        h1 = catalog_repo.compute_catalog_hash()
        h2 = catalog_repo.compute_catalog_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_certificate_queries_use_exclusive_configured_period(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = [
            metric for metric in catalog_repo.list_metrics()
            if metric.key in {"certifications_cpe", "certifications_cpe_from_aprende"}
        ]

        assert metrics
        for metric in metrics:
            assert 'fi."certificationDate" >= %(period_start)s' in metric.db_mapping
            assert 'fi."certificationDate" < %(period_end)s' in metric.db_mapping

    def test_catalog_metrics_are_cached(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        a = catalog_repo.list_metrics()
        b = catalog_repo.list_metrics()
        assert a is b  # misma instancia cacheada
