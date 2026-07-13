"""ABM de proveedores (compras.proveedores)."""

from __future__ import annotations

from typing import Any, Optional

from query_service import db

_CAMPOS = (
    "razon_social",
    "nombre_fantasia",
    "ciudad",
    "cuit",
    "mail",
    "contacto",
    "telefono",
    "rubro",
    "observaciones",
    "punt_entrega",
    "punt_calidad",
    "punt_respuesta",
    "punt_precio",
    "activo",
    "usuario_id",
)


def listar(
    *,
    solo_activos: bool = True,
    busqueda: Optional[str] = None,
    rubro: Optional[str] = None,
) -> list[dict]:
    sql = ["SELECT * FROM compras.proveedores WHERE 1=1"]
    params: list[Any] = []

    if solo_activos:
        sql.append("AND activo = TRUE")
    if rubro:
        sql.append("AND rubro = %s")
        params.append(rubro)
    if busqueda:
        sql.append(
            "AND (razon_social ILIKE %s OR nombre_fantasia ILIKE %s OR cuit ILIKE %s)"
        )
        like = f"%{busqueda}%"
        params.extend([like, like, like])

    sql.append("ORDER BY razon_social")
    return db.fetch_all("\n".join(sql), params)


def obtener(proveedor_id: int) -> dict | None:
    return db.fetch_one(
        "SELECT * FROM compras.proveedores WHERE id = %s",
        (proveedor_id,),
    )


def crear(datos: dict) -> dict:
    cols = [c for c in _CAMPOS if c in datos]
    if "razon_social" not in cols:
        raise ValueError("razon_social es obligatorio")

    placeholders = ", ".join(["%s"] * len(cols))
    colnames = ", ".join(cols)
    values = [datos[c] for c in cols]

    return db.execute_returning(
        f"""
        INSERT INTO compras.proveedores ({colnames})
        VALUES ({placeholders})
        RETURNING *
        """,
        values,
    )


def actualizar(proveedor_id: int, datos: dict) -> dict | None:
    cols = [c for c in _CAMPOS if c in datos]
    if not cols:
        return obtener(proveedor_id)

    sets = ", ".join(f"{c} = %s" for c in cols)
    values = [datos[c] for c in cols] + [proveedor_id]

    return db.execute_returning(
        f"""
        UPDATE compras.proveedores
        SET {sets}
        WHERE id = %s
        RETURNING *
        """,
        values,
    )


def desactivar(proveedor_id: int) -> dict | None:
    return actualizar(proveedor_id, {"activo": False})


def eliminar(proveedor_id: int) -> int:
    """Borrado físico. Preferir desactivar() en la UI."""
    return db.execute(
        "DELETE FROM compras.proveedores WHERE id = %s",
        (proveedor_id,),
    )
