"""Value objects inmutables del dominio del pipeline de snapshot.

Tipos sin identidad propia que representan valores del negocio:
- IDs y hashes con validación estricta.
- Estados del ciclo de vida de extracción y corrida.
- Enumeraciones para fuentes de datos y cortes temporales.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import date as Date
from enum import Enum, auto


# ── Enumeraciones ───────────────────────────────────────────────────────────


class MetricSource(str, Enum):
    """Fuente de extracción de una métrica según el catálogo."""

    DIM_USER = "dim_user"
    FACT_INSCRIPTION = "fact_inscription"
    MANUAL = "manual"


class FetchStatus(str, Enum):
    """Estado de extracción de un manifiesto individual."""

    EMPTY = "empty"
    EXTRACTED = "extracted"
    FAILED = "failed"


class RunState(str, Enum):
    """Estados del ciclo de vida de una corrida de snapshot."""

    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    VALIDATING = "validating"
    READY_FOR_REVIEW = "ready_for_review"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    PUBLISHED = "published"


# ── Terminal state check ────────────────────────────────────────────────────


TERMINAL_STATES: frozenset[RunState] = frozenset(
    {RunState.BLOCKED, RunState.FAILED, RunState.SUPERSEDED, RunState.PUBLISHED}
)


def is_terminal_state(state: RunState) -> bool:
    """Indica si un estado de corrida es terminal y no debe reabrirse."""
    return state in TERMINAL_STATES


# ── Value Objects ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MetricId:
    """Identificador de una métrica del catálogo (key única)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("MetricId no puede ser vacío")

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class RunId:
    """Identificador único de una corrida de snapshot (UUID v4)."""

    value: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            object.__setattr__(self, "value", uuid.UUID(str(self.value)))
        if self.value.version != 4:
            raise ValueError("RunId debe ser UUID v4")

    @classmethod
    def generate(cls) -> RunId:
        """Genera un nuevo RunId v4."""
        return cls(value=uuid.uuid4())

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class AttemptId:
    """Identificador único de un intento dentro de una corrida (UUID v4)."""

    value: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.value, uuid.UUID):
            object.__setattr__(self, "value", uuid.UUID(str(self.value)))
        if self.value.version != 4:
            raise ValueError("AttemptId debe ser UUID v4")

    @classmethod
    def generate(cls) -> AttemptId:
        """Genera un nuevo AttemptId v4."""
        return cls(value=uuid.uuid4())

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class HashSha256:
    """Hash SHA-256 en representación hexadecimal (64 caracteres)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("HashSha256 no puede ser vacío")
        if len(self.value) != 64:
            raise ValueError(
                f"HashSha256 debe tener 64 caracteres hex, "
                f"recibidos {len(self.value)}"
            )
        try:
            int(self.value, 16)
        except ValueError:
            raise ValueError(
                f"HashSha256 debe ser hexadecimal, "
                f"recibido '{self.value[:20]}...'"
            )

    @classmethod
    def from_bytes(cls, data: bytes) -> HashSha256:
        """Construye un HashSha256 a partir de datos binarios."""
        return cls(value=hashlib.sha256(data).hexdigest())

    @classmethod
    def from_str(cls, data: str) -> HashSha256:
        """Construye un HashSha256 a partir de una cadena UTF-8."""
        return cls.from_bytes(data.encode("utf-8"))

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class Cut:
    """Fecha de corte del snapshot. No puede estar en el futuro."""

    value: Date

    def __post_init__(self) -> None:
        if not isinstance(self.value, Date):
            object.__setattr__(
                self, "value", Date.fromisoformat(str(self.value))
            )
        today = Date.today()
        if self.value > today:
            raise ValueError(
                f"Cut no puede estar en el futuro: "
                f"{self.value.isoformat()} > {today.isoformat()}"
            )

    @classmethod
    def from_iso(cls, date_str: str) -> Cut:
        """Construye un Cut desde una fecha ISO 8601 (YYYY-MM-DD)."""
        return cls(value=Date.fromisoformat(date_str))

    def isoformat(self) -> str:
        """Representación ISO 8601."""
        return self.value.isoformat()

    def __str__(self) -> str:
        return self.isoformat()

    def __hash__(self) -> int:
        return hash(self.value)
