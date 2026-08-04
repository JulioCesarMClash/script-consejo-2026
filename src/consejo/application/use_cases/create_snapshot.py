"""Caso de uso: creación de snapshot en Google Sheets.

Verifica que el bundle haya pasado DQS antes de delegar en SheetRepo.
Si el bundle tiene fallos bloqueantes, aborta sin llamar a Sheets.
"""

from __future__ import annotations

from src.consejo.application.ports import SheetRepo
from src.consejo.domain.entities import Bundle


def create_snapshot(
    bundle: Bundle,
    sheet_repo: SheetRepo,
) -> str:
    """Crea o actualiza el snapshot en Google Sheets.

    Args:
        bundle: Bundle validado con hash SHA-256.
        sheet_repo: Repositorio de Sheets para escribir el snapshot.

    Returns:
        El spreadsheet ID devuelto por SheetRepo.snapshot().

    Raises:
        ValueError: Si el bundle contiene fallos DQS bloqueantes.
    """
    blockers = [i for i in bundle.dqs if i.severity == "blocker"]

    if blockers:
        codes = [i.code for i in blockers]
        raise ValueError(
            f"Bundle failed DQS validation with {len(blockers)} blocker(s): "
            f"{', '.join(codes)}. Snapshot blocked."
        )

    return sheet_repo.snapshot(bundle)
