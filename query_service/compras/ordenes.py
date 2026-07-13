"""Órdenes de compra (OC) + ítems."""

from __future__ import annotations

from typing import Any, Optional

from query_service import db


def listar(*, estado: Optional[str] = None, limite: int = 100) -> list[dict]:
    sql = ["SELECT * FROM compras.ordenes WHERE 1=1"]
    params: list[Any] = []
    if estado:
        sql.append("AND estado = %s")
        params.append(estado)
    sql.append("ORDER BY fecha_oc DESC, id DESC LIMIT %s")
    params.append(limite)
    return db.fetch_all("\n".join(sql), params)


def obtener_por_nro(nro_oc: str) -> dict | None:
    cab = db.fetch_one(
        "SELECT * FROM compras.ordenes WHERE nro_oc = %s",
        (nro_oc,),
    )
    if not cab:
        return None
    cab["items"] = db.fetch_all(
        """
        SELECT * FROM compras.orden_items
        WHERE orden_id = %s
        ORDER BY id
        """,
        (cab["id"],),
    )
    return cab


def siguiente_nro(prefijo: str = "OC", anio: Optional[int] = None) -> str:
    from datetime import date

    anio = anio or date.today().year
    patron = f"{prefijo}-{anio}-%"
    row = db.fetch_one(
        """
        SELECT nro_oc FROM compras.ordenes
        WHERE nro_oc LIKE %s
        ORDER BY nro_oc DESC LIMIT 1
        """,
        (patron,),
    )
    if not row:
        return f"{prefijo}-{anio}-001"
    try:
        n = int(row["nro_oc"].rsplit("-", 1)[-1]) + 1
    except ValueError:
        n = 1
    return f"{prefijo}-{anio}-{n:03d}"


def crear(cabecera: dict, items: list[dict]) -> dict:
    if not items:
        raise ValueError("La OC necesita al menos un ítem")
    if "nro_oc" not in cabecera or "fecha_oc" not in cabecera:
        raise ValueError("nro_oc y fecha_oc son obligatorios")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO compras.ordenes (
                    nro_oc, solicitud_id, nro_solicitud, fecha_oc,
                    proveedor_id, proveedor_adjudicado, iva_pct,
                    tipo_cambio, estado, usuario_id
                ) VALUES (
                    %(nro_oc)s, %(solicitud_id)s, %(nro_solicitud)s, %(fecha_oc)s,
                    %(proveedor_id)s, %(proveedor_adjudicado)s, %(iva_pct)s,
                    %(tipo_cambio)s, %(estado)s, %(usuario_id)s
                )
                RETURNING *
                """,
                {
                    "nro_oc": cabecera["nro_oc"],
                    "solicitud_id": cabecera.get("solicitud_id"),
                    "nro_solicitud": cabecera.get("nro_solicitud"),
                    "fecha_oc": cabecera["fecha_oc"],
                    "proveedor_id": cabecera.get("proveedor_id"),
                    "proveedor_adjudicado": cabecera.get("proveedor_adjudicado"),
                    "iva_pct": cabecera.get("iva_pct", 21),
                    "tipo_cambio": cabecera.get("tipo_cambio", 1),
                    "estado": cabecera.get("estado", "Emitida"),
                    "usuario_id": cabecera.get("usuario_id"),
                },
            )
            oc = cur.fetchone()

            for item in items:
                cur.execute(
                    """
                    INSERT INTO compras.orden_items (
                        orden_id, cantidad, unidad, codigo_interno, nro_plano,
                        descripcion, proveedor_sugerido, fecha_entrega,
                        precio_unitario, descuento, desctipo,
                        precio_neto, precio_iva, precio_final, estado_oc
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    """,
                    (
                        oc["id"],
                        item["cantidad"],
                        item["unidad"],
                        item.get("codigo_interno"),
                        item.get("nro_plano"),
                        item["descripcion"],
                        item.get("proveedor_sugerido"),
                        item.get("fecha_entrega"),
                        item.get("precio_unitario", 0),
                        item.get("descuento", 0),
                        item.get("desctipo", "pct"),
                        item.get("precio_neto", 0),
                        item.get("precio_iva", 0),
                        item.get("precio_final", 0),
                        item.get("estado_oc", "Pendiente"),
                    ),
                )

            cur.execute(
                "SELECT * FROM compras.orden_items WHERE orden_id = %s ORDER BY id",
                (oc["id"],),
            )
            oc["items"] = list(cur.fetchall())
            return oc


def actualizar_estado(nro_oc: str, estado: str) -> dict | None:
    return db.execute_returning(
        """
        UPDATE compras.ordenes SET estado = %s
        WHERE nro_oc = %s
        RETURNING *
        """,
        (estado, nro_oc),
    )


def eliminar(nro_oc: str) -> int:
    return db.execute(
        "DELETE FROM compras.ordenes WHERE nro_oc = %s",
        (nro_oc,),
    )
