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

    # Cursos que pertenecen a más de una ruta de slide 12, con las rutas que
    # los comparten. Declarado por el usuario 2026-10-02 al alinear el
    # catálogo con la hoja "Slide12_Sep2025 - Sep2026". Cada entrada infla el
    # TOTAL de la slide (suma de subtotales por sección), así que la lista se
    # mantiene explícita para que un duplicado accidental no pase inadvertido.
    SLIDE12_SHARED_COURSES = {
        299: {"¿Cómo mejorar mi entorno?", "Convive mejor con otros"},
    }

    def test_slide12_course_assignments_match_the_declared_sharing(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Slide 12 — solo los cursos declarados pertenecen a varias rutas.

        El TOTAL de la slide es la suma de los subtotales por sección, así que
        un curso en dos rutas se cuenta dos veces tanto en inscripciones como
        en certificados. Por eso el reparto se fija acá: 114 asignaciones
        sobre 113 cursos distintos, y el único compartido es 299.
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

        por_curso: dict[int, set[str]] = {}
        for ruta, ids in rutas:
            for i in ids.split(","):
                por_curso.setdefault(int(i), set()).add(ruta)

        asignaciones = sum(len(v) for v in por_curso.values())
        assert asignaciones == 114
        assert len(por_curso) == 113

        compartidos = {c: r for c, r in por_curso.items() if len(r) > 1}
        assert compartidos == self.SLIDE12_SHARED_COURSES

        assert "Compras y pagos digitales" not in sql
        assert "curso_ids_conteo" not in sql
        assert 'ANY(r.curso_ids)' in sql

    def test_slide12_has_empleabilidad_and_convivencia_routes(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Slide 12 — rutas "Preparación para buscar trabajo" (Emprendimiento)
        y "Convive mejor con otros" (Capacitación básica).

        De los cursos duplicados en la tabla `course` se toma el ID vivo: 67
        (Guía para entrevistas) y 212 (Disciplina en el trabajo); 329 y 330
        quedaron sin inscripciones nuevas.

        El reparto exacto de cursos compartidos vive en
        `test_slide12_course_assignments_match_the_declared_sharing`: desde el
        2026-10-02 Convive comparte 299 con "¿Cómo mejorar mi entorno?".

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
        assert [int(i) for i in convive[3].split(",")] == [
            100330, 100380, 100381, 305, 100070, 100063, 299,
        ]

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
        entre slides sin que nadie lo note.

        Las dos métricas de Crecimiento Integral que habían quedado en
        '2026-08-01' se alinearon el 2026-10-05 a pedido del usuario, tras
        ver la divergencia en la hoja.
        """
        stale = {
            m.key
            for m in catalog_repo.list_metrics()
            if "2026-08-01" in (m.db_mapping or "")
        }

        assert stale == set()

    def test_accumulated_metrics_share_the_oct2026_cutoff(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Las 19 métricas con corte duro de la corrida usan '2026-10-01'.

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
        # Las 3 métricas de slide 20 comparten el corte de la corrida.
        for key in (
            "slide20_crecimiento_integral_inscripciones",
            "slide20_crecimiento_integral_personas_unicas_inscritas",
            "slide20_crecimiento_integral_cursos_ofertados",
        ):
            assert key in with_cutoff

    def test_slide20_inscripciones_splits_at_the_course_change(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Slide 20 parte la ventana el 2026-06-01, cuando cambiaron los cursos.

        Los cursos de Crecimiento Integral se liberaron el 2025-04-03 y se
        mantuvieron iguales hasta el 2026-06-01. Desde ese día el catálogo
        cambió, por lo que la cuenta es:

            85 cursos originales en [2025-04-03, 2026-06-01)
          + 53 cursos vigentes   en [2026-06-01, 2026-10-01)

        Las dos ventanas son disjuntas, así que cada inscripción cae en
        exactamente una y `COUNT` no duplica.
        """
        metric = next(
            m
            for m in catalog_repo.list_metrics()
            if m.key == "slide20_crecimiento_integral_inscripciones"
        )
        sql = metric.db_mapping

        cohorts = re.findall(r'IN \(([\d,\s]+)\)', sql)
        assert len(cohorts) == 2
        originales = [int(i) for i in cohorts[0].split(",")]
        vigentes = [int(i) for i in cohorts[1].split(",")]

        assert len(originales) == 85
        assert len(set(originales)) == 85
        assert len(vigentes) == 53
        assert len(set(vigentes)) == 53
        # La lista vigente es un subconjunto de la original: el 2026-06-01
        # solo se retiraron cursos, no se agregaron.
        assert set(vigentes) < set(originales)
        assert len(set(originales) - set(vigentes)) == 32

        # Ventanas disjuntas y contiguas.
        assert (
            "fi.\"inscripcionDate\" >= '2025-04-03' "
            "AND fi.\"inscripcionDate\" < '2026-06-01'"
        ) in sql
        assert (
            "fi.\"inscripcionDate\" >= '2026-06-01' "
            "AND fi.\"inscripcionDate\" < '2026-10-01'"
        ) in sql

        # Inscripciones = filas, no personas.
        assert 'COUNT(fi."userId")' in sql
        assert "DISTINCT" not in sql
        assert 'du."plataformaId" = 2' in sql

    def test_slide20_retired_courses_are_absent_after_the_change(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Los 32 cursos retirados no entran en la ventana post 2026-06-01."""
        metric = next(
            m
            for m in catalog_repo.list_metrics()
            if m.key == "slide20_crecimiento_integral_inscripciones"
        )
        vigentes = {
            int(i)
            for i in re.findall(r'IN \(([\d,\s]+)\)', metric.db_mapping)[1]
            .split(",")
        }

        retirados = {
            100109, 100360, 100390, 100660, 100695, 100696, 100697, 100698,
            100699, 100700, 100701, 100702, 100703, 100704, 100705, 100706,
            100707, 100708, 100709, 100710, 100712, 100713, 100714, 100715,
            100716, 100717, 100718, 100719, 100722, 100723, 100724, 100725,
        }

        assert vigentes & retirados == set()

    def test_slide20_unicas_uses_the_literal_single_window(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Personas únicas de slide 20 queda en una sola ventana.

        A diferencia de inscripciones, que se parte en el cambio de cursos
        del 2026-06-01, personas únicas usa los 85 cursos originales en una
        sola ventana, tal cual la query declarada por el usuario.

        El corte se alineó el 2026-10-05 con el resto de la corrida: había
        quedado en '2026-08-01' y el usuario lo corrigió a '2026-10-01' al
        revisar la hoja. El universo sigue incluyendo los 32 cursos
        retirados en junio, que es la diferencia con inscripciones.
        """
        metric = next(
            m
            for m in catalog_repo.list_metrics()
            if m.key
            == "slide20_crecimiento_integral_personas_unicas_inscritas"
        )
        sql = metric.db_mapping

        cohorts = re.findall(r'IN \(([\d,\s]+)\)', sql)
        assert len(cohorts) == 1, "una sola ventana, sin partir en junio"
        cursos = [int(i) for i in cohorts[0].split(",")]
        assert len(cursos) == 85
        assert len(set(cursos)) == 85

        assert 'COUNT(DISTINCT fi."userId")' in sql
        assert 'du."plataformaId" = 2' in sql
        assert "fi.\"inscripcionDate\" >= '2025-04-03'" in sql
        assert "fi.\"inscripcionDate\" < '2026-10-01'" in sql
        assert "2026-08-01" not in sql
        # Sin el OR de dos cohortes no hay riesgo de doble conteo, pero el
        # universo incluye los 32 cursos retirados en junio.
        assert " OR " not in sql

    def test_slide20_cursos_ofertados_follows_unicas(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """Cursos ofertados comparte ventana y universo con personas únicas."""
        unicas, ofertados = (
            next(
                m
                for m in catalog_repo.list_metrics()
                if m.key == key
            )
            for key in (
                "slide20_crecimiento_integral_personas_unicas_inscritas",
                "slide20_crecimiento_integral_cursos_ofertados",
            )
        )

        assert 'COUNT(DISTINCT fi."courseId")' in ofertados.db_mapping
        assert re.findall(r'IN \(([\d,\s]+)\)', ofertados.db_mapping) == (
            re.findall(r'IN \(([\d,\s]+)\)', unicas.db_mapping)
        )
        assert "fi.\"inscripcionDate\" < '2026-10-01'" in ofertados.db_mapping

    def test_slide12_convivencia_matches_the_control_sheet(
        self, catalog_repo: YamlMetricRepo
    ) -> None:
        """"Convive mejor con otros" sigue el orden de la hoja de control.

        La hoja "Slide12_Sep2025 - Sep2026" la trae escrita dos veces: un
        bloque viejo con 3 cursos en su posición y uno nuevo al final con los
        3 originales más 4 agregados. El usuario confirmó el 2026-10-02 que el
        bloque de abajo era un agregado, no un reordenamiento: la ruta se queda
        en el orden 12 dentro de Capacitación básica para que las secciones
        sigan contiguas y los subtotales de la hoja no se dupliquen.
        """
        metric = next(
            m for m in catalog_repo.list_metrics()
            if m.key == "slide12_rutas_aprendizaje"
        )
        rutas = re.findall(
            r"\((\d+), '([^']+)', '([^']+)', ARRAY\[([\d,\s]+)\]::bigint\[\]\)",
            metric.db_mapping,
        )
        by_ruta = {r[2]: r for r in rutas}

        convive = by_ruta["Convive mejor con otros"]
        assert int(convive[0]) == 12
        assert convive[1] == "Capacitación básica"
        # Orden exacto de la hoja: los 3 originales y después los 4 nuevos.
        assert [int(i) for i in convive[3].split(",")] == [
            100330, 100380, 100381, 305, 100070, 100063, 299,
        ]

        # Las secciones ocupan órdenes consecutivos: el bloque de la hoja
        # emite un subtotal cada vez que cambia de sección.
        secciones = [r[1] for r in sorted(rutas, key=lambda r: int(r[0]))]
        bloques = [s for i, s in enumerate(secciones) if i == 0 or s != secciones[i - 1]]
        assert len(bloques) == len(set(bloques))
