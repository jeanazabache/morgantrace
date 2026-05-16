# ─────────────────────────────────────────────────────────────────────────────
# MorganTrace — Logger de Auditoría
# Autor: Jean Pierre Azabache
#
# Registra cada predicción de fraude en un archivo JSONL (una línea por evento).
# Formato pensado para cumplimiento y trazabilidad, similar a lo que exige
# regulación bancaria (SBS en Perú, PCI-DSS internacionalmente).
#
# Archivo de salida: logs/predicciones.jsonl
# Formato por línea:
#   {
#     "timestamp": "2025-05-15T10:23:01.123456",
#     "endpoint": "/predict",
#     "monto_transaccion": 1500.0,
#     "nivel_riesgo": "BAJO",
#     "es_fraude": false,
#     "probabilidad_fraude": 0.023,
#     "confianza_modelo": 0.977,
#     "tiempo_inferencia_ms": 2.847
#   }
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("morgantrace.audit")

# Ruta configurable vía variable de entorno (útil para Docker/k8s)
RUTA_LOG = Path(os.getenv("AUDIT_LOG_PATH", "logs/predicciones.jsonl"))


def _asegurar_directorio() -> None:
    """Crea la carpeta logs/ si no existe."""
    RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)


def registrar_prediccion(
    *,
    endpoint: str,
    monto_transaccion: float,
    nivel_riesgo: str,
    es_fraude: bool,
    probabilidad_fraude: float,
    confianza_modelo: float,
    tiempo_inferencia_ms: float,
    lote_size: Optional[int] = None,
) -> None:
    """
    Escribe un registro de auditoría en formato JSON Lines.

    Parámetros:
        endpoint            Ruta que generó la predicción ('/predict' o '/predict/batch').
        monto_transaccion   Monto analizado (o monto promedio del lote).
        nivel_riesgo        'BAJO', 'MEDIO' o 'ALTO'.
        es_fraude           True si el modelo clasificó como fraude.
        probabilidad_fraude Probabilidad de fraude entre 0.0 y 1.0.
        confianza_modelo    Confianza de la predicción entre 0.0 y 1.0.
        tiempo_inferencia_ms Latencia de inferencia en milisegundos.
        lote_size           Número de transacciones (solo para /predict/batch).
    """
    _asegurar_directorio()

    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "monto_transaccion": monto_transaccion,
        "nivel_riesgo": nivel_riesgo,
        "es_fraude": es_fraude,
        "probabilidad_fraude": probabilidad_fraude,
        "confianza_modelo": confianza_modelo,
        "tiempo_inferencia_ms": tiempo_inferencia_ms,
    }

    # Campo extra solo para llamadas batch
    if lote_size is not None:
        registro["lote_size"] = lote_size

    try:
        with open(RUTA_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError as e:
        # No interrumpir la API si el log falla — solo alertar
        logger.error(f"❌ No se pudo escribir en el log de auditoría: {e}")
