<div align="center">

# 🔍 MorganTrace

### Sistema de Detección de Fraude Financiero Electrónico en Tiempo Real

[![CI](https://github.com/jeanazabache/morgantrace/actions/workflows/ci.yml/badge.svg)](https://github.com/jeanazabache/morgantrace/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange)](https://xgboost.readthedocs.io)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.3-green)](https://lightgbm.readthedocs.io)
[![MLflow](https://img.shields.io/badge/MLflow-2.12-blue)](https://mlflow.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-k3d-326CE5?logo=kubernetes)](https://k3d.io)
[![Prometheus](https://img.shields.io/badge/Prometheus-2.51-E6522C?logo=prometheus)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Grafana-10.4-F46800?logo=grafana)](https://grafana.com)

**Autor:** Jean Pierre Azabache · [github.com/jeanazabache](https://github.com/jeanazabache)

</div>

---

## 💡 Motivación

El fraude electrónico es uno de los mayores desafíos del sector financiero peruano y global. Según la SBS, las pérdidas por fraude con tarjetas representan millones de soles anuales, y los bancos necesitan sistemas capaces de detectar operaciones sospechosas **en milisegundos**, sin interrumpir la experiencia del cliente legítimo.

**MorganTrace** nació como un proyecto personal para explorar cómo la industria financiera aplica Machine Learning en producción. El nombre está inspirado en J.P. Morgan, figura icónica de la banca moderna. El objetivo fue construir un pipeline ML completo — desde el análisis exploratorio hasta el despliegue en Kubernetes — aplicando las mismas prácticas que usan los equipos de Data Science en bancos como BCP, Interbank o BBVA:

- **Modelos con alta precisión** sobre datos reales de fraude (IEEE-CIS, ~590K transacciones)
- **API de inferencia en tiempo real** con FastAPI, con respuesta en ~3ms
- **Escalado automático** con Kubernetes HPA (2 a 10 réplicas según carga)
- **Auditoría completa** de cada decisión del modelo (requerimiento regulatorio SBS / PCI-DSS)
- **Monitoreo operacional** con Prometheus + Grafana para observar el comportamiento en producción

---

## 🏗️ Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTE                              │
│         (app bancaria, sistema de pagos, curl)              │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP REST
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   KUBERNETES (k3d local)                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              LoadBalancer :8080                      │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                       │
│       ┌─────────────┼─────────────┐                         │
│       ▼             ▼             ▼                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  HPA: 2–10 réplicas │
│  │  Pod 1  │  │  Pod 2  │  │  Pod N  │  CPU >70% → scale   │
│  │FastAPI  │  │FastAPI  │  │FastAPI  │                      │
│  └────┬────┘  └────┬────┘  └────┬────┘                      │
│       └────────────┼────────────┘                           │
└────────────────────│────────────────────────────────────────┘
                     │
        ┌────────────┼───────────────────┐
        ▼            ▼                   ▼
  ┌──────────┐  ┌─────────┐      ┌──────────────┐
  │ XGBoost  │  │  Audit  │      │  Prometheus  │
  │  model   │  │  Logger │      │   /metrics   │
  │ .pkl     │  │ .jsonl  │      └──────┬───────┘
  └──────────┘  └─────────┘             │
                                        ▼
                                  ┌──────────┐
                                  │ Grafana  │
                                  │dashboard │
                                  └──────────┘
```

### Flujo de una predicción

```
Transacción → Validación Pydantic → Preparar features → XGBoost.predict()
           → Calcular nivel_riesgo → Audit log (JSONL) → Métricas Prometheus
           → Respuesta JSON (~3ms)
```

---

## 📁 Estructura del proyecto

```
morgantrace/
│
├── 📓 notebooks/
│   ├── 01_eda.ipynb          # Análisis exploratorio: desbalance, montos, correlaciones
│   ├── 02_features.ipynb     # SMOTE, escalado, split train/test estratificado
│   └── 03_modeling.ipynb     # XGBoost + LightGBM + MLflow experiment tracking
│
├── 🐍 src/api/
│   ├── main.py               # API FastAPI: /predict, /predict/batch, /health, /info
│   └── audit_logger.py       # Logger de auditoría → logs/predicciones.jsonl
│
├── 📊 monitoring/
│   ├── prometheus.yml        # Configuración de scraping (cada 15s)
│   └── grafana/
│       ├── provisioning/     # Datasource + dashboard auto-provisionados
│       └── dashboards/       # Dashboard MorganTrace (8 paneles)
│
├── ☸️  k8s/
│   ├── deployment.yaml       # 2 réplicas, liveness/readiness probes, usuario no-root
│   ├── service.yaml          # NodePort :30080
│   └── hpa.yaml              # HPA: 2–10 réplicas, CPU 70% / memoria 80%
│
├── 🔧 k3d/
│   └── setup.sh              # Despliegue automatizado en un solo comando
│
├── 🧪 tests/
│   └── test_api.py           # 17 tests: endpoints + audit logger (pytest)
│
├── .github/workflows/
│   └── ci.yml                # GitHub Actions: tests automáticos en cada push
│
├── Dockerfile                # Python 3.11-slim, usuario no-root, puerto 8000
├── docker-compose.yml        # API + MLflow + Prometheus + Grafana
└── requirements.txt          # Dependencias del proyecto
```

---

## 📊 Métricas del modelo

| Modelo | ROC-AUC | F1-Score | Precisión | Recall |
|--------|---------|----------|-----------|--------|
| XGBoost | **0.9234** | **0.8156** | **0.8743** | **0.7651** |
| LightGBM | 0.9198 | 0.8089 | 0.8691 | 0.7563 |
| **Ganador** | **XGBoost** ✅ | | | |

> Dataset: IEEE-CIS Fraud Detection · ~590K transacciones · ~3.5% fraude · Balanceo con SMOTE

---

## 🚀 Inicio rápido

### Prerequisitos

```bash
# Verificar que están instalados:
python --version   # 3.11+
docker --version
kubectl version --client
k3d version
```

### Paso 1 — Clonar e instalar

```bash
git clone https://github.com/jeanazabache/morgantrace.git
cd morgantrace
pip install -r requirements.txt
```

### Paso 2 — Descargar el dataset (requiere cuenta Kaggle)

```bash
# Configurar API key de Kaggle primero:
# https://www.kaggle.com/settings → API → Create New Token

kaggle competitions download -c ieee-fraud-detection -p data/raw/
cd data/raw && unzip ieee-fraud-detection.zip && cd ../..
```

### Paso 3 — Entrenar el modelo

```bash
# Ejecutar los notebooks en orden (genera src/models/model.pkl)
jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/02_features.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/03_modeling.ipynb --inplace
```

### Paso 4A — Docker Compose (modo completo con monitoreo)

```bash
docker-compose up --build
```

| Servicio | URL | Descripción |
|----------|-----|-------------|
| API + Swagger | http://localhost:8000/docs | Documentación interactiva |
| MLflow | http://localhost:5000 | Tracking de experimentos |
| Prometheus | http://localhost:9090 | Métricas en tiempo real |
| **Grafana** | **http://localhost:3000** | **Dashboard visual (admin/admin)** |

### Paso 4B — Kubernetes con k3d (simulación de producción)

```bash
bash k3d/setup.sh
# API disponible en http://localhost:8080
```

---

## 🧪 Endpoints de la API

### `GET /health` — Liveness probe

```bash
curl http://localhost:8000/health
```

```json
{
  "estado": "activo",
  "modelo_cargado": true,
  "nombre_modelo": "model",
  "version_api": "1.0.0"
}
```

### `POST /predict` — Predicción individual

```bash
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "monto_transaccion": 1500.00,
       "delta_tiempo": 86400.0,
       "tipo_tarjeta": "credit",
       "banco_emisor": "discover",
       "tipo_dispositivo": "desktop",
       "v1": -2.5,
       "v14": -3.2
     }'
```

```json
{
  "es_fraude": false,
  "probabilidad_fraude": 0.023,
  "nivel_riesgo": "BAJO",
  "confianza_modelo": 0.977,
  "tiempo_inferencia_ms": 2.847,
  "mensaje": "✅ Transacción legítima (riesgo BAJO)"
}
```

### `POST /predict/batch` — Lote de transacciones

Procesa hasta **500 transacciones en una sola llamada** usando inferencia vectorizada.
Útil para revisiones periódicas o cierres de turno bancario.

```bash
curl -X POST http://localhost:8000/predict/batch \
     -H "Content-Type: application/json" \
     -d '{
       "transacciones": [
         {"monto_transaccion": 150.0, "delta_tiempo": 86400.0, "tipo_tarjeta": "credit"},
         {"monto_transaccion": 9999.0, "delta_tiempo": 120.0, "v14": -5.2}
       ]
     }'
```

```json
{
  "total_transacciones": 2,
  "total_fraudes": 1,
  "porcentaje_fraude": 50.0,
  "tiempo_total_ms": 4.21,
  "resultados": [...]
}
```

### Niveles de riesgo

| Nivel | Probabilidad | Acción recomendada |
|-------|-------------|-------------------|
| `BAJO` | < 30% | ✅ Aprobar automáticamente |
| `MEDIO` | 30% – 70% | ⚠️ Enviar a revisión manual |
| `ALTO` | ≥ 70% | 🚨 Bloquear y alertar al cliente |

---

## 📋 Auditoría y trazabilidad

Cada predicción se registra automáticamente en `logs/predicciones.jsonl` (una línea por evento), cumpliendo con los requisitos de trazabilidad del sector financiero:

```json
{
  "timestamp": "2025-05-15T10:23:01.123456+00:00",
  "endpoint": "/predict",
  "monto_transaccion": 1500.0,
  "nivel_riesgo": "BAJO",
  "es_fraude": false,
  "probabilidad_fraude": 0.023012,
  "confianza_modelo": 0.976988,
  "tiempo_inferencia_ms": 2.847
}
```

> El formato JSONL permite ingesta directa en herramientas como ElasticSearch, Splunk o AWS CloudWatch Logs.

---

## 📈 Monitoreo con Prometheus + Grafana

El sistema expone métricas HTTP estándar y métricas de negocio propias:

**Métricas de negocio (custom):**
- `morgantrace_predicciones_total` — contador por endpoint y nivel de riesgo
- `morgantrace_fraudes_detectados_total` — total de fraudes detectados

**Métricas HTTP automáticas:**
- Latencia por percentil (p50, p95, p99)
- Tasa de requests por endpoint
- Códigos de respuesta (2xx, 4xx, 5xx)

El dashboard de Grafana se carga automáticamente al hacer `docker-compose up`:

```
http://localhost:3000  →  usuario: admin  /  contraseña: admin
```

---

## ☸️ Gestión del cluster Kubernetes

```bash
# Estado general
kubectl get pods -l app=morgantrace
kubectl get hpa morgantrace-hpa
kubectl get svc morgantrace-service

# Logs en tiempo real
kubectl logs -l app=morgantrace --tail=50 -f

# Escalar manualmente
kubectl scale deployment morgantrace-api --replicas=5

# Limpiar
k3d cluster delete morgantrace
```

---

## 🧪 Tests

```bash
# Correr todos los tests
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ --cov=src --cov-report=html
```

El pipeline de CI corre los tests automáticamente en cada push a `main` vía GitHub Actions.

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| API REST | FastAPI 0.111 + Uvicorn |
| Modelos ML | XGBoost 2.0 + LightGBM 4.3 |
| Balanceo de clases | SMOTE (imbalanced-learn) |
| Experiment tracking | MLflow 2.12 |
| Auditoría | JSON Lines (`logs/predicciones.jsonl`) |
| Métricas | Prometheus 2.51 + prometheus-fastapi-instrumentator |
| Dashboards | Grafana 10.4 (auto-provisionado) |
| Contenedores | Docker + Docker Compose |
| Orquestación | Kubernetes via k3d |
| Escalado automático | HPA (2–10 réplicas, CPU 70% / memoria 80%) |
| CI/CD | GitHub Actions |
| Tests | pytest + httpx (17 tests) |

---

## 📦 Dataset

**IEEE-CIS Fraud Detection** (Kaggle) — [Descargar aquí](https://www.kaggle.com/c/ieee-fraud-detection)

| Característica | Detalle |
|---------------|---------|
| Transacciones | ~590,000 |
| Variables | 433 (features Vxxx anonimizadas + metadatos) |
| Tasa de fraude | ~3.5% (dataset desbalanceado) |
| Estrategia | SMOTE para balanceo en entrenamiento |

> El dataset **no está incluido** en este repositorio por su tamaño (~360 MB comprimido). Requiere cuenta Kaggle gratuita.

---

<div align="center">

Desarrollado por **Jean Pierre Azabache** · [github.com/jeanazabache](https://github.com/jeanazabache)

*Proyecto personal para explorar ML aplicado al sector financiero peruano*

</div>
