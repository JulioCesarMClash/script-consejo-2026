"""Fixtures compartidos para todos los tests del pipeline."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_path_fixture(tmp_path: Path) -> Path:
    """Directorio temporal aislado por test."""
    return tmp_path


@pytest.fixture
def sample_catalog_path() -> Path:
    """Ruta al catálogo de métricas YAML usado en tests."""
    return Path(__file__).resolve().parent.parent / "data" / "catalogo-metricas.yaml"

