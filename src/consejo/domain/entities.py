"""Entidades del dominio del pipeline de snapshot.

Entidades con identidad propia:
- Metric: definición de una métrica del catálogo.
- SourceManifest: resultado de extracción de una fuente.
- Run: corrida de extracción/validación con estado y manifiestos.
- Bundle: paquete canónico con datos, DQS y hash.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date as Date
from datetime import datetime, timezone
from typing import Any, Sequence

from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    FetchStatus,
    HashSha256,
    MetricId,
    MetricSource,
    RunId,
    RunState,
    is_terminal_state,
)


# ── Metric ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Metric:
    """Definición canónica de una métrica según el catálogo."""

    id: MetricId
    name: str
    key: str
    source: MetricSource
    formula: str
    db_mapping: str
    platform_scope: list[str] = field(default_factory=list)
    grain: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Metric name no puede ser vacío")
        if not self.key or not self.key.strip():
            raise ValueError("Metric key no puede ser vacío")


# ── SourceManifest ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SourceManifest:
    """Resultado de extracción de una métrica desde una fuente específica."""

    metric_id: MetricId
    source: MetricSource
    cut: Cut
    fetched_at: datetime
    freshness_hours: float
    rows: Sequence[dict[str, Any]] = field(default_factory=tuple)
    status: FetchStatus = FetchStatus.EMPTY

    def __post_init__(self) -> None:
        if self.fetched_at.tzinfo is None:
            object.__setattr__(
                self, "fetched_at", self.fetched_at.replace(tzinfo=timezone.utc)
            )
        if self.freshness_hours < 0:
            raise ValueError("freshness_hours no puede ser negativo")
        if self.source == MetricSource.MANUAL and self.rows:
            raise ValueError(
                "SourceManifest manual no debe contener filas con valores; "
                "el valor debe ser nulo/ausente"
            )


# ── Run ─────────────────────────────────────────────────────────────────────


@dataclass
class Run:
    """Corrida de snapshot con estado y manifiestos asociados."""

    run_id: RunId
    attempt_id: AttemptId
    state: RunState
    cut: Cut
    catalog_hash: str = ""
    manifests: list[SourceManifest] = field(default_factory=list)

    def transition_to(self, new_state: RunState) -> None:
        """Transiciona la corrida a un nuevo estado.

        Los estados terminales no pueden reabrirse.
        """
        if is_terminal_state(self.state):
            raise ValueError(
                f"No se puede transicionar desde estado terminal "
                f"'{self.state.value}'. Crear un nuevo intento."
            )
        if new_state == self.state:
            raise ValueError(
                f"La corrida ya está en estado '{self.state.value}'"
            )
        self.state = new_state


# ── DqsIssue ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DqsIssue:
    """Registro de un fallo DQS en una obligación específica."""

    obligation: int
    code: str
    severity: str  # "blocker" | "warning"
    message: str
    details: dict[str, Any] = field(default_factory=dict)


# ── Bundle ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Bundle:
    """Paquete canónico de un intento de snapshot.

    Contiene datos normalizados, resultados DQS y hash SHA-256.
    El hash se calcula excluyendo el propio campo `hash` para lograr
    idempotencia real.
    """

    run_id: RunId
    attempt_id: AttemptId
    cut: Cut
    catalog_hash: str
    manifests: Sequence[SourceManifest] = field(default_factory=tuple)
    rows: Sequence[dict[str, Any]] = field(default_factory=tuple)
    dqs: Sequence[DqsIssue] = field(default_factory=tuple)
    hash: HashSha256 = field(default_factory=lambda: HashSha256("0" * 64))

    def compute_hash(self) -> HashSha256:
        """Calcula el hash SHA-256 del bundle excluyendo el campo hash."""
        payload = self._canonical_dict(exclude_hash=True)
        canonical_json = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return HashSha256.from_str(canonical_json)

    def _canonical_dict(self, exclude_hash: bool = False) -> dict[str, Any]:
        """Representación en diccionario con claves canónicas ordenadas."""
        result: dict[str, Any] = {
            "attempt_id": str(self.attempt_id),
            "catalog_hash": self.catalog_hash,
            "cut": self.cut.isoformat(),
            "dqs": [
                {
                    "code": i.code,
                    "details": dict(sorted(i.details.items())),
                    "message": i.message,
                    "obligation": i.obligation,
                    "severity": i.severity,
                }
                for i in self.dqs
            ],
            "manifests": [
                {
                    "cut": m.cut.isoformat(),
                    "fetched_at": m.fetched_at.isoformat(),
                    "freshness_hours": m.freshness_hours,
                    "metric_id": str(m.metric_id),
                    "rows": list(m.rows),
                    "source": m.source.value,
                    "status": m.status.value,
                }
                for m in self.manifests
            ],
            "rows": list(self.rows),
            "run_id": str(self.run_id),
        }
        if not exclude_hash:
            result["hash"] = str(self.hash)
        return result

    def canonical_json(self) -> str:
        """Devuelve la representación canónica JSON UTF-8 del bundle."""
        return json.dumps(
            self._canonical_dict(exclude_hash=False),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":")
        )
