# -*- coding: utf-8 -*-
"""
Capa de Servicios de Backend - Modelos de Base de Datos
Representación orientada a objetos de las entidades de persistencia.
"""

class Usuario:
    def __init__(self, id_usuario=None, nombre_completo="", nombre_usuario="", email="", password_hash="", dos_factores_activo=False, secreto_2fa=None):
        self.id_usuario = id_usuario
        self.nombre_completo = nombre_completo
        self.nombre_usuario = nombre_usuario
        self.email = email
        self.password_hash = password_hash
        self.dos_factores_activo = dos_factores_activo
        self.secreto_2fa = secreto_2fa

class TicketSoporte:
    def __init__(self, id_ticket=None, codigo="", usuario="", tipo_caso="", asunto="", descripcion="", prioridad="media", estado="abierto"):
        self.id_ticket = id_ticket
        self.codigo = codigo
        self.usuario = usuario
        self.tipo_caso = tipo_caso
        self.asunto = asunto
        self.descripcion = descripcion
        self.prioridad = prioridad
        self.estado = estado

class RegistroHistorial:
    def __init__(self, id_escaneo=None, usuario="", denominacion="", confianza=0.0, metodo="camara_tiempo_real", latencia_ms=0):
        self.id_escaneo = id_escaneo
        self.usuario = usuario
        self.denominacion = denominacion
        self.confianza = confianza
        self.metodo = metodo
        self.latencia_ms = latencia_ms
