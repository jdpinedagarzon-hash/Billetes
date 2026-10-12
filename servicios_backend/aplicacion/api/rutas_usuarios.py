# -*- coding: utf-8 -*-
"""
Capa de Servicios de Aplicación (API REST) - Rutas de Usuarios y Autenticación
Endpoints para registro, inicio de sesión y autenticación multifactor (2FA).
"""
from flask import Blueprint, jsonify, request

bp_usuarios = Blueprint('usuarios', __name__)

@bp_usuarios.route('/api/auth/ping', methods=['GET'])
def ping_auth():
    return jsonify({"service": "VisionCash Auth API", "status": "active"})
