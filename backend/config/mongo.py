"""Conexión a MongoDB, la base documental del sistema híbrido."""
from django.conf import settings
from pymongo import ASCENDING, DESCENDING, MongoClient

_cliente = None


def obtener_db():
    """Devuelve la base de MongoDB, reutilizando una sola conexión por proceso."""
    global _cliente
    if _cliente is None:
        _cliente = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
    return _cliente[settings.MONGO_DB]


def crear_indices():
    """Índices para que las consultas por archivo, calificación y corredora sean rápidas."""
    db = obtener_db()
    db.resultados_carga.create_index([("archivo_id", ASCENDING)], unique=True)
    db.resultados_carga.create_index([("corredora_id", ASCENDING), ("fecha", DESCENDING)])
    db.historial_calificaciones.create_index([("calificacion_id", ASCENDING), ("fecha", DESCENDING)])
    db.historial_calificaciones.create_index([("corredora_id", ASCENDING), ("ejercicio_comercial", ASCENDING)])