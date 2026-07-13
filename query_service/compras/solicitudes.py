"""Solicitudes de compra (SC) + ítems."""

from __future__ import annotations

from typing import Any, Optional

from query_service import db


def listar(
    *,
    estado: Optional[str] = None,
    area: Optional[str] = None,
    limite: int = 100,
) -> list[dict]:
    sql = ["SELECT * FROM compras.solicitudes WHERE 1=1"]
    params: list[Any] = []

    if estado:
        sql.append("AND estado = %s")
        params.append(estado)
    if area:
        sql.append("AND area = %s")
        params.append(area)

    sql.append("ORDER BY fecha DESC, id DESC LIMIT %s")
    params.append(limite)
    return db.fetch_all("\n".join(sql), params)


def obtener(solicitud_id: int) -> dict | None:
    return db.fetch_one(
        "SELECT * FROM compras.solicitudes WHERE id = %s",
        (solicitud_id,),
    )


def obtener_por_nro(nro_solicitud: str) -> dict | None:
    cab = db.fetch_one(
        "SELECT * FROM compras.solicitudes WHERE nro_solicitud = %s",
        (nro_solicitud,),
    )
    if not cab:
        return None
    cab["items"] = listar_items(cab["id"])
    return cab


def listar_items(solicitud_id: int) -> list[dict]:
    return db.fetch_all(
        """
        SELECT * FROM compras.solicitud_items
        WHERE solicitud_id = %s
        ORDER BY id
        """,
        (solicitud_id,),
    )


def siguiente_nro(prefijo: str = "SC", anio: Optional[int] = None) -> str:
    """Sugiere el próximo nro_solicitud (SC-YYYY-NNN)."""
    from datetime import date

    anio = anio or date.today().year
    patron = f"{prefijo}-{anio}-%"
    row = db.fetch_one(
        """
        SELECT nro_solicitud
        FROM compras.solicitudes
        WHERE nro_solicitud LIKE %s
        ORDER BY nro_solicitud DESC
        LIMIT 1
        """,
        (patron,),
    )
    if not row:
        return f"{prefijo}-{anio}-001"

    ultimo = row["nro_solicitud"].rsplit("-", 1)[-1]
    try:
        n = int(ultimo) + 1
    except ValueError:
        n = 1
    return f"{prefijo}-{anio}-{n:03d}"


def crear(cabecera: dict, items: list[dict]) -> dict:
    """
    Crea SC + ítems en una transacción.

    cabecera: nro_solicitud, fecha, area, solicitante, ...
    items: lista de dicts con cantidad, unidad, descripcion, ...
    """
    if not items:
        raise ValueError("La solicitud necesita al menos un ítem")

    obligatorios = ("nro_solicitud", "fecha", "area", "solicitante")
    for campo in obligatorios:
        if campo not in cabecera:
            raise ValueError(f"Falta {campo} en la cabecera")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO compras.solicitudes (
                    nro_solicitud, fecha, area, solicitante, rubro,
                    prioridad, tipo_cambio, estado, creador,
                    check_pedido, usuario_id
                ) VALUES (
                    %(nro_solicitud)s, %(fecha)s, %(area)s, %(solicitante)s,
                    %(rubro)s, %(prioridad)s, %(tipo_cambio)s, %(estado)s,
                    %(creador)s, %(check_pedido)s, %(usuario_id)s
                )
                RETURNING *
                """,
                {
                    "nro_solicitud": cabecera["nro_solicitud"],
                    "fecha": cabecera["fecha"],
                    "area": cabecera["area"],
                    "solicitante": cabecera["solicitante"],
                    "rubro": cabecera.get("rubro"),
                    "prioridad": cabecera.get("prioridad", "MEDIA"),
                    "tipo_cambio": cabecera.get("tipo_cambio", 1),
                    "estado": cabecera.get("estado", "Pendiente"),
                    "creador": cabecera.get("creador"),
                    "check_pedido": cabecera.get("check_pedido", ""),
                    "usuario_id": cabecera.get("usuario_id"),
                },
            )
            sc = cur.fetchone()
            sc_id = sc["id"]

            for item in items:
                cur.execute(
                    """
                    INSERT INTO compras.solicitud_items (
                        solicitud_id, cantidad, unidad, codigo_interno,
                        nro_plano, descripcion, proveedor_sugerido,
                        fecha_entrega, precio_unitario, observaciones,
                        estado_cot
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        sc_id,
                        item["cantidad"],
                        item["unidad"],
                        item.get("codigo_interno"),
                        item.get("nro_plano"),
                        item["descripcion"],
                        item.get("proveedor_sugerido"),
                        item.get("fecha_entrega"),
                        item.get("precio_unitario", 0),
                        item.get("observaciones"),
                        item.get("estado_cot", ""),
                    ),
                )

            cur.execute(
                "SELECT * FROM compras.solicitud_items WHERE solicitud_id = %s ORDER BY id",
                (sc_id,),
            )
            sc["items"] = list(cur.fetchall())
            return sc


def actualizar_estado(nro_solicitud: str, estado: str) -> dict | None:
    return db.execute_returning(
        """
        UPDATE compras.solicitudes
        SET estado = %s
        WHERE nro_solicitud = %s
        RETURNING *
        """,
        (estado, nro_solicitud),
    )


def marcar_check(nro_solicitud: str, check_pedido: str) -> dict | None:
    return db.execute_returning(
        """
        UPDATE compras.solicitudes
        SET check_pedido = %s
        WHERE nro_solicitud = %s
        RETURNING *
        """,
        (check_pedido, nro_solicitud),
    )


def eliminar(nro_solicitud: str) -> int:
    """
    Elimina SC (cascada de ítems).
    Falla si hay cotización u OC que referencien la SC (FK SET NULL /
    conviene validar en UI antes).
    """
    return db.execute(
        "DELETE FROM compras.solicitudes WHERE nro_solicitud = %s",
        (nro_solicitud,),
    )
