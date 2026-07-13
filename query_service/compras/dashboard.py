"""Resúmenes para el dashboard de Compras."""

from __future__ import annotations

from query_service import db


def resumen() -> dict:
    """Contadores rápidos para la pantalla de inicio."""
    return {
        "solicitudes_pendientes": _count(
            "SELECT COUNT(*)::int AS n FROM compras.solicitudes WHERE estado = %s",
            ("Pendiente",),
        ),
        "ordenes_emitidas": _count(
            "SELECT COUNT(*)::int AS n FROM compras.ordenes WHERE estado = %s",
            ("Emitida",),
        ),
        "cotizaciones_pendientes": _count(
            "SELECT COUNT(*)::int AS n FROM compras.cotizaciones WHERE estado = %s",
            ("Pendiente",),
        ),
        "recepciones": _count(
            "SELECT COUNT(*)::int AS n FROM compras.recepciones"
        ),
        "items_panol": _count(
            "SELECT COUNT(*)::int AS n FROM compras.stock_maestro"
        ),
        "salidas": _count(
            "SELECT COUNT(*)::int AS n FROM compras.stock_salidas"
        ),
    }


def ultimas_solicitudes(limite: int = 10) -> list[dict]:
    return db.fetch_all(
        """
        SELECT id, nro_solicitud, fecha, area, solicitante, estado, prioridad
        FROM compras.solicitudes
        ORDER BY creado_en DESC, id DESC
        LIMIT %s
        """,
        (limite,),
    )


def ultimas_ordenes(limite: int = 10) -> list[dict]:
    return db.fetch_all(
        """
        SELECT id, nro_oc, fecha_oc, proveedor_adjudicado, estado, nro_solicitud
        FROM compras.ordenes
        ORDER BY creado_en DESC, id DESC
        LIMIT %s
        """,
        (limite,),
    )


def _count(sql: str, params: tuple | None = None) -> int:
    row = db.fetch_one(sql, params)
    return int(row["n"]) if row else 0
