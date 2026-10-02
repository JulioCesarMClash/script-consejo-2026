# Corrida de cierre Sep 2026 (corte 2026-10-01)

## Objective

Move the whole pipeline cutoff from `2026-08-01` to `2026-10-01` and set the
reporting window to 13 months: `2025-09-01` .. `2026-10-01` (Sep 2025 through
Sep 2026 inclusive, upper bound exclusive).

## Problem

Dates live in four places and none of them share a single source of truth:

1. `.env` / `Settings` — `CERTIFICATE_PERIOD_START` / `CERTIFICATE_PERIOD_END`,
   consumed as `%(period_start)s` / `%(period_end)s` by slide 1, slide 2 and
   the four `certifications_cpe*` metrics.
2. `data/catalogo-metricas.yaml` — 19 metrics carry the cutoff as a hardcoded
   SQL literal `'2026-08-01'` (accumulated metrics: slides 12, 13, 15, 19, 20
   and the fixed windows of slides 3 and 4).
3. `src/consejo/adapters/sheets/google_mcp_sheet_repo.py` — per-slide
   `SLIDE*_PERIODO_FIN` label constants plus the December projection month
   counters.
4. Tests mirror all of the above as literals.

## Scope (authorized)

- `.env`, `src/consejo/config/settings.py`
- `data/catalogo-metricas.yaml`, `data/mapping-slides.yaml`
- `src/consejo/adapters/sheets/google_mcp_sheet_repo.py`
- `tests/**`

## Out of scope (left untouched, flagged to the user)

- `2026-06-01` in `slide20_*` — the "quitados" course sub-window is its own
  business rule, not the run cutoff.
- `2025-04-03` (`SLIDE20_PERIODO_INICIO`) — crecimiento integral start date.
- `SLIDE13_CENTROS`, the hardcoded Pilotos value in `_build_slide4_block`.
- The December projection factor disagreement between this repo (`12/9` after
  this change) and the Apps Script side (`1.025`).

## Tasks

- [x] T1 — Period window: `.env` + `Settings` defaults to 2025-09-01 / 2026-10-01
- [x] T2 — Catalog: 19 `db_mapping` cutoffs + caveats/notes prose
- [x] T3 — Sheet repo: `SLIDE*_PERIODO_FIN` labels + projection months (7/5 -> 9/3)
- [x] T4 — Fixtures and docs coherence (`mapping-slides.yaml`, pipeline fixtures)
- [ ] T5 — Full suite green + dry run

## Checks

`.venv/bin/python -m pytest -q` (DQS Stop gate requires green)

## TDD

Mode: strict (enabled by session configuration). Runner:
`.venv/bin/python -m pytest -q`. Tests change first, RED is observed, then
source.

## Progress

Route per task: direct inline (mechanical, already-understood literal
migration; the Agent tool is disabled for this session by user instruction).
