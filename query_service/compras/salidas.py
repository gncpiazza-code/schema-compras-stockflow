"""Salidas de pañol (stock_salidas + salida_items)."""

from __future__ import annotations

from typing import Optional

from query_service import db


def listar(*, limite: int = 100) -> list[dict]:
    return db.fetch_all(
        """
        SELECT * FROM compras.stock_salidas
        ORDER BY fecha DESC, id DESC
        LIMIT %s
        """,
        (limite,),
    )


def obtener_por_nro(nro_salida: str) -> dict | None:
    cab = db.fetch_one(
        "SELECT * FROM compras.stock_salidas WHERE nro_salida = %s",
        (nro_salida,),
    )
    if not cab:
        return None
    cab["items"] = db.fetch_all(
        """
        SELECT * FROM compras.salida_items
        WHERE salida_id = %s
        ORDER BY id
        """,
        (cab["id"],),
    )
    return cab


def siguiente_nro(prefijo: str = "SAL", anio: Optional[int] = None) -> str:
    from datetime import date

    anio = anio or date.today().year
    patron = f"{prefijo}-{anio}-%"
    row = db.fetch_one(
        """
        SELECT nro_salida FROM compras.stock_salidas
        WHERE nro_salida LIKE %s
        ORDER BY nro_salida DESC LIMIT 1
        """,
        (patron,),
    )
    if not row:
        return f"{prefijo}-{anio}-001"
    try:
        n = int(row["nro_salida"].rsplit("-", 1)[-1]) + 1
    except ValueError:
        n = 1
    return f"{prefijo}-{anio}-{n:03d}"


def crear(cabecera: dict, items: list[dict], *, descontar_stock: bool = True) -> dict:
    """
    Crea salida + ítems.
    Si descontar_stock=True, registra movimiento 'salida' y baja stock_maestro.
    """
    if not items:
        raise ValueError("La salida necesita al menos un ítem")
    for campo in ("nro_salida", "fecha", "responsable", "area"):
        if campo not in cabecera:
            raise ValueError(f"Falta {campo}")

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO compras.stock_salidas (
                    nro_salida, fecha, responsable, area, motivo, estado,
                    firma_img, maquina, tipo_reparacion, grupo, horas,
                    motivo_reparacion, usuario_id
                ) VALUES (
                    %(nro_salida)s, %(fecha)s, %(responsable)s, %(area)s,
                    %(motivo)s, %(estado)s, %(firma_img)s, %(maquina)s,
                    %(tipo_reparacion)s, %(grupo)s, %(horas)s,
                    %(motivo_reparacion)s, %(usuario_id)s
                )
                RETURNING *
                """,
                {
                    "nro_salida": cabecera["nro_salida"],
                    "fecha": cabecera["fecha"],
                    "responsable": cabecera["responsable"],
                    "area": cabecera["area"],
                    "motivo": cabecera.get("motivo"),
                    "estado": cabecera.get("estado", "Emitida"),
                    "firma_img": cabecera.get("firma_img"),
                    "maquina": cabecera.get("maquina"),
                    "tipo_reparacion": cabecera.get("tipo_reparacion"),
                    "grupo": cabecera.get("grupo"),
                    "horas": cabecera.get("horas"),
                    "motivo_reparacion": cabecera.get("motivo_reparacion"),
                    "usuario_id": cabecera.get("usuario_id"),
                },
            )
            salida = cur.fetchone()

            for item in items:
                cantidad = item["cantidad"]
                codigo = item.get("codigo")
                maestro_id = item.get("maestro_id")

                if descontar_stock and (maestro_id or codigo):
                    # Descuento dentro de la misma transacción
                    if maestro_id is None:
                        cur.execute(
                            "SELECT id, cantidad FROM compras.stock_maestro WHERE codigo = %s",
                            (codigo,),
                        )
                        m = cur.fetchone()
                        if not m:
                            raise ValueError(f"Código no encontrado en pañol: {codigo}")
                        maestro_id = m["id"]

                    cur.execute(
                        """
                        UPDATE compras.stock_maestro
                        SET cantidad = cantidad - %s,
                            actualizado_en = CURRENT_TIMESTAMP
                        WHERE id = %s AND cantidad >= %s
                        RETURNING *
                        """,
                        (cantidad, maestro_id, cantidad),
                    )
                    if cur.fetchone() is None:
                        raise ValueError(
                            f"Stock insuficiente para maestro_id={maestro_id}"
                        )

                    cur.execute(
                        """
                        INSERT INTO compras.stock_movimientos (
                            tipo, maestro_id, codigo, descripcion, cantidad,
                            unidad, referencia, responsable, usuario_id
                        ) VALUES (
                            'salida', %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            maestro_id,
                            codigo,
                            item.get("descripcion"),
                            cantidad,
                            item.get("unidad"),
                            cabecera["nro_salida"],
                            cabecera["responsable"],
                            cabecera.get("usuario_id"),
                        ),
                    )

                cur.execute(
                    """
                    INSERT INTO compras.salida_items (
                        salida_id, maestro_id, codigo, codigo_original,
                        descripcion, cantidad, unidad
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        salida["id"],
                        maestro_id,
                        codigo,
                        item.get("codigo_original"),
                        item["descripcion"],
                        cantidad,
                        item.get("unidad"),
                    ),
                )

            cur.execute(
                "SELECT * FROM compras.salida_items WHERE salida_id = %s ORDER BY id",
                (salida["id"],),
            )
            salida["items"] = list(cur.fetchall())
            return salida


def eliminar(nro_salida: str) -> int:
    """Borra la salida (cascada ítems). No reintegra stock automáticamente."""
    return db.execute(
        "DELETE FROM compras.stock_salidas WHERE nro_salida = %s",
        (nro_salida,),
    )
