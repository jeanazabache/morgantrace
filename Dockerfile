# ─────────────────────────────────────────────────────────────────────────────
# MorganTrace — Imagen Docker
# Detección de fraude financiero con FastAPI + XGBoost/LightGBM
# Autor: Jean Pierre Azabache
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Jean Pierre Azabache"
LABEL project="MorganTrace"
LABEL description="API de detección de fraude financiero en tiempo real"
LABEL version="1.0.0"

WORKDIR /app

# Dependencias del sistema necesarias para libs de ML
RUN apt-get update && apt-get install -y \
    gcc g++ libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python (primero para caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/

# Crear directorios necesarios y usuario no-root (buena práctica de seguridad)
RUN mkdir -p src/models logs && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MODEL_PATH=src/models/model.pkl
ENV AUDIT_LOG_PATH=logs/predicciones.jsonl

# Un solo worker: el modelo se carga una vez en memoria.
# El escalado horizontal lo maneja Kubernetes (HPA).
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
