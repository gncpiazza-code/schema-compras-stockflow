"""Recepciones / control de ingreso (pedida vs recibida)."""

from __future__ import annotations

from typing import Optional

from query_service import db


def listar(*, limite: int = 100) -> list[dict]:
    return db.fetch_all(
        """
        SELECT * FROM compras.recepciones
        ORDER BY fecha_recepcion DESC, id DESC
        LIMIT %s
        """,
        (limite,),
    )


def obtener(recepcion_id: int) -> dict | None:
    cab = db.fetch_one(
        "SELECT * FROM compras.recepciones WHERE id = %s",
        (recepcion_id,),
    )
    if not cab:
        return None
    cab["items"] = db.fetch_all(
        """
        SELECT * FROM compras.recepcion_items
        WHERE recepcion_id = %s
        ORDER BY id
        """,
        (cab["id"],),
    )
    return cab


def obtener_por_solicitud(nro_solicitud: str) -> dict | None:
    cab = db.fetch_one(
        """
        SELECT * FROM compras.recepciones
        WHERE nro_solicitud = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (nro_solicitud,),
    )
    if not cab:
        return None
    return obtener(cab["id"])


def crear(cabecera: dict, items: list[dict]) -> dict:
    if not items:
        raise ValueError("La recepción necesita al menos un ítem")
    if "fecha_recepcion" not in cabecera:
        raise ValueError("fecha_recepcion es obligatoria")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO compras.recepciones (
                    orden_id, solicitud_id, nro_solicitud,
                    fecha_recepcion, proveedor, nro_remito, usuario_id
                ) VALUES (
                    %(orden_id)s, %(solicitud_id)s, %(nro_solicitud)s,
                    %(fecha_recepcion)s, %(proveedor)s, %(nro_remito)s,
                    %(usuario_id)s
                )
                RETURNING *
                """,
                {
                    "orden_id": cabecera.get("orden_id"),
                    "solicitud_id": cabecera.get("solicitud_id"),
                    "nro_solicitud": cabecera.get("nro_solicitud"),
                    "fecha_recepcion": cabecera["fecha_recepcion"],
                    "proveedor": cabecera.get("proveedor"),
                    "nro_remito": cabecera.get("nro_remito"),
                    "usuario_id": cabecera.get("usuario_id"),
                },
            )
            rec = cur.fetchone()

            for item in items:
                cur.execute(
                    """
                    INSERT INTO compras.recepcion_items (
                        recepcion_id, descripcion, codigo_interno, nro_plano,
                        cant_pedida, cant_recibida, precio_unitario,
                        estado, observaciones, estado_repuesto
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        rec["id"],
                        item["descripcion"],
                        item.get("codigo_interno"),
                        item.get("nro_plano"),
                        item.get("cant_pedida", 0),
                        item.get("cant_recibida", 0),
                        item.get("precio_unitario", 0),
                        item.get("estado", "Pendiente"),
                        item.get("observaciones"),
                        item.get("estado_repuesto", "A confirmar"),
                    ),
                )

            cur.execute(
                """
                SELECT * FROM compras.recepcion_items
                WHERE recepcion_id = %s ORDER BY id
                """,
                (rec["id"],),
            )
            rec["items"] = list(cur.fetchall())
            return rec


def eliminar(recepcion_id: int) -> int:
    return db.execute(
        "DELETE FROM compras.recepciones WHERE id = %s",
        (recepcion_id,),
    )
