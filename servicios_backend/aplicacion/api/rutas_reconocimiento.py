# -*- coding: utf-8 -*-
"""
Capa de Servicios de Aplicación (API REST) - Rutas de Reconocimiento
Endpoints para inferencia de IA, predicción individual, ráfagas y estado del modelo.
"""
from flask import Blueprint, jsonify, request

bp_reconocimiento = Blueprint('reconocimiento', __name__)

@bp_reconocimiento.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        "status": "online",
        "service": "VisionCash Recognition API",
        "version": "2.0"
    })
