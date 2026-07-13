"""
Conexión PostgreSQL para el Query Service.

Lee el `.env` generado por el instalador:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE (opcional)

Uso típico:

    from query_service.db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

import psycopg
from psycopg.rows import dict_row


def _cargar_dotenv(ruta: Optional[str | Path] = None) -> None:
    """Carga KEY=VALUE del .env si aún no están en el entorno."""
    candidatos = []
    if ruta:
        candidatos.append(Path(ruta))
    env_path = os.environ.get("STOCKFLOW_ENV")
    if env_path:
        candidatos.append(Path(env_path))
    candidatos.extend(
        [
            Path.cwd() / ".env",
            Path.home() / ".env",
        ]
    )

    for path in candidatos:
        if not path.is_file():
            continue
        for linea in path.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            key, _, value = linea.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        break


def get_connection_params(env_file: Optional[str | Path] = None) -> dict[str, Any]:
    _cargar_dotenv(env_file)

    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    faltantes = [k for k in required if not os.environ.get(k)]
    if faltantes:
        raise RuntimeError(
            "Faltan variables de entorno: "
            + ", ".join(faltantes)
            + ". Indicá el .env del instalador (STOCKFLOW_ENV) o cargá las vars."
        )

    params: dict[str, Any] = {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "connect_timeout": 10,
        "row_factory": dict_row,
    }
    sslmode = os.environ.get("DB_SSLMODE")
    if sslmode:
        params["sslmode"] = sslmode
    return params


@contextmanager
def get_connection(
    env_file: Optional[str | Path] = None,
) -> Iterator[psycopg.Connection]:
    """Abre conexión con search_path: compras, deposito, public."""
    params = get_connection_params(env_file)
    conn = psycopg.connect(**params)
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO compras, deposito, public")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params: tuple | list | dict | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params: tuple | list | dict | None = None) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql: str, params: tuple | list | dict | None = None) -> int:
    """INSERT/UPDATE/DELETE. Devuelve rowcount."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def execute_returning(
    sql: str, params: tuple | list | dict | None = None
) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
