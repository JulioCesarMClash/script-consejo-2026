"""Tests de integración para YamlMetricRepo con catálogo real.

Verifica que el catálogo YAML se lea correctamente, exponga 16 métricas,
identifique correctamente las plataformas y fuentes manuales.
"""

import re
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
        assert len(metrics) == 37

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
        assert len(dim_user) == 8
        dim_keys = {m.key for m in dim_user}
        assert dim_keys == {
            "registered_cpe",
            "registered_aprende",
            "registered_total",
            "slide3_capacitate_carso",
            "slide3_academica_labs",
            "slide4_cultura_salud_aprende",
            "slide15_mario_molina_vistas",
            "slide13_penitenciarios_usuarios_registrados",
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
            # Slide 3 usa ventanas FIJAS de cuatro columnas, sin period_start/end.
            assert "%(period_start)s" not in m.db_mapping
            assert "%(period_end)s" not in m.db_mapping
            assert '"2025"' in m.db_mapping
            assert '"sep2026"' in m.db_mapping
            assert '"acumulado"' in m.db_mapping
            assert '"base_dic2026"' in m.db_mapping
            assert "'2000-01-01'" in m.db_mapping
            assert "'2025-01-01'" in m.db_mapping
            assert "'2026-10-01'" in m.db_mapping
            assert "'2027-01-01'" in m.db_mapping

    def test_postgres_metrics_have_db_source_postgres(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        postgres = [m for m in metrics if m.key in {
            "slide4_cultura_salud_aprende",
        }]
        assert len(postgres) == 1
        for m in postgres:
            assert m.db_source == "postgres"
            assert m.db_mapping.strip().startswith("SELECT")
            # Slide 4 usa ventanas FIJAS de cuatro columnas, sin period_start/end.
            # sep2026, dic2026 y acumulado usan todos el corte 2026-10-01 (alineado con slide3).
            assert "%(period_start)s" not in m.db_mapping
            assert "%(period_end)s" not in m.db_mapping
            assert '"2025"' in m.db_mapping
            assert '"sep2026"' in m.db_mapping
            assert '"dic2026"' in m.db_mapping
            assert '"acumulado"' in m.db_mapping
            assert "'2025-01-01'" in m.db_mapping
            assert "'2026-10-01'" in m.db_mapping

    def test_finds_fact_inscription_metrics(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        fact = [
            m
            for m in metrics
            if m.source == MetricSource.FACT_INSCRIPTION
        ]
        assert len(fact) == 29  # 17 + slide12 + 3 slide13 (insc,cert,cursos; usuarios ahora dim_user) + 1 slide15 + 4 slide19 + 3 slide20 (insc, personas, cursos_ofertados) + 1 slide4_aprende(PG)

    def test_platform_scope_cpe(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        metrics = list(catalog_repo.list_metrics())
        cpe = [m for m in metrics if "cpe" in m.platform_scope]
        assert len(cpe) == 23  # 23 de 38 incluyen cpe; las 2 MySQL, 2 slide4, 4 slide13, slide15_vistas, registered_aprende y las 2 slide20 (scope=[aprende] desde 2026-08-19 tras la query buena sin filtro de platformId del curso) no

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

    def test_slide12_has_no_duplicated_courses(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Slide 12 — cada curso pertenece a UNA sola ruta.

        Sin cursos repetidos, el TOTAL de la slide (suma de subtotales por
        sección) no cuenta dos veces las inscripciones ni los certificados,
        así que la SQL cuenta todos los cursos de cada ruta y no necesita un
        array de conteo aparte.
        """
        metric = next(
            m for m in catalog_repo.list_metrics()
            if m.key == "slide12_rutas_aprendizaje"
        )
        sql = metric.db_mapping

        rutas = re.findall(
            r"\(\d+, '[^']+', '([^']+)', ARRAY\[([\d,\s]+)\]::bigint\[\]\)",
            sql,
        )
        assert len(rutas) == 18

        asignaciones = [
            int(i) for _, ids in rutas for i in ids.split(",")
        ]
        assert len(asignaciones) == len(set(asignaciones))

        assert "Compras y pagos digitales" not in sql
        assert "curso_ids_conteo" not in sql
        assert 'ANY(r.curso_ids)' in sql

    def test_slide12_has_empleabilidad_and_convivencia_routes(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Slide 12 — rutas "Preparación para buscar trabajo" (Emprendimiento)
        y "Convive mejor con otros" (Capacitación básica).

        Ninguno de sus 10 cursos pertenece a otra ruta de la slide. De los cursos
        duplicados en la tabla `course` se toma el ID vivo: 67 (Guía para
        entrevistas) y 212 (Disciplina en el trabajo); 329 y 330 quedaron sin
        inscripciones nuevas.

        Las secciones se mantienen contiguas por `orden` porque el bloque de
        la hoja emite un subtotal al detectar un cambio de sección.
        """
        metric = next(
            m for m in catalog_repo.list_metrics()
            if m.key == "slide12_rutas_aprendizaje"
        )
        rutas = re.findall(
            r"\((\d+), '([^']+)', '([^']+)', ARRAY\[([\d,\s]+)\]::bigint\[\]\)",
            metric.db_mapping,
        )
        assert len(rutas) == 18

        by_ruta = {r[2]: r for r in rutas}
        buscar = by_ruta["Preparación para buscar trabajo"]
        assert buscar[1] == "Emprendimiento"
        assert [int(i) for i in buscar[3].split(",")] == [
            67, 212, 216, 227, 228, 100059, 100853,
        ]

        convive = by_ruta["Convive mejor con otros"]
        assert convive[1] == "Capacitación básica"
        assert [int(i) for i in convive[3].split(",")] == [100330, 100380, 100381]

        # Los IDs retirados no entran.
        assert "329" not in buscar[3] and "330" not in buscar[3]

        # Cada sección ocupa órdenes consecutivos (requisito de los subtotales).
        secciones = [r[1] for r in sorted(rutas, key=lambda r: int(r[0]))]
        assert secciones == list(dict.fromkeys(secciones)) or all(
            secciones.index(s) + secciones.count(s) - 1
            == len(secciones) - 1 - secciones[::-1].index(s)
            for s in set(secciones)
        )

    def test_no_metric_keeps_the_previous_run_cutoff(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Ninguna métrica conserva el corte de la corrida anterior.

        La corrida de cierre Sep 2026 mueve el corte duro de '2026-08-01'
        a '2026-10-01'. Un literal viejo sobreviviente mezclaría ventanas
        entre slides.
        """
        stale = [
            m.key
            for m in catalog_repo.list_metrics()
            if "2026-08-01" in (m.db_mapping or "")
        ]

        assert stale == []

    def test_accumulated_metrics_share_the_oct2026_cutoff(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Las 19 métricas con corte duro usan todas '2026-10-01'.

        Las demás derivan su ventana de `%(period_start)s`/`%(period_end)s`
        (slides 1 y 2 y las certificaciones) o no tienen corte.
        """
        with_cutoff = sorted(
            m.key
            for m in catalog_repo.list_metrics()
            if "'2026-10-01'" in (m.db_mapping or "")
        )

        assert len(with_cutoff) == 19
        assert "slide12_rutas_aprendizaje" in with_cutoff
        assert "slide3_capacitate_carso" in with_cutoff
        assert "slide4_aprende_seguridad_vial" in with_cutoff
