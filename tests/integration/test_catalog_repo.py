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

    def test_returns_16_metrics(self, catalog_repo: YamlMetricRepo) -> None:
        metrics = list(catalog_repo.list_metrics())
        assert len(metrics) == 16

    def test_metrics_have_unique_keys(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        keys = [m.key for m in metrics]
        assert len(keys) == len(set(keys))

    def test_finds_manual_metrics(self, catalog_repo: YamlMetricRepo) -> None:
        metrics = list(catalog_repo.list_metrics())
        manual = [m for m in metrics if m.source == MetricSource.MANUAL]
        assert len(manual) == 2
        manual_keys = {m.key for m in manual}
        assert manual_keys == {"beneficiaries", "beneficiaries_unique"}

    def test_finds_dim_user_metrics(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        dim_user = [m for m in metrics if m.source == MetricSource.DIM_USER]
        assert len(dim_user) == 3
        dim_keys = {m.key for m in dim_user}
        assert dim_keys == {
            "registered_cpe",
            "registered_aprende",
            "registered_total",
        }

    def test_finds_fact_inscription_metrics(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        fact = [
            m
            for m in metrics
            if m.source == MetricSource.FACT_INSCRIPTION
        ]
        assert len(fact) == 11

    def test_platform_scope_cpe(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        cpe = [m for m in metrics if "cpe" in m.platform_scope]
        assert len(cpe) == 15  # 15 de 16 incluyen cpe; solo registered_aprende no

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

    def test_catalog_metrics_are_cached(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        a = catalog_repo.list_metrics()
        b = catalog_repo.list_metrics()
        assert a is b  # misma instancia cacheada
