"""Congela una copia de tablas de PG (schema public) en un namespace nuevo del datalake.

Respalda las cifras ya reportadas: los periodos cerrados (<= corte) leen esta
copia congelada en vez de `silver_cpe`, que sigue viva vía el ETL Fargate.

- Solo escribe en el namespace indicado (p. ej. `reportado_cpe_202609`); nunca
  toca `silver_cpe` ni `gold_cpe`.
- Copia las tablas tal cual están en PG: mismos tipos, nombres de columna en
  minúscula (Athena/Glue los normaliza así).
- Excluye PII en texto plano (`dim_user.email`): el lake solo admite hashes.
- Idempotente: si la tabla ya existe aborta, salvo `--replace` (drop + carga
  completa). Una carga cortada a la mitad se repite con `--replace`.

Uso (credenciales PG desde `.env` vía Settings, AWS desde el perfil SSO):

    AWS_PROFILE=sandbox-datalake uv run --with "pyiceberg[pyarrow]" \\
        python scripts/freeze_pg_to_lake.py --namespace reportado_cpe_202609
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pyarrow as pa

# Tablas permitidas -> columnas excluidas (PII en texto plano).
TABLAS: dict[str, tuple[str, ...]] = {
    "fact_inscription": (),
    "dim_user": ("email",),
    "dim_local": (),
    "course": (),
    # Snapshots mensuales tal como están en PG (cifras de cierre reportadas).
    "analytics_snapshot_run": (),
    "analytics_snapshot_course_metric": (),
    "analytics_snapshot_user_metric": (),
    "analytics_snapshot_course_metric_current": (),
    "analytics_snapshot_user_metric_current": (),
    "cpe_snapshot_meta": (),
}

_TIPOS = {
    "character varying": pa.string(),
    "text": pa.string(),
    "smallint": pa.int32(),  # Iceberg no tiene int16
    "integer": pa.int32(),
    "bigint": pa.int64(),
    "boolean": pa.bool_(),
    "date": pa.date32(),
    "timestamp without time zone": pa.timestamp("us"),
    "timestamp with time zone": pa.timestamp("us", tz="UTC"),
}

TABLE_BUCKET_ARN = "arn:aws:s3tables:us-east-1:278711064005:bucket/datalake-fcs"
REGION = "us-east-1"


def _tipo_arrow(columna: str, data_type: str, precision, scale) -> pa.DataType:
    if data_type == "numeric":
        if precision is None or scale is None:
            raise ValueError(f"numeric sin precision/escala en columna {columna}")
        return pa.decimal128(int(precision), int(scale))
    try:
        return _TIPOS[data_type]
    except KeyError:
        raise ValueError(f"tipo no soportado {data_type} en columna {columna}") from None


def construir_schema(tabla: str, columnas) -> tuple[pa.Schema, list[str]]:
    """Schema Arrow destino y columnas PG a leer, en orden.

    Args:
        tabla: tabla de `public`; debe estar en TABLAS.
        columnas: secuencia (nombre, data_type, precision, scale) en el orden
            de information_schema.

    Returns:
        (schema con nombres en minúscula, nombres PG a seleccionar).
    """
    if tabla not in TABLAS:
        raise ValueError(f"tabla no permitida: {tabla}")
    excluidas = {c.lower() for c in TABLAS[tabla]}
    campos, select_cols = [], []
    for nombre, data_type, precision, scale in columnas:
        if nombre.lower() in excluidas:
            continue
        campos.append(pa.field(nombre.lower(), _tipo_arrow(nombre, data_type, precision, scale)))
        select_cols.append(nombre)
    return pa.schema(campos), select_cols


def select_sql(tabla: str, select_cols: list[str]) -> str:
    """SELECT con identificadores citados (vienen de information_schema)."""
    cols = ", ".join(f'"{c}"' for c in select_cols)
    return f'SELECT {cols} FROM public."{tabla}"'


def filas_a_arrow(filas, schema: pa.Schema) -> pa.Table:
    """Convierte filas (tuplas) a una tabla Arrow columnar con el schema dado."""
    columnas = list(zip(*filas)) if filas else [[] for _ in schema]
    arrays = [pa.array(col, type=campo.type) for col, campo in zip(columnas, schema)]
    return pa.Table.from_arrays(arrays, schema=schema)


def _catalogo():
    from pyiceberg.catalog import load_catalog

    return load_catalog(
        "s3tables_freeze",
        **{
            "type": "rest",
            "warehouse": TABLE_BUCKET_ARN,
            "uri": f"https://s3tables.{REGION}.amazonaws.com/iceberg",
            "rest.sigv4-enabled": "true",
            "rest.signing-name": "s3tables",
            "rest.signing-region": REGION,
        },
    )


def _conectar_pg():
    import psycopg2

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.consejo.config.settings import Settings

    s = Settings()
    conn = psycopg2.connect(
        host=s.db_host, dbname=s.db_name, user=s.db_user,
        password=s.db_password, port=s.db_port, connect_timeout=10,
    )
    conn.set_session(readonly=True)
    return conn


def _columnas_pg(conn, tabla: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name, data_type, numeric_precision, numeric_scale "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
            (tabla,),
        )
        return cur.fetchall()


def _contar_pg(conn, tabla: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM public."{tabla}"')
        return cur.fetchone()[0]


def congelar_tabla(conn, namespace: str, tabla: str, batch: int, replace: bool) -> None:
    schema, select_cols = construir_schema(tabla, _columnas_pg(conn, tabla))
    fqn = f"{namespace}.{tabla}"
    cat = _catalogo()
    if cat.table_exists(fqn):
        if not replace:
            raise SystemExit(f"{fqn} ya existe; usar --replace para recargarla completa")
        # S3 Tables solo acepta drop con purge (borra también los archivos).
        cat.purge_table(fqn)
        print(f"[{tabla}] drop previo (replace)")
    cat.create_table(fqn, schema=schema)

    esperado = _contar_pg(conn, tabla)
    t0, cargadas = time.time(), 0
    # Cursor server-side: streaming sin materializar la tabla en memoria.
    with conn.cursor(name=f"freeze_{tabla}") as cur:
        cur.itersize = batch
        cur.execute(select_sql(tabla, select_cols))
        while filas := cur.fetchmany(batch):
            # Catálogo fresco por commit: S3 Tables corta sesiones REST largas.
            _catalogo().load_table(fqn).append(filas_a_arrow(filas, schema))
            cargadas += len(filas)
            print(f"[{tabla}] {cargadas:,}/{esperado:,} ({time.time() - t0:,.0f}s)", flush=True)

    total = int(_catalogo().load_table(fqn).current_snapshot().summary["total-records"])
    estado = "OK" if total == esperado == cargadas else "DIFERENCIA"
    print(f"[{tabla}] {estado}: pg={esperado:,} cargadas={cargadas:,} lake={total:,}")
    if estado != "OK":
        raise SystemExit(f"{fqn}: conteo no coincide")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--namespace", required=True)
    p.add_argument("--tables", nargs="+", required=True, choices=list(TABLAS))
    p.add_argument("--batch", type=int, default=1_000_000)
    p.add_argument("--replace", action="store_true")
    a = p.parse_args(argv)
    if a.namespace in ("silver_cpe", "gold_cpe", "silver_carso", "gold_carso"):
        raise SystemExit(f"namespace protegido: {a.namespace}")

    cat = _catalogo()
    if (a.namespace,) not in cat.list_namespaces():
        cat.create_namespace(a.namespace)
        print(f"namespace creado: {a.namespace}")

    conn = _conectar_pg()
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = 0")
        for tabla in a.tables:
            congelar_tabla(conn, a.namespace, tabla, a.batch, a.replace)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
