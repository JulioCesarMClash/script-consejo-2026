# Freeze reported PG data into the lake (cutoff 2026-09-30)

Objective: closed periods (<= 2026-09-30) read a frozen copy of PG in the lake so they match the reported figures exactly; open periods read live `silver_cpe`. Branch: `feature/datalake-athena`. Delivery: ask-on-risk. Test runner: pytest (`uv run pytest`).

## Specs

- S1 — Approach B chosen by the user: "B" = freeze a copy of PG `fact_inscription` and `dim_user` into the lake and point closed periods at it.
- S2 — Exact equality for closed periods: "lo que almenos septiembre hacia atras, sea excatamente igual". Acceptance: `reconcile --tolerance-abs 0` passes for every translated metric with period end <= 2026-10-01 between PG and the frozen tables.
- S3 — Open periods keep reading live `silver_cpe` (Fargate from MySQL): "si hay un incremento se puede argumentar el incremento en el mes".
- S4 — No writes to the lake without explicit user approval of the concrete plan (original prompt: "NO escribas en el lake sin mi aprobación explícita"). Nothing existing in `silver_cpe`/`gold_cpe` is modified; only a new namespace is created.
- S5 — No plaintext PII in the lake: PG `dim_user.email` is excluded (assumption: no translated metric needs it).

## Tasks

- [x] T1 (S1, S4, S5) — Loader `scripts/freeze_pg_to_lake.py` + `tests/unit/test_freeze_pg_to_lake.py` (RED: module missing; GREEN: 9 passed; suite 277 passed, 6 skipped). Route: inline.
- [x] T2 (S1, S4) — Load after user OK ("si dale, seguí con la carga"). course 935, dim_local 23,828, dim_user 16,282,964, fact_inscription 59,129,651 — all equal to PG. Checksums (users, sums, cert100, min/max dates): 13/13 equal. Route: inline.
- [x] T3 (S2, S3) — Seam in SQL, no routing code: each of the 4 `athena_mapping` unions `reportado_cpe_202609` rows dated < 2026-10-01 with `silver_cpe` rows dated >= 2026-10-01 (registrations by registration date, inscriptions by inscription date, certificates by certification date). Frozen side keeps PG semantics (México via `dim_local.countryname`); live side uses `country_id = 'MX'` (live `dim_local.country_name` is 'Mexico' without accent). Written; pending execution check. Route: inline.
- [ ] T4 (S2) — Period 2025-09-01..2026-10-01: slide1 264,849 and slide2 54,139 EXACT vs PG; registered_cpe +4,734 and inscriptions_cpe +20,458 (October from live silver, expected). Crossing period ..2026-11-01: closed part unchanged by construction; October live part uses country_id='MX', so some categories come out below PG for October (e.g. slide1_buscar_trabajo 26,599 vs 26,638). Pending: compare against the deck values (needs the user's numbers). Route: inline.

## Log

- L1 (2026-10-23, user, verbatim): "el otro problema es que lo que esta en pg esta reportado, y seguramente lo que tenga en octubre, si hay un incremento se puede argumentar el incremento en el mes, pero es por eso que lo que almenos septiembre hacia atras, sea excatamente igual" — then chose "B".
- L2 — Diagnosis: the lake was missing 2026-03-25..2026-09-30 (closed by the user's manual backfill on 2026-10-23, task 41932f63..., ETL_SAMPLE_SINCE=2026-03-01). Live PG vs MySQL differ because `inscription.lastUpdate` is not bumped when `advance` changes and both ETLs are date-window incrementals: 69/300 of the lake's June certificates are stale in PG; 60/60 checked in MySQL have advance=100.
- L3 — Sizes (PG public): fact_inscription 59,129,651; dim_user 16,282,964; dim_local 23,828; course 935. SSO role AWSAdministratorAccess: simulation `allowed` for s3tables Create*/PutTableData/DeleteTable.
- L5 (2026-10-23, user, verbatim): "yo tambien copiaria la taba snapshot de pg como esta en el datalake, asi cuando el etl ya llene correctamente no tendra esos problemas". gold_cpe.analytics_snapshot_* already matched PG run by run (runs 9,11,13,15,16,17); copied anyway into reportado_cpe_202609 so the frozen photo does not depend on the monthly snapshot job: analytics_snapshot_run 6, course_metric 570,654, user_metric 36,932, course_metric_current 96,644, user_metric_current 6,175, cpe_snapshot_meta 2 — all counts OK. cpe_snapshot_metric skipped (0 rows, numeric without precision). gold_cpe untouched.
- L4 — Rollback snapshots for live tables (not touched by this plan): fact_inscription 7726959662990517047, dim_user 2192273234682692163.
