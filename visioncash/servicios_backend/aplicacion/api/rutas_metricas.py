# -*- coding: utf-8 -*-
"""
Capa de Servicios de Aplicación (API REST) - Rutas de Métricas y Soporte
Endpoints para auditoría de escaneos, KPIs y mesa de ayuda técnica.
"""
from flask import Blueprint, jsonify, request

bp_metricas = Blueprint('metricas', __name__)

@bp_metricas.route('/api/metricas/ping', methods=['GET'])
def ping_metricas():
    return jsonify({"service": "VisionCash Metrics & Support API", "status": "active"})
