"""Adaptador YAML para MetricRepo.

Lee el catálogo de métricas desde un archivo YAML y expone las métricas
como instancias del dominio.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Sequence

import yaml

from src.consejo.application.ports import MetricRepo
from src.consejo.domain.entities import Metric
from src.consejo.domain.value_objects import MetricId, MetricSource


class YamlMetricRepo(MetricRepo):
    """Repositorio de métricas que lee desde un archivo YAML."""

    def __init__(self, catalog_path: str) -> None:
        self._catalog_path = Path(catalog_path)
        self._metrics: list[Metric] | None = None

    def list_metrics(self) -> Sequence[Metric]:
        """Carga y cachea las métricas del catálogo YAML."""
        if self._metrics is not None:
            return self._metrics

        with open(self._catalog_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        raw_metrics: list[dict] = raw.get("metrics", [])
        self._metrics = [_parse_metric(m) for m in raw_metrics]
        return self._metrics

    def compute_catalog_hash(self) -> str:
        """Calcula el hash SHA-256 del contenido del catálogo."""
        metrics = list(self.list_metrics())
        payload = "|".join(
            f"{m.key}:{m.source.value}:{m.db_mapping}"
            for m in sorted(metrics, key=lambda m: m.key)
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_metric(raw: dict) -> Metric:
    """Convierte una entrada YAML en un objeto Metric del dominio."""
    source_str = raw.get("source", "manual")
    source = MetricSource(source_str)
    scope_raw = raw.get("platform_scope", [])
    platform_scope: list[str] = [str(s) for s in scope_raw]
    grain = _infer_grain(raw.get("key", ""), source_str)

    return Metric(
        id=MetricId(raw["key"]),
        name=raw.get("name", ""),
        key=raw["key"],
        source=source,
        formula=raw.get("formula", ""),
        db_mapping=raw.get("db_mapping", ""),
        platform_scope=platform_scope,
        grain=grain,
        db_source=raw.get("db_source", "postgres"),
    )


def _infer_grain(key: str, source_str: str) -> str:
    """Infiere el grano de una métrica según su key y fuente."""
    if "registered" in key:
        return "usuario distinto × plataforma de origen"
    if "beneficiaries" in key:
        return "declaración × corte, sin valor"
    if "inscriptions_cpe" in key and "total" in key:
        return "evento de inscripción × origen"
    if "inscriptions" in key:
        return "evento de inscripción × origen"
    if "inscribed_unique" in key:
        return "usuario distinto × origen"
    if "certified_unique" in key and "total" in key:
        return "usuario distinto × origen"
    if "certified_unique" in key:
        return "usuario distinto × origen"
    if "certifications" in key and "total" in key:
        return "evento × origen"
    if "certifications" in key:
        return "evento × origen"
    if "empleo_incluyente" in key:
        return "usuario distinto × curso × sector"
    if key.startswith("slide"):
        return "categoría × período"
    return "desconocido"
