"""Historial de versiones de calificaciones en MongoDB."""
import logging

from bson import Decimal128
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from config.mongo import obtener_db

logger = logging.getLogger(__name__)


def version_documento(calificacion, factores, origen, usuario_email, motivo, fecha):
    """Arma la foto de una calificación y sus factores en un momento dado."""
    return {
        "calificacion_id": calificacion.pk,
        "corredora_id": calificacion.corredora_id,
        "instrumento_id": calificacion.instrumento_id,
        "ejercicio_comercial": calificacion.ejercicio_comercial,
        "secuencia_evento": calificacion.secuencia_evento,
        "fecha_pago": calificacion.fecha_pago.isoformat(),
        "origen": origen,
        "usuario": usuario_email,
        "motivo": motivo,
        "fecha": fecha,
        # Decimal128 conserva los 8 decimales exactos (un float los alteraría)
        "factores": {str(columna): Decimal128(str(valor)) for columna, valor in factores.items()},
    }


def registrar_versiones(versiones):
    if not versiones:
        return
    try:
        obtener_db().historial_calificaciones.insert_many(versiones, ordered=False)
    except PyMongoError:
        logger.exception("No se pudo guardar el historial de %s calificaciones en MongoDB", len(versiones))


def obtener_historial(calificacion_id):
    try:
        return list(obtener_db().historial_calificaciones
                    .find({"calificacion_id": calificacion_id}, {"_id": 0})
                    .sort("fecha", DESCENDING))
    except PyMongoError:
        return []