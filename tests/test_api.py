# ─────────────────────────────────────────────────────────────────────────────
# MorganTrace — Tests de la API
# Framework: pytest + httpx
# Autor: Jean Pierre Azabache
# ─────────────────────────────────────────────────────────────────────────────
"""
Tests unitarios e integración para la API de MorganTrace.
Ejecutar con: pytest tests/ -v
"""

import json
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.api.main import app
from src.api import audit_logger

cliente = TestClient(app)


class TestEndpointHealth:
    """Tests del endpoint GET /health."""

    def test_health_retorna_200(self):
        """El endpoint /health debe responder con código 200."""
        respuesta = cliente.get("/health")
        assert respuesta.status_code == 200

    def test_health_estructura_respuesta(self):
        """La respuesta debe contener los campos esperados."""
        respuesta = cliente.get("/health")
        datos = respuesta.json()
        assert "estado" in datos
        assert "modelo_cargado" in datos
        assert "version_api" in datos
        assert datos["estado"] == "activo"


class TestEndpointPredict:
    """Tests del endpoint POST /predict."""

    TRANSACCION_VALIDA = {
        "monto_transaccion": 150.75,
        "delta_tiempo": 86400.0,
        "tipo_tarjeta": "credit",
        "banco_emisor": "discover",
        "tipo_dispositivo": "desktop",
        "v1": -1.2, "v2": 0.5, "v3": 2.1, "v4": -0.8,
        "v12": 1.3, "v14": -0.4, "v17": 0.9,
    }

    def test_predict_sin_modelo_retorna_503(self):
        """Sin modelo cargado, /predict debe retornar 503."""
        respuesta = cliente.post("/predict", json=self.TRANSACCION_VALIDA)
        assert respuesta.status_code == 503

    def test_predict_monto_negativo_retorna_422(self):
        """Monto negativo debe fallar la validación (422)."""
        transaccion_invalida = {**self.TRANSACCION_VALIDA, "monto_transaccion": -100.0}
        respuesta = cliente.post("/predict", json=transaccion_invalida)
        assert respuesta.status_code == 422

    def test_predict_monto_excesivo_retorna_422(self):
        """Monto mayor a $20,000 debe fallar la validación."""
        transaccion_invalida = {**self.TRANSACCION_VALIDA, "monto_transaccion": 25000.0}
        respuesta = cliente.post("/predict", json=transaccion_invalida)
        assert respuesta.status_code == 422

    def test_predict_sin_campos_opcionales(self):
        """La predicción debe funcionar con solo los campos obligatorios."""
        transaccion_minima = {
            "monto_transaccion": 50.0,
            "delta_tiempo": 3600.0,
        }
        respuesta = cliente.post("/predict", json=transaccion_minima)
        # Sin modelo cargado espera 503, con modelo espera 200
        assert respuesta.status_code in [200, 503]


class TestEndpointPredictBatch:
    """Tests del endpoint POST /predict/batch."""

    TRANSACCION_VALIDA = {
        "monto_transaccion": 150.75,
        "delta_tiempo": 86400.0,
        "tipo_tarjeta": "credit",
        "banco_emisor": "discover",
        "tipo_dispositivo": "desktop",
        "v1": -1.2, "v14": -0.4,
    }

    def test_batch_sin_modelo_retorna_503(self):
        """Sin modelo cargado, /predict/batch debe retornar 503."""
        payload = {"transacciones": [self.TRANSACCION_VALIDA, self.TRANSACCION_VALIDA]}
        respuesta = cliente.post("/predict/batch", json=payload)
        assert respuesta.status_code == 503

    def test_batch_lista_vacia_retorna_422(self):
        """Lista vacía debe fallar la validación (mínimo 1 transacción)."""
        respuesta = cliente.post("/predict/batch", json={"transacciones": []})
        assert respuesta.status_code == 422

    def test_batch_transaccion_invalida_retorna_422(self):
        """Transacción con monto negativo dentro del lote debe fallar."""
        transaccion_mala = {**self.TRANSACCION_VALIDA, "monto_transaccion": -50.0}
        payload = {"transacciones": [self.TRANSACCION_VALIDA, transaccion_mala]}
        respuesta = cliente.post("/predict/batch", json=payload)
        assert respuesta.status_code == 422

    def test_batch_estructura_respuesta_sin_modelo(self):
        """La respuesta de error 503 debe incluir el campo 'detail'."""
        payload = {"transacciones": [self.TRANSACCION_VALIDA]}
        respuesta = cliente.post("/predict/batch", json=payload)
        assert respuesta.status_code == 503
        assert "detail" in respuesta.json()

    def test_batch_acepta_multiples_transacciones(self):
        """El endpoint debe aceptar un lote de varias transacciones."""
        lote = [self.TRANSACCION_VALIDA] * 5
        payload = {"transacciones": lote}
        respuesta = cliente.post("/predict/batch", json=payload)
        # Sin modelo retorna 503, con modelo retorna 200
        assert respuesta.status_code in [200, 503]


class TestAuditLogger:
    """Tests del módulo de logging de auditoría."""

    def test_registrar_prediccion_crea_archivo(self, tmp_path, monkeypatch):
        """Debe crear el archivo JSONL al registrar la primera predicción."""
        ruta_log = tmp_path / "test_predicciones.jsonl"
        monkeypatch.setattr(audit_logger, "RUTA_LOG", ruta_log)

        audit_logger.registrar_prediccion(
            endpoint="/predict",
            monto_transaccion=150.75,
            nivel_riesgo="BAJO",
            es_fraude=False,
            probabilidad_fraude=0.023,
            confianza_modelo=0.977,
            tiempo_inferencia_ms=2.5,
        )

        assert ruta_log.exists()

    def test_registro_contiene_campos_correctos(self, tmp_path, monkeypatch):
        """Cada línea del JSONL debe contener los campos de auditoría."""
        ruta_log = tmp_path / "test_predicciones.jsonl"
        monkeypatch.setattr(audit_logger, "RUTA_LOG", ruta_log)

        audit_logger.registrar_prediccion(
            endpoint="/predict",
            monto_transaccion=500.0,
            nivel_riesgo="ALTO",
            es_fraude=True,
            probabilidad_fraude=0.85,
            confianza_modelo=0.85,
            tiempo_inferencia_ms=3.1,
        )

        linea = json.loads(ruta_log.read_text(encoding="utf-8").strip())
        assert linea["endpoint"] == "/predict"
        assert linea["monto_transaccion"] == 500.0
        assert linea["es_fraude"] is True
        assert linea["nivel_riesgo"] == "ALTO"
        assert "timestamp" in linea

    def test_multiples_registros_en_una_linea_cada_uno(self, tmp_path, monkeypatch):
        """Cada predicción debe ser una línea independiente en el JSONL."""
        ruta_log = tmp_path / "test_predicciones.jsonl"
        monkeypatch.setattr(audit_logger, "RUTA_LOG", ruta_log)

        for _ in range(3):
            audit_logger.registrar_prediccion(
                endpoint="/predict",
                monto_transaccion=100.0,
                nivel_riesgo="BAJO",
                es_fraude=False,
                probabilidad_fraude=0.05,
                confianza_modelo=0.95,
                tiempo_inferencia_ms=1.0,
            )

        lineas = ruta_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(lineas) == 3
        for linea in lineas:
            json.loads(linea)  # Cada línea debe ser JSON válido

    def test_registro_batch_incluye_lote_size(self, tmp_path, monkeypatch):
        """Los registros batch deben incluir el campo 'lote_size'."""
        ruta_log = tmp_path / "test_predicciones.jsonl"
        monkeypatch.setattr(audit_logger, "RUTA_LOG", ruta_log)

        audit_logger.registrar_prediccion(
            endpoint="/predict/batch",
            monto_transaccion=300.0,
            nivel_riesgo="BAJO",
            es_fraude=False,
            probabilidad_fraude=0.1,
            confianza_modelo=0.9,
            tiempo_inferencia_ms=10.0,
            lote_size=50,
        )

        linea = json.loads(ruta_log.read_text(encoding="utf-8").strip())
        assert linea["lote_size"] == 50
        assert linea["endpoint"] == "/predict/batch"


class TestEndpointInfo:
    """Tests del endpoint GET /info."""

    def test_info_retorna_200(self):
        respuesta = cliente.get("/info")
        assert respuesta.status_code == 200

    def test_info_sin_modelo_indica_estado(self):
        respuesta = cliente.get("/info")
        datos = respuesta.json()
        assert "estado" in datos or "modelo" in datos
