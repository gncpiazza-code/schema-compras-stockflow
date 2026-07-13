"""Pañol: stock_maestro + stock_movimientos."""

from __future__ import annotations

from typing import Any, Optional

from query_service import db


def listar_inventario(*, busqueda: Optional[str] = None) -> list[dict]:
    sql = ["SELECT * FROM compras.stock_maestro WHERE 1=1"]
    params: list[Any] = []
    if busqueda:
        sql.append(
            "AND (codigo ILIKE %s OR descripcion ILIKE %s OR ubicacion ILIKE %s)"
        )
        like = f"%{busqueda}%"
        params.extend([like, like, like])
    sql.append("ORDER BY codigo")
    return db.fetch_all("\n".join(sql), params)


def obtener_por_codigo(codigo: str) -> dict | None:
    return db.fetch_one(
        "SELECT * FROM compras.stock_maestro WHERE codigo = %s",
        (codigo,),
    )


def upsert_item(datos: dict) -> dict:
    """Alta o actualización por código único."""
    if "codigo" not in datos or "descripcion" not in datos:
        raise ValueError("codigo y descripcion son obligatorios")

    return db.execute_returning(
        """
        INSERT INTO compras.stock_maestro (
            codigo, codigo_original, descripcion, cantidad,
            unidad, ubicacion, observaciones, usuario_id
        ) VALUES (
            %(codigo)s, %(codigo_original)s, %(descripcion)s, %(cantidad)s,
            %(unidad)s, %(ubicacion)s, %(observaciones)s, %(usuario_id)s
        )
        ON CONFLICT (codigo) DO UPDATE SET
            codigo_original = EXCLUDED.codigo_original,
            descripcion = EXCLUDED.descripcion,
            cantidad = EXCLUDED.cantidad,
            unidad = EXCLUDED.unidad,
            ubicacion = EXCLUDED.ubicacion,
            observaciones = EXCLUDED.observaciones,
            usuario_id = COALESCE(EXCLUDED.usuario_id, compras.stock_maestro.usuario_id),
            actualizado_en = CURRENT_TIMESTAMP
        RETURNING *
        """,
        {
            "codigo": datos["codigo"],
            "codigo_original": datos.get("codigo_original"),
            "descripcion": datos["descripcion"],
            "cantidad": datos.get("cantidad", 0),
            "unidad": datos.get("unidad", "UN"),
            "ubicacion": datos.get("ubicacion"),
            "observaciones": datos.get("observaciones"),
            "usuario_id": datos.get("usuario_id"),
        },
    )


def registrar_movimiento(
    *,
    tipo: str,
    cantidad: float,
    codigo: Optional[str] = None,
    maestro_id: Optional[int] = None,
    descripcion: Optional[str] = None,
    unidad: Optional[str] = None,
    referencia: Optional[str] = None,
    responsable: Optional[str] = None,
    usuario_id: Optional[int] = None,
    ajustar_stock: bool = True,
) -> dict:
    """
    Registra movimiento. Si ajustar_stock=True y hay maestro_id/codigo,
    suma (ingreso) o resta (egreso/salida) en stock_maestro.

    Convención de tipo (sugerida):
      ingreso | egreso | ajuste | salida
    """
    if cantidad == 0:
        raise ValueError("cantidad no puede ser 0")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            if maestro_id is None and codigo:
                cur.execute(
                    "SELECT id, cantidad, unidad, descripcion FROM compras.stock_maestro WHERE codigo = %s",
                    (codigo,),
                )
                row = cur.fetchone()
                if row:
                    maestro_id = row["id"]
                    unidad = unidad or row["unidad"]
                    descripcion = descripcion or row["descripcion"]

            if ajustar_stock and maestro_id is not None:
                delta = cantidad if tipo.lower() in ("ingreso", "ajuste+") else -abs(cantidad)
                if tipo.lower() in ("ajuste",):
                    delta = cantidad  # signo lo define quien llama
                cur.execute(
                    """
                    UPDATE compras.stock_maestro
                    SET cantidad = cantidad + %s,
                        actualizado_en = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                    """,
                    (delta, maestro_id),
                )
                actualizado = cur.fetchone()
                if actualizado is None:
                    raise ValueError(f"stock_maestro id={maestro_id} no existe")
                if actualizado["cantidad"] < 0:
                    raise ValueError("Stock insuficiente")

            cur.execute(
                """
                INSERT INTO compras.stock_movimientos (
                    tipo, maestro_id, codigo, descripcion, cantidad,
                    unidad, referencia, responsable, usuario_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING *
                """,
                (
                    tipo,
                    maestro_id,
                    codigo,
                    descripcion,
                    cantidad,
                    unidad,
                    referencia,
                    responsable,
                    usuario_id,
                ),
            )
            return cur.fetchone()


def listar_movimientos(
    *,
    codigo: Optional[str] = None,
    limite: int = 100,
) -> list[dict]:
    sql = ["SELECT * FROM compras.stock_movimientos WHERE 1=1"]
    params: list[Any] = []
    if codigo:
        sql.append("AND codigo = %s")
        params.append(codigo)
    sql.append("ORDER BY creado_en DESC, id DESC LIMIT %s")
    params.append(limite)
    return db.fetch_all("\n".join(sql), params)


def eliminar_item(codigo: str) -> int:
    return db.execute(
        "DELETE FROM compras.stock_maestro WHERE codigo = %s",
        (codigo,),
    )


def resumen() -> dict:
    row = db.fetch_one(
        """
        SELECT
            COUNT(*)::int AS items,
            COALESCE(SUM(cantidad), 0) AS cantidad_total
        FROM compras.stock_maestro
        """
    )
    return row or {"items": 0, "cantidad_total": 0}
