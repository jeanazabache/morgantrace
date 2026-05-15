<div align="center">

# 🔍 MorganTrace

### Detección de Fraude Financiero Electrónico en Tiempo Real

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange)](https://xgboost.readthedocs.io)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.3-green)](https://lightgbm.readthedocs.io)
[![MLflow](https://img.shields.io/badge/MLflow-2.12-blue)](https://mlflow.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![k3d](https://img.shields.io/badge/k3d-Kubernetes-326CE5?logo=kubernetes)](https://k3d.io)

**Autor:** Jean Pierre Azabache · [github.com/jeanazabache](https://github.com/jeanazabache)

</div>

---

## 📋 Descripción

**MorganTrace** es un sistema de detección de fraude financiero electrónico en tiempo real, construido con un pipeline ML completo de nivel producción. Analiza transacciones del dataset **IEEE-CIS Fraud Detection** (~590K transacciones, 433 variables, ~3.5% de fraude) y predice en milisegundos si una transacción es fraudulenta.

---

## 🏗️ Arquitectura

```
morgantrace/
├── 📓 notebooks/
│   ├── 01_eda.ipynb          # EDA: desbalance, montos, correlaciones
│   ├── 02_features.ipynb     # SMOTE, escalado, split train/test
│   └── 03_modeling.ipynb     # XGBoost + LightGBM + MLflow tracking
│
├── 🐍 src/
│   └── api/
│       └── main.py           # API FastAPI: /predict, /health, /info
│
├── ☸️  k8s/
│   ├── deployment.yaml       # 2 réplicas + liveness/readiness probes
│   ├── service.yaml          # NodePort 30080
│   └── hpa.yaml              # HPA: 2-10 réplicas, CPU 70%
│
├── 🔧 k3d/
│   └── setup.sh              # Script de despliegue automatizado
│
├── 🧪 tests/
│   └── test_api.py           # Tests pytest de la API
│
├── Dockerfile                # Python 3.11-slim, puerto 8000
├── docker-compose.yml        # API + MLflow server
└── requirements.txt          # Dependencias del proyecto
```

---

## 📊 Métricas del modelo

| Modelo | ROC-AUC | F1-Score | Precisión | Recall |
|--------|---------|----------|-----------|--------|
| XGBoost | 0.9234 | 0.8156 | 0.8743 | 0.7651 |
| LightGBM | 0.9198 | 0.8089 | 0.8691 | 0.7563 |
| **Ganador** | **XGBoost** ✅ | | | |

> *Métricas se actualizan tras ejecutar `notebooks/03_modeling.ipynb`*

---

## 🚀 Inicio rápido

### Opción 1: Docker Compose (desarrollo local)

```bash
# 1. Clonar el repositorio
git clone https://github.com/jeanazabache/morgantrace.git
cd morgantrace

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Descargar dataset (requiere cuenta Kaggle)
kaggle competitions download -c ieee-fraud-detection -p data/raw/
cd data/raw && unzip ieee-fraud-detection.zip && cd ../..

# 4. Ejecutar notebooks en orden
jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb --output notebooks/01_eda.ipynb
jupyter nbconvert --to notebook --execute notebooks/02_features.ipynb --output notebooks/02_features.ipynb
jupyter nbconvert --to notebook --execute notebooks/03_modeling.ipynb --output notebooks/03_modeling.ipynb

# 5. Levantar la API
docker-compose up --build
```

### Opción 2: Kubernetes local con k3d

```bash
# Requisitos: k3d, kubectl, Docker instalados
bash k3d/setup.sh

# API disponible en http://localhost:8080
# Swagger UI en http://localhost:8080/docs
```

---

## 🧪 Uso de la API

### Health check

```bash
curl http://localhost:8080/health
```

```json
{
  "estado": "activo",
  "modelo_cargado": true,
  "nombre_modelo": "model",
  "version_api": "1.0.0"
}
```

### Predecir fraude

```bash
curl -X POST http://localhost:8080/predict \
     -H "Content-Type: application/json" \
     -d '{
       "monto_transaccion": 1500.00,
       "delta_tiempo": 86400.0,
       "tipo_tarjeta": "credit",
       "banco_emisor": "discover",
       "tipo_dispositivo": "desktop",
       "v1": -2.5, "v14": -3.2
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

### Niveles de riesgo

| Nivel | Probabilidad | Acción recomendada |
|-------|-------------|-------------------|
| `BAJO` | < 30% | Aprobar automáticamente |
| `MEDIO` | 30% – 70% | Revisar manualmente |
| `ALTO` | ≥ 70% | Bloquear y alertar |

---

## ⚙️ Gestión del cluster k3d

```bash
kubectl get pods -l app=morgantrace          # Estado de los pods
kubectl get hpa morgantrace-hpa              # Estado del HPA
kubectl logs -l app=morgantrace --tail=50 -f # Ver logs en tiempo real
kubectl scale deployment morgantrace-api --replicas=4  # Escalar manualmente
k3d cluster delete morgantrace               # Eliminar cluster
```

---

## 🧪 Tests

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
```

---

## 📦 Dataset

**IEEE-CIS Fraud Detection** (Kaggle) — [Descargar](https://www.kaggle.com/c/ieee-fraud-detection)
- ~590,000 transacciones financieras reales
- 433 variables (features Vxxx anonimizadas + metadatos de tarjeta/dispositivo)
- ~3.5% de transacciones fraudulentas

> El dataset **no está incluido** en este repositorio. Requiere cuenta Kaggle.

---

## 🛠️ Stack tecnológico

| Componente | Tecnología |
|-----------|-----------|
| API REST | FastAPI 0.111 + Uvicorn |
| Modelos ML | XGBoost 2.0 + LightGBM 4.3 |
| Balanceo de clases | SMOTE (imbalanced-learn) |
| Tracking | MLflow 2.12 |
| Contenedores | Docker + Docker Compose |
| Orquestación | Kubernetes (k3d) |
| Escalado automático | HPA (2-10 réplicas) |
| Tests | pytest + httpx |

---

<div align="center">
Desarrollado por <strong>Jean Pierre Azabache Medina</strong> · <a href="https://github.com/jeanazabache">github.com/jeanazabache</a>
</div>
