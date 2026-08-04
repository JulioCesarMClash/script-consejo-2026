"""Puertos abstractos para la capa de aplicación.

Protocols que definen los contratos que los adaptadores deben implementar,
permitiendo que los casos de uso dependan de abstracciones, no de concreciones.
"""

from __future__ import annotations

from typing import Mapping, Protocol, Sequence

from src.consejo.domain.entities import Bundle, Metric


class MetricRepo(Protocol):
    """Repositorio de métricas del catálogo."""

    def list_metrics(self) -> Sequence[Metric]:
        """Devuelve todas las métricas del catálogo."""
        ...


class SourceConn(Protocol):
    """Conexión a fuente de datos para extracción parametrizada."""

    def fetch(
        self, sql: str, params: Mapping[str, object]
    ) -> Sequence[Mapping[str, object]]:
        """Ejecuta una consulta SQL parametrizada y devuelve las filas."""
        ...


class SheetRepo(Protocol):
    """Repositorio de Google Sheets para snapshot."""

    def snapshot(self, bundle: Bundle) -> str:
        """Crea o actualiza las 5 hojas del snapshot. Retorna spreadsheet ID."""
        ...


class SlidesRepo(Protocol):
    """Repositorio de Google Slides para publicación futura.

    Marcado como futuro: no se implementa en este alcance.
    """

    def publish(self, bundle: Bundle, copy_id: str) -> str:
        """Publica el bundle en una copia de Slides. No implementado aún."""
        raise NotImplementedError(
            "SlidesRepo.publish no está implementado — "
            "la publicación sobre Slides es un alcance futuro."
        )
