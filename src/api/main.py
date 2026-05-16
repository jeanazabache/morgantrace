# ─────────────────────────────────────────────────────────────────────────────
# MorganTrace — API Principal de Detección de Fraude
# Framework: FastAPI | Modelo: XGBoost / LightGBM
# Autor: Jean Pierre Azabache
# ─────────────────────────────────────────────────────────────────────────────
"""
MorganTrace: API en tiempo real para detección de fraude financiero.

Endpoints:
    GET  /health         → Estado de salud del servicio (liveness probe)
    POST /predict        → Predicción de fraude para una transacción
    POST /predict/batch  → Predicción de fraude para múltiples transacciones
    GET  /info           → Información sobre el modelo cargado
"""

import os
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ── Configuración del logger ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("morgantrace")

# ── Ruta al modelo serializado ────────────────────────────────────────────────
RUTA_MODELO = os.getenv("MODEL_PATH", "src/models/model.pkl")

# Estado global del modelo (cargado al iniciar la app)
estado = {"modelo": None, "nombre_modelo": None, "cargado_en": None}


# ── Ciclo de vida de la aplicación ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo al iniciar y libera recursos al apagar."""
    ruta = Path(RUTA_MODELO)
    if ruta.exists():
        try:
            estado["modelo"] = joblib.load(ruta)
            estado["nombre_modelo"] = ruta.stem
            estado["cargado_en"] = time.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"✅ Modelo cargado desde: {ruta}")
        except Exception as e:
            logger.error(f"❌ Error al cargar el modelo: {e}")
    else:
        logger.warning(
            f"⚠️  Modelo no encontrado en: {ruta} — "
            "ejecuta el notebook 03_modeling.ipynb primero"
        )
    yield
    logger.info("🔴 Apagando MorganTrace API...")


# ── Instancia FastAPI ─────────────────────────────────────────────────────────
app = FastAPI(
    title="MorganTrace API",
    description=(
        "API de detección de fraude financiero electrónico en tiempo real. "
        "Dataset: IEEE-CIS Fraud Detection (~590K transacciones). "
        "Modelos: XGBoost + LightGBM con seguimiento MLflow."
    ),
    version="1.0.0",
    contact={
        "name": "Jean Pierre Azabache",
        "url": "https://github.com/jeanazabache/morgantrace",
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Esquemas Pydantic ─────────────────────────────────────────────────────────
class TransaccionEntrada(BaseModel):
    """Datos de entrada para la predicción de fraude."""

    monto_transaccion: float = Field(
        ..., gt=0, description="Monto de la transacción en USD", example=150.75
    )
    delta_tiempo: float = Field(
        ..., ge=0, description="Segundos desde la primera transacción del dataset", example=86400.0
    )
    tipo_tarjeta: Optional[str] = Field(None, description="'credit' o 'debit'", example="credit")
    banco_emisor: Optional[str] = Field(None, description="Banco emisor", example="discover")
    tipo_dispositivo: Optional[str] = Field(None, description="desktop/mobile/tablet", example="desktop")
    v1: Optional[float] = Field(None, description="Feature V1 IEEE-CIS")
    v2: Optional[float] = Field(None, description="Feature V2 IEEE-CIS")
    v3: Optional[float] = Field(None, description="Feature V3 IEEE-CIS")
    v4: Optional[float] = Field(None, description="Feature V4 IEEE-CIS")
    v12: Optional[float] = Field(None, description="Feature V12 IEEE-CIS")
    v14: Optional[float] = Field(None, description="Feature V14 IEEE-CIS")
    v17: Optional[float] = Field(None, description="Feature V17 IEEE-CIS")

    @field_validator("monto_transaccion")
    @classmethod
    def validar_monto(cls, v):
        if v > 20_000:
            raise ValueError("Monto excede el límite de $20,000 para este modelo")
        return round(v, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "monto_transaccion": 150.75,
                "delta_tiempo": 86400.0,
                "tipo_tarjeta": "credit",
                "banco_emisor": "discover",
                "tipo_dispositivo": "desktop",
                "v1": -1.2, "v2": 0.5, "v3": 2.1, "v4": -0.8,
                "v12": 1.3, "v14": -0.4, "v17": 0.9,
            }
        }


class ResultadoPrediccion(BaseModel):
    """Resultado del endpoint /predict."""

    es_fraude: bool = Field(..., description="True si la transacción es sospechosa")
    probabilidad_fraude: float = Field(..., description="Probabilidad de fraude (0.0 – 1.0)")
    nivel_riesgo: str = Field(..., description="BAJO, MEDIO o ALTO")
    confianza_modelo: float = Field(..., description="Confianza de la predicción")
    tiempo_inferencia_ms: float = Field(..., description="Tiempo de inferencia en ms")
    mensaje: str = Field(..., description="Descripción legible del resultado")


class EstadoSalud(BaseModel):
    """Respuesta del endpoint /health."""

    estado: str
    modelo_cargado: bool
    nombre_modelo: Optional[str]
    version_api: str


class SolicitudBatch(BaseModel):
    """Cuerpo de entrada para el endpoint /predict/batch."""

    transacciones: List[TransaccionEntrada] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Lista de transacciones a evaluar (máximo 500 por llamada)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transacciones": [
                    {
                        "monto_transaccion": 150.75,
                        "delta_tiempo": 86400.0,
                        "tipo_tarjeta": "credit",
                        "banco_emisor": "discover",
                        "v14": -0.4,
                    },
                    {
                        "monto_transaccion": 9999.99,
                        "delta_tiempo": 120.0,
                        "tipo_tarjeta": "credit",
                        "banco_emisor": "visa",
                        "v14": -5.2,
                    },
                ]
            }
        }


class ResultadoBatch(BaseModel):
    """Respuesta del endpoint /predict/batch."""

    total_transacciones: int = Field(..., description="Número de transacciones evaluadas")
    total_fraudes: int = Field(..., description="Número de transacciones marcadas como fraude")
    porcentaje_fraude: float = Field(..., description="Porcentaje de fraude en el lote (%)")
    tiempo_total_ms: float = Field(..., description="Tiempo total de inferencia del lote en ms")
    resultados: List[ResultadoPrediccion] = Field(..., description="Resultado individual por transacción")


# ── Funciones auxiliares ──────────────────────────────────────────────────────
def calcular_nivel_riesgo(probabilidad: float) -> str:
    """
    Clasifica el riesgo según la probabilidad de fraude.

    Umbrales (calibrados para dataset IEEE-CIS, ~3.5% fraude):
        BAJO:  prob < 0.30
        MEDIO: 0.30 ≤ prob < 0.70
        ALTO:  prob ≥ 0.70
    """
    if probabilidad < 0.30:
        return "BAJO"
    elif probabilidad < 0.70:
        return "MEDIO"
    return "ALTO"


def preparar_caracteristicas(t: TransaccionEntrada) -> np.ndarray:
    """Convierte los datos de la transacción en un vector numérico para el modelo."""
    mapa_tarjeta = {"credit": 1.0, "debit": 0.0}
    mapa_banco = {"discover": 0.0, "mastercard": 1.0, "visa": 2.0, "american express": 3.0}
    mapa_dispositivo = {"desktop": 0.0, "mobile": 1.0, "tablet": 2.0}

    return np.array([[
        t.monto_transaccion,
        t.delta_tiempo,
        mapa_tarjeta.get(str(t.tipo_tarjeta).lower(), 0.5),
        mapa_banco.get(str(t.banco_emisor).lower(), 4.0),
        mapa_dispositivo.get(str(t.tipo_dispositivo).lower(), 3.0),
        t.v1 or 0.0, t.v2 or 0.0, t.v3 or 0.0, t.v4 or 0.0,
        t.v12 or 0.0, t.v14 or 0.0, t.v17 or 0.0,
    ]], dtype=np.float64)


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health", response_model=EstadoSalud, summary="Estado del servicio", tags=["Monitoreo"])
async def verificar_salud():
    """Verifica que la API está activa. Usado por liveness/readiness probes de Kubernetes."""
    return EstadoSalud(
        estado="activo",
        modelo_cargado=estado["modelo"] is not None,
        nombre_modelo=estado["nombre_modelo"],
        version_api=app.version,
    )


@app.post(
    "/predict",
    response_model=ResultadoPrediccion,
    summary="Predecir fraude en una transacción",
    tags=["Predicción"],
)
async def predecir_fraude(transaccion: TransaccionEntrada):
    """
    Analiza una transacción financiera y determina si es fraudulenta.

    **Niveles de riesgo:**
    - `BAJO`  → probabilidad < 30%
    - `MEDIO` → probabilidad entre 30% y 70%
    - `ALTO`  → probabilidad ≥ 70%
    """
    if estado["modelo"] is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo no disponible. Ejecuta el notebook 03_modeling.ipynb.",
        )

    inicio = time.perf_counter()
    try:
        X = preparar_caracteristicas(transaccion)
        prediccion = estado["modelo"].predict(X)[0]
        probs = estado["modelo"].predict_proba(X)[0]
        prob_fraude = float(probs[1])
        es_fraude = bool(prediccion == 1)
        nivel_riesgo = calcular_nivel_riesgo(prob_fraude)
        confianza = float(max(probs))
    except Exception as e:
        logger.error(f"Error en inferencia: {e}")
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")

    tiempo_ms = (time.perf_counter() - inicio) * 1000
    mensaje = (
        f"⚠️ ALERTA: Transacción sospechosa (riesgo {nivel_riesgo})"
        if es_fraude
        else f"✅ Transacción legítima (riesgo {nivel_riesgo})"
    )

    logger.info(f"Predicción | fraude={es_fraude} | prob={prob_fraude:.4f} | {nivel_riesgo} | {tiempo_ms:.1f}ms")

    return ResultadoPrediccion(
        es_fraude=es_fraude,
        probabilidad_fraude=round(prob_fraude, 6),
        nivel_riesgo=nivel_riesgo,
        confianza_modelo=round(confianza, 6),
        tiempo_inferencia_ms=round(tiempo_ms, 3),
        mensaje=mensaje,
    )


@app.post(
    "/predict/batch",
    response_model=ResultadoBatch,
    summary="Predecir fraude en múltiples transacciones",
    tags=["Predicción"],
)
async def predecir_fraude_batch(solicitud: SolicitudBatch):
    """
    Analiza un lote de transacciones financieras en una sola llamada.

    Útil para procesar múltiples transacciones de forma eficiente,
    como en revisiones periódicas o cierres de turno bancario.

    **Límite:** máximo 500 transacciones por llamada.

    **Respuesta incluye:**
    - Resultado individual de cada transacción
    - Resumen del lote: total de fraudes y porcentaje
    """
    if estado["modelo"] is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo no disponible. Ejecuta el notebook 03_modeling.ipynb.",
        )

    inicio_total = time.perf_counter()
    resultados: List[ResultadoPrediccion] = []

    try:
        # Construir matriz de features para todas las transacciones de una vez
        X = np.vstack([preparar_caracteristicas(t) for t in solicitud.transacciones])
        predicciones = estado["modelo"].predict(X)
        probabilidades = estado["modelo"].predict_proba(X)
    except Exception as e:
        logger.error(f"Error en inferencia batch: {e}")
        raise HTTPException(status_code=500, detail=f"Error en predicción batch: {str(e)}")

    for i, transaccion in enumerate(solicitud.transacciones):
        inicio_item = time.perf_counter()
        prob_fraude = float(probabilidades[i][1])
        es_fraude = bool(predicciones[i] == 1)
        nivel_riesgo = calcular_nivel_riesgo(prob_fraude)
        confianza = float(max(probabilidades[i]))
        tiempo_item_ms = (time.perf_counter() - inicio_item) * 1000

        mensaje = (
            f"⚠️ ALERTA: Transacción sospechosa (riesgo {nivel_riesgo})"
            if es_fraude
            else f"✅ Transacción legítima (riesgo {nivel_riesgo})"
        )
        resultados.append(
            ResultadoPrediccion(
                es_fraude=es_fraude,
                probabilidad_fraude=round(prob_fraude, 6),
                nivel_riesgo=nivel_riesgo,
                confianza_modelo=round(confianza, 6),
                tiempo_inferencia_ms=round(tiempo_item_ms, 3),
                mensaje=mensaje,
            )
        )

    tiempo_total_ms = (time.perf_counter() - inicio_total) * 1000
    total_fraudes = sum(1 for r in resultados if r.es_fraude)
    porcentaje = round(total_fraudes / len(resultados) * 100, 2)

    logger.info(
        f"Batch | transacciones={len(resultados)} | fraudes={total_fraudes} "
        f"({porcentaje}%) | {tiempo_total_ms:.1f}ms total"
    )

    return ResultadoBatch(
        total_transacciones=len(resultados),
        total_fraudes=total_fraudes,
        porcentaje_fraude=porcentaje,
        tiempo_total_ms=round(tiempo_total_ms, 3),
        resultados=resultados,
    )


@app.get("/info", summary="Información del modelo", tags=["Monitoreo"])
async def informacion_modelo():
    """Devuelve metadatos del modelo actualmente cargado."""
    if estado["modelo"] is None:
        return {"estado": "sin_modelo", "mensaje": "Ejecuta 03_modeling.ipynb para entrenar el modelo"}

    info = {
        "nombre": estado["nombre_modelo"],
        "cargado_en": estado["cargado_en"],
        "tipo": type(estado["modelo"]).__name__,
        "ruta": RUTA_MODELO,
    }
    if hasattr(estado["modelo"], "get_params"):
        params = estado["modelo"].get_params()
        info["parametros_clave"] = {
            k: v for k, v in params.items()
            if k in ["n_estimators", "max_depth", "learning_rate", "n_jobs"]
        }
    return {"modelo": info, "api_version": app.version}
