#!/usr/bin/env bash
# =============================================================================
# MorganTrace — Script de configuración del cluster k3d
# Crea el cluster local, construye la imagen Docker y despliega la API
# Autor: Jean Pierre Azabache
# Uso: bash k3d/setup.sh
# =============================================================================

set -euo pipefail

CLUSTER_NAME="morgantrace"
IMAGE_NAME="morgantrace"
IMAGE_TAG="latest"
REGISTRY_PORT="5050"
REGISTRY_NAME="k3d-registry.localhost"
API_PORT_HOST="8080"
API_PORT_K8S="30080"

echo "====================================================================="
echo " MorganTrace — Despliegue en k3d"
echo " Autor: Jean Pierre Azabache"
echo "====================================================================="

# Paso 1: Verificar dependencias
echo "[1/6] Verificando dependencias (k3d, kubectl, docker)..."
for cmd in k3d kubectl docker; do
    command -v "$cmd" &>/dev/null || { echo "❌ '$cmd' no instalado"; exit 1; }
done
echo "✅ Dependencias OK"

# Paso 2: Crear registro local de imágenes Docker
echo "[2/6] Configurando registro local..."
if k3d registry list 2>/dev/null | grep -q "$REGISTRY_NAME"; then
    echo "ℹ️  Registro ya existe, se reutiliza"
else
    k3d registry create "$REGISTRY_NAME" --port "$REGISTRY_PORT"
    echo "✅ Registro creado en localhost:$REGISTRY_PORT"
fi

# Paso 3: Crear cluster k3d
echo "[3/6] Creando cluster k3d '$CLUSTER_NAME'..."
if k3d cluster list 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    echo "ℹ️  Cluster ya existe, se reutiliza"
else
    k3d cluster create "$CLUSTER_NAME" \
        --port "${API_PORT_HOST}:${API_PORT_K8S}@loadbalancer" \
        --agents 2 \
        --registry-use "k3d-${REGISTRY_NAME}:${REGISTRY_PORT}" \
        --wait
    echo "✅ Cluster '$CLUSTER_NAME' creado"
fi
kubectl config use-context "k3d-${CLUSTER_NAME}"

# Paso 4: Construir y subir imagen Docker
echo "[4/6] Construyendo imagen Docker..."
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "localhost:${REGISTRY_PORT}/${IMAGE_NAME}:${IMAGE_TAG}"
docker push "localhost:${REGISTRY_PORT}/${IMAGE_NAME}:${IMAGE_TAG}"
echo "✅ Imagen construida y subida al registro k3d"

# Paso 5: Aplicar manifiestos Kubernetes
echo "[5/6] Aplicando manifiestos Kubernetes..."
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
echo "✅ Manifiestos aplicados"

# Paso 6: Esperar que los pods estén listos
echo "[6/6] Esperando pods..."
kubectl rollout status deployment/morgantrace-api --timeout=120s

echo ""
echo "====================================================================="
echo " ✅ MorganTrace desplegado exitosamente en k3d!"
echo "====================================================================="
echo " Pods activos:"
kubectl get pods -l app=morgantrace
echo ""
echo " HPA:"
kubectl get hpa morgantrace-hpa
echo ""
echo " 🚀 API: http://localhost:${API_PORT_HOST}"
echo " 📊 Swagger: http://localhost:${API_PORT_HOST}/docs"
echo ""
echo " 🧪 Prueba rápida:"
echo "   curl http://localhost:${API_PORT_HOST}/health"
echo ""
echo "   curl -X POST http://localhost:${API_PORT_HOST}/predict \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"monto_transaccion\": 1500.00, \"delta_tiempo\": 86400.0, \"tipo_tarjeta\": \"credit\"}'"
echo "====================================================================="
