"""Cotizaciones comparativas (hasta 3 proveedores) + ítems."""

from __future__ import annotations

from typing import Any, Optional

from query_service import db


def listar(*, estado: Optional[str] = None, limite: int = 100) -> list[dict]:
    sql = ["SELECT * FROM compras.cotizaciones WHERE 1=1"]
    params: list[Any] = []
    if estado:
        sql.append("AND estado = %s")
        params.append(estado)
    sql.append("ORDER BY fecha DESC, id DESC LIMIT %s")
    params.append(limite)
    return db.fetch_all("\n".join(sql), params)


def obtener_por_nro(nro_cot: str) -> dict | None:
    cab = db.fetch_one(
        "SELECT * FROM compras.cotizaciones WHERE nro_cot = %s",
        (nro_cot,),
    )
    if not cab:
        return None
    cab["items"] = db.fetch_all(
        """
        SELECT * FROM compras.cotizacion_items
        WHERE cotizacion_id = %s
        ORDER BY id
        """,
        (cab["id"],),
    )
    return cab


def siguiente_nro(prefijo: str = "COT", anio: Optional[int] = None) -> str:
    from datetime import date

    anio = anio or date.today().year
    patron = f"{prefijo}-{anio}-%"
    row = db.fetch_one(
        """
        SELECT nro_cot FROM compras.cotizaciones
        WHERE nro_cot LIKE %s
        ORDER BY nro_cot DESC LIMIT 1
        """,
        (patron,),
    )
    if not row:
        return f"{prefijo}-{anio}-001"
    try:
        n = int(row["nro_cot"].rsplit("-", 1)[-1]) + 1
    except ValueError:
        n = 1
    return f"{prefijo}-{anio}-{n:03d}"


def crear(cabecera: dict, items: list[dict]) -> dict:
    """
    cabecera: nro_cot, fecha, solicitud_id?, moneda, prov1_nombre, ...
    items: descripcion, cantidad, pu1/pu2/pu3, desc1/2/3, ...
    """
    if "nro_cot" not in cabecera or "fecha" not in cabecera:
        raise ValueError("nro_cot y fecha son obligatorios")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO compras.cotizaciones (
                    nro_cot, solicitud_id, nro_solicitud, fecha, moneda,
                    tc_usd, tc_eur, iva_pct, estado,
                    prov1_nombre, prov1_entrega, prov1_pago, prov1_flete,
                    prov2_nombre, prov2_entrega, prov2_pago, prov2_flete,
                    prov3_nombre, prov3_entrega, prov3_pago, prov3_flete,
                    usuario_id
                ) VALUES (
                    %(nro_cot)s, %(solicitud_id)s, %(nro_solicitud)s, %(fecha)s,
                    %(moneda)s, %(tc_usd)s, %(tc_eur)s, %(iva_pct)s, %(estado)s,
                    %(prov1_nombre)s, %(prov1_entrega)s, %(prov1_pago)s, %(prov1_flete)s,
                    %(prov2_nombre)s, %(prov2_entrega)s, %(prov2_pago)s, %(prov2_flete)s,
                    %(prov3_nombre)s, %(prov3_entrega)s, %(prov3_pago)s, %(prov3_flete)s,
                    %(usuario_id)s
                )
                RETURNING *
                """,
                {
                    "nro_cot": cabecera["nro_cot"],
                    "solicitud_id": cabecera.get("solicitud_id"),
                    "nro_solicitud": cabecera.get("nro_solicitud"),
                    "fecha": cabecera["fecha"],
                    "moneda": cabecera.get("moneda", "ARS"),
                    "tc_usd": cabecera.get("tc_usd", 1),
                    "tc_eur": cabecera.get("tc_eur", 1),
                    "iva_pct": cabecera.get("iva_pct", 21),
                    "estado": cabecera.get("estado", "Pendiente"),
                    "prov1_nombre": cabecera.get("prov1_nombre"),
                    "prov1_entrega": cabecera.get("prov1_entrega"),
                    "prov1_pago": cabecera.get("prov1_pago"),
                    "prov1_flete": cabecera.get("prov1_flete"),
                    "prov2_nombre": cabecera.get("prov2_nombre"),
                    "prov2_entrega": cabecera.get("prov2_entrega"),
                    "prov2_pago": cabecera.get("prov2_pago"),
                    "prov2_flete": cabecera.get("prov2_flete"),
                    "prov3_nombre": cabecera.get("prov3_nombre"),
                    "prov3_entrega": cabecera.get("prov3_entrega"),
                    "prov3_pago": cabecera.get("prov3_pago"),
                    "prov3_flete": cabecera.get("prov3_flete"),
                    "usuario_id": cabecera.get("usuario_id"),
                },
            )
            cot = cur.fetchone()

            for item in items:
                cur.execute(
                    """
                    INSERT INTO compras.cotizacion_items (
                        cotizacion_id, idx_sc, descripcion, unidad, cantidad,
                        pu1, pu2, pu3, desc1, desc2, desc3,
                        desctipo1, desctipo2, desctipo3
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    """,
                    (
                        cot["id"],
                        item.get("idx_sc"),
                        item.get("descripcion"),
                        item.get("unidad"),
                        item.get("cantidad", 0),
                        item.get("pu1", 0),
                        item.get("pu2", 0),
                        item.get("pu3", 0),
                        item.get("desc1", 0),
                        item.get("desc2", 0),
                        item.get("desc3", 0),
                        item.get("desctipo1", "pct"),
                        item.get("desctipo2", "pct"),
                        item.get("desctipo3", "pct"),
                    ),
                )

            cur.execute(
                """
                SELECT * FROM compras.cotizacion_items
                WHERE cotizacion_id = %s ORDER BY id
                """,
                (cot["id"],),
            )
            cot["items"] = list(cur.fetchall())
            return cot


def eliminar(nro_cot: str) -> int:
    return db.execute(
        "DELETE FROM compras.cotizaciones WHERE nro_cot = %s",
        (nro_cot,),
    )
