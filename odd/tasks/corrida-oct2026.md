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
- [x] T5 — Full suite green + dry run (see T5 section below)

## Checks

`.venv/bin/python -m pytest -q` (DQS Stop gate requires green)

## TDD

Mode: strict (enabled by session configuration). Runner:
`.venv/bin/python -m pytest -q`. Tests change first, RED is observed, then
source.

## Progress

Route per task: direct inline (mechanical, already-understood literal
migration; the Agent tool is disabled for this session by user instruction).

## T6 — Slide 20 Crecimiento Integral, nueva estructura de cohortes

Declared by the user 2026-10-02. The CI courses were released 2025-04-03 and
stayed unchanged until 2026-06-01, when the course set changed. The previous
catalog shape (46 "mantenidos" + 27 "quitados" = 73 courses) is replaced.

New course lists: A = 85 original courses, B = 53 courses still live after the
change. `B` is a strict subset of `A`; the 2026-06-01 change only retired 32
courses, none were added. The user's pasted list B carried `100359` twice (54
entries, 53 distinct) and was deduplicated.

The three metrics no longer share a window:

| Metric | Shape | Window |
|---|---|---|
| `*_inscripciones` | `COUNT`, two cohorts OR'd | A in `[2025-04-03, 2026-06-01)` + B in `[2026-06-01, 2026-10-01)` |
| `*_personas_unicas_inscritas` | `COUNT(DISTINCT userId)`, one cohort | A in `[2025-04-03, 2026-08-01)` |
| `*_cursos_ofertados` | `COUNT(DISTINCT courseId)`, one cohort | A in `[2025-04-03, 2026-08-01)` |

The `2026-08-01` cutoff on the last two **diverges from the run cutoff on
purpose**: it was raised to the user as a conflict and they chose to keep the
query literal. Consequences recorded so the deck can explain them:

- Those two metrics reach two months less than inscripciones on the same slide.
- Their universe includes the 32 courses retired on 2026-06-01, which the
  inscripciones live cohort excludes.
- The sheet row for personas únicas now carries its own
  `SLIDE20_PERIODO_FIN_UNICAS = "2026-08-01"` instead of the shared
  `SLIDE20_PERIODO_FIN`, so the published period matches the query that ran.
- `test_no_metric_keeps_the_previous_run_cutoff` now asserts an explicit
  two-metric allowlist rather than an empty set, and
  `test_accumulated_metrics_share_the_oct2026_cutoff` drops from 19 to 17.

### Still open on slide 20

`SLIDE20_CONTENIDO = 73` was derived from the old 46+27 list. It has not been
reconciled against the new 85/53 lists and is still painted as a hardcoded KPI.

## Tasks (continued)

- [x] T6 — Slide 20: cohorts split at 2026-06-01, per-row period for únicas
- [ ] T7 — Reconcile `SLIDE20_CONTENIDO` (73) against the new course lists

## T8 — Slide 12 aligned with the control sheet

Source: tab `Slide12_Sep2025 - Sep2026` of spreadsheet
`1K6aej9AFJGBkttvqYWuGVoDqFlJa1mbo7fm1uk6NY0w`.

Route order already matched; 17 of 18 routes were already identical. The only
change is `Convive mejor con otros`, 3 -> 7 courses (adds 305, 100070, 100063,
299), kept at `orden` 12 in Capacitación básica so section blocks stay
contiguous for the subtotal logic.

Course 299 is now the first cross-route duplicate in slide 12. The
zero-duplicates guard was replaced by an explicit sharing allowlist: 114
assignments over 113 distinct courses. Full write-up in
`docs/hallazgos-sep2026.md` H11.

- [x] T8 — Slide 12: Convive mejor con otros 3 -> 7, sharing allowlist
- [x] T9 — DISCARDED by the user 2026-10-02: "Busca tu primer trabajo"
      stays out for now, so "Preparación para buscar trabajo" keeps its 7
      courses and slide 12 closes at 114 assignments / 113 distinct.

## T5 — done (dry run)

`pipeline --cut 2026-10-01 --dry-run` against the real databases: 37 manifests,
DQS 0 issues, bundle hash `a1c55192ab3de961`. Results and the slide-1
reconciliation are in `docs/hallazgos-sep2026.md` H12.

Tasks:

- [x] T5 — Full suite green + dry run
- [x] T10 — Production run: 37 metrics, 87 rows, DQS 0 issues, written to
      "Consejo 2026 - Snapshot Técnico". Verified value-by-value against the
      dry run: 0 differences. See `docs/hallazgos-sep2026.md` H13.
- [ ] T7 — Reconcile `SLIDE20_CONTENIDO` (73) against the new course lists
