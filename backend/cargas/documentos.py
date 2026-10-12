"""Detalle de cada carga masiva en MongoDB."""
import logging

from django.utils import timezone
from pymongo.errors import PyMongoError

from config.mongo import obtener_db

logger = logging.getLogger(__name__)


def guardar_resultado_carga(archivo, resumen, errores, previsualizacion):
    documento = {
        "archivo_id": archivo.pk,
        "nombre_archivo": archivo.nombre_archivo,
        "corredora_id": archivo.cargado_por.corredora_id,
        "cargado_por": archivo.cargado_por.email,
        "formato_tipo": archivo.formato_tipo,
        "estado": archivo.estado_carga,
        "fecha": timezone.now(),
        "resumen": resumen,
        "errores": errores,
        "previsualizacion": previsualizacion,
    }
    try:
        # Si el archivo se reprocesa, se reemplaza su resultado anterior
        obtener_db().resultados_carga.replace_one({"archivo_id": archivo.pk}, documento, upsert=True)
    except PyMongoError:
        logger.exception("No se pudo guardar el resultado de la carga %s en MongoDB", archivo.pk)


def obtener_resultado_carga(archivo_id):
    try:
        return obtener_db().resultados_carga.find_one({"archivo_id": archivo_id}, {"_id": 0})
    except PyMongoError:
        return None