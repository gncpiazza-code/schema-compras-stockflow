"""Insumos internos de Compras.

Catálogo propio del sector. Dos modos:
  1. Vinculado a codificacion (compra de artículo oficial).
  2. Interno puro (codificacion_id NULL): producto a comprar
     que NO cruza con la codificación original.
"""

from __future__ import annotations

from typing import Any, Optional

from query_service import db
from query_service.compras import codificacion as codif_svc


def listar(
    *,
    solo_activos: bool = True,
    solo_internos: bool = False,
    solo_vinculados: bool = False,
    busqueda: Optional[str] = None,
) -> list[dict]:
    sql = [
        """
        SELECT
            i.*,
            c.codigo AS codificacion_codigo,
            c.nombre AS codificacion_nombre,
            c.categoria AS codificacion_categoria
        FROM compras.insumos i
        LEFT JOIN compras.codificacion c ON c.id = i.codificacion_id
        WHERE 1=1
        """
    ]
    params: list[Any] = []

    if solo_activos:
        sql.append("AND i.activo = TRUE")
    if solo_internos:
        sql.append("AND i.codificacion_id IS NULL")
    if solo_vinculados:
        sql.append("AND i.codificacion_id IS NOT NULL")
    if busqueda:
        sql.append(
            """
            AND (
                i.codigo ILIKE %s OR i.nombre ILIKE %s
                OR i.descripcion ILIKE %s OR c.codigo ILIKE %s
            )
            """
        )
        like = f"%{busqueda}%"
        params.extend([like, like, like, like])

    sql.append("ORDER BY i.nombre")
    return db.fetch_all("\n".join(sql), params)


def obtener(insumo_id: int) -> dict | None:
    return db.fetch_one(
        """
        SELECT
            i.*,
            c.codigo AS codificacion_codigo,
            c.nombre AS codificacion_nombre
        FROM compras.insumos i
        LEFT JOIN compras.codificacion c ON c.id = i.codificacion_id
        WHERE i.id = %s
        """,
        (insumo_id,),
    )


def crear_interno(datos: dict) -> dict:
    """Alta de insumo que NO cruza con codificación oficial."""
    if not datos.get("nombre"):
        raise ValueError("nombre es obligatorio")

    return db.execute_returning(
        """
        INSERT INTO compras.insumos (
            codigo, nombre, descripcion, unidad,
            codificacion_id, usuario_id
        ) VALUES (
            %(codigo)s, %(nombre)s, %(descripcion)s, %(unidad)s,
            NULL, %(usuario_id)s
        )
        RETURNING *
        """,
        {
            "codigo": datos.get("codigo"),
            "nombre": datos["nombre"],
            "descripcion": datos.get("descripcion") or datos["nombre"],
            "unidad": datos.get("unidad", "UN"),
            "usuario_id": datos.get("usuario_id"),
        },
    )


def crear_desde_codificacion(
    codificacion_id: int,
    *,
    usuario_id: Optional[int] = None,
    codigo_interno: Optional[str] = None,
) -> dict:
    """
    Alta de insumo alimentado por la codificación oficial.
    Copia nombre/descripcion/unidad canónicos.
    """
    oficial = codif_svc.obtener(codificacion_id)
    if not oficial:
        raise ValueError(f"codificacion id={codificacion_id} no existe")

    existente = db.fetch_one(
        "SELECT * FROM compras.insumos WHERE codificacion_id = %s",
        (codificacion_id,),
    )
    if existente:
        return existente

    return db.execute_returning(
        """
        INSERT INTO compras.insumos (
            codigo, nombre, descripcion, unidad,
            codificacion_id, usuario_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
        RETURNING *
        """,
        (
            codigo_interno or oficial["codigo"],
            oficial["nombre"],
            oficial["descripcion"],
            oficial["unidad"],
            oficial["id"],
            usuario_id,
        ),
    )


def actualizar(insumo_id: int, datos: dict) -> dict | None:
    """
    Edita un insumo. Si está vinculado a codificación, no permite
    cambiar nombre/descripcion/unidad (deben respetar el oficial).
    """
    actual = obtener(insumo_id)
    if not actual:
        return None

    if actual.get("codificacion_id"):
        prohibidos = {"nombre", "descripcion", "unidad", "codificacion_id"}
        tocados = prohibidos.intersection(datos)
        if tocados:
            raise ValueError(
                "Insumo vinculado a codificación: no se puede alterar "
                + ", ".join(sorted(tocados))
            )

    cols = [
        c
        for c in ("codigo", "nombre", "descripcion", "unidad", "activo")
        if c in datos
    ]
    if not cols:
        return actual

    sets = ", ".join(f"{c} = %s" for c in cols)
    values = [datos[c] for c in cols] + [insumo_id]
    return db.execute_returning(
        f"""
        UPDATE compras.insumos
        SET {sets}
        WHERE id = %s
        RETURNING *
        """,
        values,
    )


def desactivar(insumo_id: int) -> dict | None:
    return actualizar(insumo_id, {"activo": False})


def eliminar(insumo_id: int) -> int:
    return db.execute(
        "DELETE FROM compras.insumos WHERE id = %s",
        (insumo_id,),
    )
