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

## T11 — Slide 20 personas únicas realigned to the run cutoff (2026-10-05)

The user spotted the `2026-08-01` in the snapshot sheet and asked for
`2026-10-01`, reversing the 2026-10-02 literal-query decision. Both
`personas_unicas_inscritas` and `cursos_ofertados` moved, since they share the
window by design. The single-window structure stays: the real difference from
inscripciones is the 32 retired courses, never the date.

`SLIDE20_PERIODO_FIN_UNICAS` was removed; the guard allowlist is empty again and
the oct2026 cutoff count is back to 19. Write-up in H14.

- [x] T11 — Realign slide 20 únicas/ofertados to 2026-10-01
- [x] T12 — Re-ran production: 37 metrics, 87 rows, DQS 0 issues. Personas
      únicas 17,372 -> 19,361 (+11.4%). The other 40 changed rows are source
      drift over 3 days, confirmed by diffing the catalog between runs: only
      the 2 slide20 queries changed. See H15.
- [ ] T13 — Watch the `slide4_cultura_salud_aprende` decrement (-428 on an
      accumulated COUNT(DISTINCT), source-side, not ours)

## T14 — Slide 2 gains the "Convivir mejor con otros" sector (2026-10-05)

6 -> 7 sectors, 30 -> 38 courses. All 8 course IDs already existed elsewhere in
the catalog; none is new. Resolved two name-duplicate IDs by dominance and
liveness (305 over 297/331/100109/100711/100907; 100063 over 100704), matching
slide 12's choices.

Slide 2 groups by `c.name`, so same-name IDs would merge into one row — verified
no collisions. Added a guard that each course belongs to exactly one sector,
since the `CASE` silently prefers the first matching branch.

- [x] T14 — Slide 2: new sector with 8 courses
- [x] T16 — Slide 2 final list: 37 courses, course 27 removed (H17)
- [x] T17 — Fix: `Datos` clear range covered 8 columns while the widest
      block writes 9, leaving 26 stale cells in column I (H18). The width is
      now derived from the `*_TABLE_HEADERS` constants.
- [x] T15 — Re-ran production (`bundle_hash e16ddcf4`): 37 metrics, 94 rows,
      DQS 0 issues, 0 stale cells. Slide 2 TOTAL 54,145 across 7 sectors.

## T18 — Course 299 leaves the Convive route (2026-10-06)

The real pobreza-extrema certificate total is 2,302,728 (the 113 distinct
courses), not the 2,307,998 the sheet showed: course 299 sat in two routes and
its 5,270 certifications entered the section-subtotal sum twice. It now lives
only in "¿Cómo mejorar mi entorno?" and the strict no-duplicates invariant is
back: 113 assignments over 113 distinct courses. Write-up in H19.

- [x] T18 — 299 removed from "Convive mejor con otros" (6 courses now)
- [ ] T19 — Re-run production so the sheet TOTAL reads 2,302,728

## T20 — Duplicate audit on slides 1 and 2 (2026-10-06)

No duplicate courses in either: slide 1 is 101/101 across 5 categories, slide 2
is 37/37 across 7 sectors. Nothing to deduplicate. Slide 1's `compartidos`
literals (summing 12) are an editorial count of conceptual overlap, not repeated
array entries — the overlap was already resolved by assigning each course to one
category (see the course-342 caveat).

What the audit did surface: both slides' TOTAL inflates people, because it sums
`COUNT(DISTINCT userId)` per group. Slide 1 publishes 237,691 against 208,815
real people (+13.8%); slide 2 publishes 54,145 against 43,461 (+24.6%). Not
changed — the per-course grain is what the deck asked for — but it matters if
either figure is presented as "personas beneficiadas". Write-up in H20.

- [x] T20 — Audit slides 1 and 2 for duplicates; added 2 guards
- [ ] T21 — Decide whether the deck needs a "personas únicas" figure alongside
      the summed TOTAL for slides 1 and 2

## T22 — Course 299 relocated to "Convive mejor con otros" (2026-10-06)

Third and final placement. The total does not change (2,302,728): it is a move,
not a duplication, and both routes belong to Capacitación básica so the section
subtotal is unchanged too. "¿Cómo mejorar mi entorno?" drops to 4 courses,
convivencia goes to 7. Invariant holds: 113/113/0. Write-up in H21.

- [x] T22 — 299 moved to "Convive mejor con otros"
- [ ] T23 — Re-run production so the two route rows reflect the move

## T24 — Slide 2 final data: 36 courses (2026-10-06)

Course 348 leaves the convivencia sector (8 -> 7 courses, slide 2 37 -> 36) and
the sector is renamed "Convivir" -> "Convive", matching slide 12's route name.
36 assignments over 36 distinct courses.

Slide 2's tests were decoupled from the other slides: the excluded-course guards
(27 and 348) used to assert those courses still appeared in slides 1 and 12,
which would break slide 2's tests when those lists change. All four slide-2
tests now read only `slide2_empleo_incluyente_por_sector`. Write-up in H22.

- [x] T24 — Slide 2: 348 removed, sector renamed, tests decoupled
- [ ] T25 — Re-run production for the slide 2 change
