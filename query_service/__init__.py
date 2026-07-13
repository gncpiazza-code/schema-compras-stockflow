"""
Query Service — capa de datos StockFlow.

La UI (CustomTkinter) solo importa módulos de este paquete.
No debe ejecutar SQL ni abrir conexiones por su cuenta.
"""

from query_service.db import get_connection, get_connection_params

__all__ = ["get_connection", "get_connection_params"]
