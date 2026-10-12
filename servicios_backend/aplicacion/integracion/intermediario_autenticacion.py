# -*- coding: utf-8 -*-
"""
Capa de Integración - Middleware & Intermediario de Autenticación
Gestiona cabeceras CORS, túneles ngrok y puente de comunicación entre servicios.
"""

def configurar_cors_y_ngrok(app):
    @app.after_request
    def after_request_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response
    return app
