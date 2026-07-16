"""Catálogo de codificación oficial del sistema.

Los artículos de esta tabla se nombran SIEMPRE con su
codigo + nombre + descripcion (y unidad) canónicos.
Compras se alimenta de aquí; no es el catálogo editable libre.
"""

from __future__ import annotations

from typing import Any, Optional

from query_service import db


def listar(
    *,
    categoria: Optional[str] = None,
    busqueda: Optional[str] = None,
    solo_activos: bool = True,
) -> list[dict]:
    sql = ["SELECT * FROM compras.codificacion WHERE 1=1"]
    params: list[Any] = []

    if solo_activos:
        sql.append("AND activo = TRUE")
    if categoria:
        sql.append("AND categoria = %s")
        params.append(categoria)
    if busqueda:
        sql.append(
            "AND (codigo ILIKE %s OR nombre ILIKE %s OR descripcion ILIKE %s)"
        )
        like = f"%{busqueda}%"
        params.extend([like, like, like])

    sql.append("ORDER BY categoria NULLS LAST, codigo")
    return db.fetch_all("\n".join(sql), params)


def obtener(codificacion_id: int) -> dict | None:
    return db.fetch_one(
        "SELECT * FROM compras.codificacion WHERE id = %s",
        (codificacion_id,),
    )


def obtener_por_codigo(codigo: str) -> dict | None:
    return db.fetch_one(
        "SELECT * FROM compras.codificacion WHERE codigo = %s",
        (codigo.strip(),),
    )


def categorias() -> list[str]:
    rows = db.fetch_all(
        """
        SELECT DISTINCT categoria
        FROM compras.codificacion
        WHERE categoria IS NOT NULL AND activo = TRUE
        ORDER BY categoria
        """
    )
    return [r["categoria"] for r in rows]


def desactivar(codificacion_id: int) -> dict | None:
    return db.execute_returning(
        """
        UPDATE compras.codificacion
        SET activo = FALSE
        WHERE id = %s
        RETURNING *
        """,
        (codificacion_id,),
    )
