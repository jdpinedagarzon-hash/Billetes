# -*- coding: utf-8 -*-
"""
generar_documento_apis.py - Generador del Documento Oficial en Word (.docx)
para VisionCash: Catálogo Completo de APIs, Microservicios y Funcionamiento Interno.
"""
import os
import sys
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    """Aplica color de fondo hexadecimal a una celda de tabla."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Establece márgenes internos de celda en dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_api_card(doc, num, method, endpoint, port, purpose, internal_logic, headers, payload, response_ok, errors, consumer):
    """Crea una ficha técnica detallada y estilizada para una API en el documento Word."""
    
    # Encabezado de la API
    h = doc.add_heading(level=3)
    run_num = h.add_run(f"API {num}: ")
    run_num.font.color.rgb = RGBColor(109, 59, 245) # Púrpura
    run_num.font.size = Pt(13)
    run_num.bold = True
    
    # Badge método HTTP
    method_color = RGBColor(47, 123, 255) # Azul por defecto
    if method == "POST":
        method_color = RGBColor(16, 185, 129) # Verde
    elif method == "DELETE":
        method_color = RGBColor(239, 68, 68) # Rojo
    elif method in ["ALL", "PROXY"]:
        method_color = RGBColor(245, 158, 11) # Ámbar
        
    run_method = h.add_run(f"[{method}] ")
    run_method.font.color.rgb = method_color
    run_method.font.size = Pt(13)
    run_method.bold = True
    
    run_ep = h.add_run(endpoint)
    run_ep.font.color.rgb = RGBColor(10, 22, 51) # Navy
    run_ep.font.size = Pt(13)
    run_ep.bold = True

    # Tabla de especificación técnica
    table = doc.add_table(rows=7, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    # Anchos de columna
    widths = [Inches(1.8), Inches(4.7)]
    for row in table.rows:
        for idx, width in enumerate(widths):
            row.cells[idx].width = width

    fields = [
        ("Servicio y Puerto:", f"{port}"),
        ("¿Para qué sirve?:", purpose),
        ("¿Cómo funciona por dentro?:", internal_logic),
        ("Cabeceras (Headers):", headers),
        ("Payload / Parámetros:", payload),
        ("Respuesta Exitosa (200 OK):", response_ok),
        ("Respuestas de Error & Consumidor:", f"• Errores: {errors}\n• Consumidor: {consumer}")
    ]

    for i, (label, val) in enumerate(fields):
        c0, c1 = table.rows[i].cells
        set_cell_background(c0, "0A1633") # Azul marino oscuro
        set_cell_background(c1, "F8FAFC" if i % 2 == 0 else "EDF2F7") # Fondo suave alterno
        set_cell_margins(c0, top=120, bottom=120, left=140, right=140)
        set_cell_margins(c1, top=120, bottom=120, left=140, right=140)
        
        # Etiqueta
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r0 = p0.add_run(label)
        r0.font.bold = True
        r0.font.color.rgb = RGBColor(255, 255, 255)
        r0.font.size = Pt(9.5)
        
        # Valor
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r1 = p1.add_run(val)
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = RGBColor(30, 41, 59)
        if "Respuesta" in label or "Payload" in label:
            r1.font.name = "Consolas"
            r1.font.size = Pt(8.5)

    doc.add_paragraph() # Espaciador

def build_full_documentation(output_path):
    doc = docx.Document()
    
    # Márgenes de página (2 cm)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # ══════════════════════════════════════════════════════════════════════════
    # PORTADA / ENCABEZADO
    # ══════════════════════════════════════════════════════════════════════════
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sup = p_title.add_run("SISTEMA DE INTELIGENCIA ARTIFICIAL & MICROSERVICIOS\n")
    r_sup.font.size = Pt(11)
    r_sup.font.bold = True
    r_sup.font.color.rgb = RGBColor(109, 59, 245)

    r_title = p_title.add_run("VisionCash · Catálogo Oficial de APIs y Arquitectura Técnica\n")
    r_title.font.size = Pt(22)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(10, 22, 51)

    r_sub = p_title.add_run("Especificación Completa de los 19 Endpoints, Microservicios, Motor PyTorch y Base de Datos MySQL")
    r_sub.font.size = Pt(12)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(85, 96, 138)
    
    # Cuadro de metadata
    tbl_meta = doc.add_table(rows=4, cols=2)
    tbl_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_info = [
        ("Proyecto:", "VisionCash / BilletIA - Reconocimiento de Billetes Colombianos con Voz Inclusiva"),
        ("Arquitectura:", "Distribuida en Microservicios (Servidor IA: Puerto 5000 | Historial y Métricas: Puerto 5001)"),
        ("Tecnologías Core:", "PyTorch (EfficientNetV2-S / CUDA 12.8), Flask, Android (CameraX + TTS), MySQL XAMPP"),
        ("Estado y Despliegue:", "Versión 2.0 Modular Estable - Soporta Web Local, GitHub Pages y App Móvil Android")
    ]
    for idx, (lbl, val) in enumerate(meta_info):
        c0, c1 = tbl_meta.rows[idx].cells
        c0.width, c1.width = Inches(2.0), Inches(4.5)
        set_cell_background(c0, "10214A")
        set_cell_background(c1, "EEF2F6")
        set_cell_margins(c0, 80, 80, 100, 100)
        set_cell_margins(c1, 80, 80, 100, 100)
        p0, p1 = c0.paragraphs[0], c1.paragraphs[0]
        r0 = p0.add_run(lbl)
        r0.font.bold = True
        r0.font.size = Pt(9)
        r0.font.color.rgb = RGBColor(255, 255, 255)
        r1 = p1.add_run(val)
        r1.font.size = Pt(9)
        r1.font.color.rgb = RGBColor(30, 42, 82)
    
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: INTRODUCCIÓN Y ARQUITECTURA
    # ══════════════════════════════════════════════════════════════════════════
    h1 = doc.add_heading("1. Arquitectura General y Distribución de Componentes", level=1)
    h1.runs[0].font.color.rgb = RGBColor(10, 22, 51)

    doc.add_paragraph(
        "VisionCash es una solución tecnológica integral diseñada para el reconocimiento en tiempo real "
        "de billetes de la Nueva Familia del Banco de la República de Colombia ($2.000, $5.000, $10.000, "
        "$20.000, $50.000 y $100.000 COP). El sistema está pensado especialmente para personas con discapacidad "
        "visual o baja visión, integrando reconocimiento con Inteligencia Artificial, síntesis de voz continua y "
        "gestión financiera accesible."
    )
    doc.add_paragraph(
        "Para garantizar alto rendimiento, escalabilidad y resiliencia, la arquitectura no es un monolito rígido, "
        "sino que se encuentra dividida en capas modulares y microservicios especializados:"
    )

    p_comp = doc.add_paragraph()
    p_comp.add_run("1. Cliente Móvil Android (BilletesApp):\n").bold = True
    p_comp.add_run("   Aplicación nativa construida con Jetpack Compose y CameraX. Incorpora detección háptica por vibración, estabilización de 1.4s, modo ráfaga, lectura por voz (TTS) con el total acumulado y control mediante gestos (doble toque para reanudar, un toque para repetir cuenta, toque largo para reiniciar a cero).\n")
    p_comp.add_run("2. Cliente Web (Portal VisionCash):\n").bold = True
    p_comp.add_run("   Interfaz moderna accesible desde localhost o alojada en GitHub Pages. Permite escaneo mediante webcam WebRTC, panel de inicio de sesión con segundo factor de autenticación (2FA), registro, y mesa de ayuda (Soporte.html).\n")
    p_comp.add_run("3. Servidor Principal de IA (Puerto 5000):\n").bold = True
    p_comp.add_run("   Núcleo computacional acelerado por GPU (NVIDIA RTX 5060 Ti con CUDA 12.8). Ejecuta la red neuronal convolucional EfficientNetV2-S con TTA (Test-Time Augmentation de 8 pasadas), auto-recorte y alineación geométrica de billetes, autenticación y túnel ngrok.\n")
    p_comp.add_run("4. Microservicio de Historial & Métricas (Puerto 5001):\n").bold = True
    p_comp.add_run("   Servicio desacoplado que maneja la base de datos MySQL (XAMPP). Registra las auditorías de escaneo, gestiona tickets de soporte y calcula los KPIs analíticos en tiempo real (monto total escaneado hoy vs. acumulado histórico).\n")

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: EL MICROSERVICIO INDEPENDIENTE (PUERTO 5001)
    # ══════════════════════════════════════════════════════════════════════════
    h2 = doc.add_heading("2. ¿Qué es el Microservicio, Para Qué Sirve y Cómo Funciona?", level=1)
    h2.runs[0].font.color.rgb = RGBColor(10, 22, 51)

    doc.add_paragraph(
        "En la arquitectura de software, un microservicio es un componente independiente y autónomo que se encarga "
        "de un dominio de negocio acotado y se comunica con el resto del sistema a través de APIs REST ligeras. "
        "En VisionCash, el archivo 'componentes_transversales/monitoreo/microservicio_historial.py' opera en el "
        "puerto 5001 de manera totalmente aislada del motor de IA en el puerto 5000."
    )
    
    p_why = doc.add_paragraph()
    p_why.add_run("¿Por qué es indispensable esta separación? (Ventajas Técnicas):\n").bold = True
    p_why.add_run("• Aislamiento GPU vs. Base de Datos: La inferencia en tiempo real en la GPU RTX 5060 Ti requiere tiempos de respuesta inferiores a 50 milisegundos. Si las consultas pesadas a MySQL (agrupaciones, cálculos de totales y reportes) se ejecutaran en el mismo proceso, saturarían los hilos de Flask y causarían pausas o tirones en el video de la cámara.\n")
    p_why.add_run("• Alta Disponibilidad y Resiliencia (Tolerancia a Fallos): Si la base de datos de XAMPP se apaga o el microservicio falla por mantenimiento, el reconocimiento de billetes en tiempo real SIGUE OPERANDO al 100% en el servidor de IA sin interrumpir al usuario invidente.\n")
    p_why.add_run("• Mecanismo de Auto-Recuperación (Self-Healing): El Servidor Principal supervisa la salud del puerto 5001. Si al intentar guardar un escaneo detecta que el microservicio está apagado, la función 'asegurar_microservicio_historial()' lanza automáticamente el subproceso en segundo plano sin intervención humana.\n")
    p_why.add_run("• Escalabilidad Horizontal: Permite que en un entorno empresarial el microservicio de analítica se traslade a un servidor independiente de base de datos sin alterar el código de la inteligencia artificial.")

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: CATÁLOGO EXHAUSTIVO DE LAS 19 APIS
    # ══════════════════════════════════════════════════════════════════════════
    h3 = doc.add_heading("3. Catálogo Técnico Detallado de Cada API (19 Endpoints)", level=1)
    h3.runs[0].font.color.rgb = RGBColor(10, 22, 51)

    doc.add_paragraph(
        "A continuación se presenta la ficha técnica exhaustiva de cada una de las 19 APIs que conforman "
        "el ecosistema de VisionCash, detallando su método, propósito, funcionamiento interno paso a paso, "
        "cargas útiles (payloads), respuestas exitosas y códigos de error."
    )

    # ──────────────────────────────────────────────────────────────────────────
    # GRUPO 1: IA Y RECONOCIMIENTO (PUERTO 5000)
    # ──────────────────────────────────────────────────────────────────────────
    doc.add_heading("3.1. Módulo de Inteligencia Artificial y Diagnóstico (Puerto 5000)", level=2)

    create_api_card(
        doc,
        num="01",
        method="GET",
        endpoint="/api/status",
        port="Servidor Principal de IA (Puerto 5000 / ngrok)",
        purpose="Comprobar la salud operativa del servidor, verificar si el modelo de red neuronal está cargado en memoria, auditar el hardware de aceleración activo y consultar las denominaciones registradas.",
        internal_logic="1. Inspecciona la variable global MODEL para determinar si la red PyTorch EfficientNetV2-S está inicializada en GPU o CPU.\n2. Lee la variable HARDWARE_INFO ('GPU CUDA RTX 5060 Ti').\n3. Carga y serializa la lista de clases desde 'classes.json'.\n4. Verifica que el TTA (Test-Time Augmentation) esté habilitado.\n5. Retorna el payload JSON con estado HTTP 200.",
        headers="Accept: application/json\nngrok-skip-browser-warning: true",
        payload="Ninguno (Parámetros vacíos).",
        response_ok='''{
  "success": true,
  "model_loaded": true,
  "hardware": "GPU CUDA RTX 5060 Ti",
  "classes_count": 6,
  "classes": ["10.000", "100.000", "2.000", "20.000", "5.000", "50000"],
  "tta": true,
  "framework": "PyTorch EfficientNetV2-S"
}''',
        errors="500 Internal Server Error (si falla la inicialización del modelo o el hardware CUDA).",
        consumer="config.js (auto-detección de conexión), Menú Principal Web, Monitor de Sistema."
    )

    create_api_card(
        doc,
        num="02",
        method="POST",
        endpoint="/api/predict  (Alias: /predict)",
        port="Servidor Principal de IA (Puerto 5000 / ngrok)",
        purpose="Realizar la inferencia y reconocimiento profundo de una imagen individual de billete colombiano capturada por la cámara del celular o webcam.",
        internal_logic="1. Recepción y decodificación: Lee la imagen desde multipart 'file' o JSON Base64 'image'.\n2. Auto-recorte inteligente: Convierte a escala de grises, aplica umbralización adaptativa OTSU, detecta el contorno poligonal de 4 esquinas del billete y elimina el fondo.\n3. Alineación canónica horizontal: Detecta la orientación rectangular del billete y rota si es necesario para colocar la esquina del valor en la posición aprendida por la red.\n4. Inferencia con TTA (8 Pasadas): Genera 8 variantes con rotaciones leves, espejado y ajuste de contraste. Infiere en la GPU RTX 5060 Ti mediante 'MODEL(batch)' y promedia las probabilidades Softmax.\n5. Calibración cromática: Aplica un filtro de color HSV comparando contra los centroides oficiales del Banco de la República.\n6. Recorte de miniatura: Extrae la esquina superior izquierda como comprobante en base64.\n7. Registro asíncrono: Lanza un hilo en segundo plano que reporta el escaneo al microservicio en el puerto 5001.\n8. Retorna denominación, personaje, color, confianza y tiempos.",
        headers="Content-Type: multipart/form-data  O  application/json\nngrok-skip-browser-warning: true",
        payload='''Multipart: 'file' (Archivo binario JPEG/PNG)\n-- O bien --\nJSON: {"image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...", "usuario": "admin"}''',
        response_ok='''{
  "success": true,
  "class": 2,
  "denomination": "$2.000 COP",
  "raw_name": "2.000",
  "character": "Débora Arango",
  "color": "#3b82f6",
  "confidence": 0.9642,
  "confidence_display": "96.4%",
  "latency_ms": 38.5,
  "hardware": "GPU CUDA RTX 5060 Ti",
  "all_probabilities": {
    "$2.000 COP": 0.9642,
    "$5.000 COP": 0.0152,
    "$10.000 COP": 0.0084,
    "$20.000 COP": 0.0051,
    "$50.000 COP": 0.0042,
    "$100.000 COP": 0.0029
  },
  "corner_preview": "data:image/jpeg;base64,/9j/4AAQ..."
}''',
        errors="400 Bad Request (si no se envió imagen o el formato es inválido)\n503 Service Unavailable (si el modelo aún no se ha cargado en la GPU).",
        consumer="Menu_principal.html (Webcam), BilletesApp Android (Escaneo individual)."
    )

    create_api_card(
        doc,
        num="03",
        method="POST",
        endpoint="/api/predict-burst",
        port="Servidor Principal de IA (Puerto 5000 / ngrok)",
        purpose="Modo de alta precisión para personas con discapacidad visual: evalúa una ráfaga de 3 a 5 fotogramas consecutivos tomados en fracciones de segundo y aplica un algoritmo de votación por consenso para eliminar falsos positivos.",
        internal_logic="1. Extrae los múltiples cuadros enviados (ej. 'file_0', 'file_1', 'file_2').\n2. Para cada cuadro ejecuta el pipeline de preprocesamiento, alineación horizontal y Softmax.\n3. Aplica decaimiento temporal y votación ponderada: pondera cada voto según la confianza individual y descarta cuadros borrosos con baja nitidez.\n4. Evalúa consenso estricto: requiere que al menos el 66% de los cuadros válidos concuerden en la misma denominación.\n5. Si no hay consenso, devuelve 'indeciso' indicando al usuario que mantenga el billete quieto.\n6. Si hay consenso, despacha el veredicto consolidado y lo registra en el microservicio.",
        headers="Content-Type: multipart/form-data\nngrok-skip-browser-warning: true",
        payload="Archivos multipart: 'file_0', 'file_1', 'file_2' (JPEGs tomados con diferencia de 100ms) + campo de texto 'usuario'.",
        response_ok='''{
  "success": true,
  "denomination": "$50.000 COP",
  "character": "Gabriel García Márquez",
  "confidence": 0.9785,
  "consensus_agreement": "3/3 cuadros coincidentes",
  "frames_evaluated": 3,
  "latency_total_ms": 74.2,
  "verdict": "CONFIRMED"
}''',
        errors="400 Bad Request (si se reciben menos de 2 cuadros)\n422 Unprocessable Entity (si los cuadros no tienen coincidencia por movimiento excesivo).",
        consumer="BilletesApp Android (Modo de escaneo automático por estabilización)."
    )

    # ──────────────────────────────────────────────────────────────────────────
    # GRUPO 2: AUTENTICACIÓN Y SEGURIDAD 2FA (PUERTO 5000)
    # ──────────────────────────────────────────────────────────────────────────
    doc.add_heading("3.2. Módulo de Autenticación, Usuarios y Seguridad 2FA (Puerto 5000)", level=2)

    create_api_card(
        doc,
        num="04",
        method="POST",
        endpoint="/api/auth/registro",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Registrar una nueva cuenta de usuario en la base de datos MySQL (XAMPP), almacenar la contraseña de manera segura y generar el secreto de autenticación de dos factores (TOTP).",
        internal_logic="1. Valida campos obligatorios: nombre de usuario, correo electrónico, contraseña y teléfono.\n2. Verifica en la tabla 'usuarios' que el nombre de usuario y correo no se encuentren previamente registrados.\n3. Hashea la contraseña utilizando algoritmos seguros de derivación de claves criptográficas.\n4. Genera una clave secreta TOTP aleatoria en Base32 (16 caracteres) para el 2FA.\n5. Inserta el nuevo registro en MySQL y retorna confirmación con la clave secreta.",
        headers="Content-Type: application/json",
        payload='''{
  "username": "juan_pineda",
  "email": "juan@visioncash.com",
  "password": "Password123*",
  "telefono": "+57 300 1234567"
}''',
        response_ok='''{
  "success": true,
  "message": "Usuario registrado exitosamente",
  "usuario_id": 15,
  "totp_secret": "JBSWY3DPEHPK3PXP",
  "qr_url": "/api/auth/obtener-2fa-qr?usuario=juan_pineda"
}''',
        errors="400 Bad Request (campos incompletos o formato de correo inválido)\n409 Conflict (el nombre de usuario o correo ya existen en el sistema).",
        consumer="Menu_principal_3.html (Página de Registro de Usuarios)."
    )

    create_api_card(
        doc,
        num="05",
        method="GET",
        endpoint="/api/auth/obtener-2fa-qr",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Generar el código QR en formato gráfico Base64 para que el usuario pueda escanearlo con Google Authenticator, Microsoft Authenticator o Authy desde su teléfono móvil.",
        internal_logic="1. Recibe el parámetro 'usuario' en la URL.\n2. Consulta la base de datos MySQL para obtener el 'secreto_2fa' asignado al usuario.\n3. Construye el URI estándar: 'otpauth://totp/VisionCash:usuario?secret=...&issuer=VisionCash'.\n4. Utiliza la librería 'qrcode' para generar la matriz de imagen PNG en memoria.\n5. Codifica la imagen binaria en Base64 ('data:image/png;base64,...') y la retorna en JSON.",
        headers="Accept: application/json",
        payload="Query Param: ?usuario=juan_pineda",
        response_ok='''{
  "success": true,
  "usuario": "juan_pineda",
  "secreto_2fa": "JBSWY3DPEHPK3PXP",
  "qr_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "instrucciones": "Escanea este código QR con Google Authenticator o Authy."
}''',
        errors="404 Not Found (si el usuario no existe en la base de datos)\n500 Internal Server Error (si falla la generación del código QR).",
        consumer="verificar_2fa.html, Menu_principal_3.html (Configuración inicial de 2FA)."
    )

    create_api_card(
        doc,
        num="06",
        method="POST",
        endpoint="/api/auth/login",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Iniciar sesión de forma segura validando usuario, contraseña y el código numérico de doble factor (2FA) en un único paso atómico.",
        internal_logic="1. Valida que el payload contenga 'username', 'password' y 'codigo_2fa' (de 6 dígitos numéricos).\n2. Consulta la base de datos MySQL para verificar la existencia del usuario y compara el hash de la contraseña.\n3. Recupera el 'secreto_2fa' del usuario y utiliza el algoritmo TOTP (RFC 6238) con ventana de tiempo de ±30 segundos para validar los 6 dígitos.\n4. Si ambas comprobaciones son correctas, crea una sesión activa en la base de datos, actualiza la fecha de último acceso y retorna los datos del perfil y token de sesión.",
        headers="Content-Type: application/json",
        payload='''{
  "username": "juan_pineda",
  "password": "Password123*",
  "codigo_2fa": "482910"
}''',
        response_ok='''{
  "success": true,
  "message": "Autenticación satisfactoria",
  "usuario": {
    "id": 15,
    "nombre_usuario": "juan_pineda",
    "email": "juan@visioncash.com",
    "rol": "usuario_estandar"
  },
  "token_sesion": "vc_sess_9a8f7b6c5d4e3f2a1",
  "expira_en_horas": 8
}''',
        errors="400 Bad Request (código 2FA no contiene 6 dígitos)\n401 Unauthorized (credenciales incorrectas o código 2FA expirado/inválido)\n404 Not Found (usuario inexistente).",
        consumer="Menu_principal_2.html (Formulario de Inicio de Sesión)."
    )

    create_api_card(
        doc,
        num="07",
        method="POST",
        endpoint="/api/auth/verificar-2fa",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Validar de manera independiente un código 2FA temporal para operaciones críticas (como cambio de contraseña o confirmación de identidad).",
        internal_logic="1. Extrae 'username' y 'codigo_2fa'.\n2. Obtiene el secreto almacenado en MySQL para ese usuario.\n3. Ejecuta la validación matemática TOTP basada en el tiempo unix actual / 30.\n4. Devuelve booleano 'valido: true/false'.",
        headers="Content-Type: application/json",
        payload='''{"username": "juan_pineda", "codigo_2fa": "482910"}''',
        response_ok='''{"success": true, "valido": true, "message": "Código 2FA verificado correctamente"}''',
        errors="401 Unauthorized (código 2FA incorrecto o desincronizado)\n404 Not Found (usuario no encontrado).",
        consumer="verificar_2fa.html, módulo de recuperación y seguridad."
    )

    # ──────────────────────────────────────────────────────────────────────────
    # GRUPO 3: MESA DE AYUDA Y KPIS (PUERTO 5000)
    # ──────────────────────────────────────────────────────────────────────────
    doc.add_heading("3.3. Módulo de Mesa de Ayuda, Soporte Técnico y KPIs (Puerto 5000)", level=2)

    create_api_card(
        doc,
        num="08",
        method="POST",
        endpoint="/api/soporte/tickets",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Permitir a los usuarios y clientes radicar solicitudes de asistencia técnica, reportar fallas en el escaneo o enviar peticiones y reclamos (PQRS).",
        internal_logic="1. Valida los campos: 'usuario', 'tipo' (Falla Técnica, Duda, Reclamo, Sugerencia), 'asunto' y 'mensaje'.\n2. Genera un código de ticket único alfanumérico secuencial con prefijo (ej. 'TK-8492').\n3. Inserta el ticket en la tabla 'tickets_soporte' con estado inicial 'Pendiente', fecha y hora del sistema.\n4. Retorna el número de radicado generado para que el usuario pueda hacerle seguimiento.",
        headers="Content-Type: application/json",
        payload='''{
  "usuario": "juan_pineda",
  "tipo": "Falla Técnica",
  "asunto": "Dificultad con billete de 20.000 arrugado",
  "mensaje": "La cámara no enfoca bien el billete de 20 mil cuando tiene un pliegue en el centro.",
  "prioridad": "Media"
}''',
        response_ok='''{
  "success": true,
  "message": "Ticket creado exitosamente",
  "ticket": {
    "codigo": "TK-8492",
    "asunto": "Dificultad con billete de 20.000 arrugado",
    "estado": "Pendiente",
    "fecha_creacion": "2026-10-16 19:30:00"
  }
}''',
        errors="400 Bad Request (campos vacíos o tipo de ticket no válido)\n500 Internal Server Error (error en la base de datos MySQL).",
        consumer="Soporte.html (Formulario de Radicación de Tickets PQRS)."
    )

    create_api_card(
        doc,
        num="09",
        method="GET",
        endpoint="/api/soporte/tickets",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Consultar el listado de tickets radicados en la mesa de ayuda, con soporte de filtrado por usuario, estado o código de radicado.",
        internal_logic="1. Lee parámetros opcionales de consulta (?usuario=...&estado=...).\n2. Ejecuta una consulta SELECT sobre la tabla 'tickets_soporte' con orden descendente por fecha.\n3. Formatea las fechas, calcula el tiempo transcurrido desde la radicación y estructura la lista JSON.",
        headers="Accept: application/json",
        payload="Query Params opcionales: ?usuario=juan_pineda&estado=Pendiente",
        response_ok='''{
  "success": true,
  "total": 1,
  "tickets": [
    {
      "codigo": "TK-8492",
      "usuario": "juan_pineda",
      "tipo": "Falla Técnica",
      "asunto": "Dificultad con billete de 20.000 arrugado",
      "estado": "Pendiente",
      "respuesta_tecnica": null,
      "calificacion": null,
      "fecha": "2026-10-16 19:30:00"
    }
  ]
}''',
        errors="500 Internal Server Error (si falla la conexión a MySQL).",
        consumer="Soporte.html (Bandeja de seguimiento de solicitudes y panel de soporte)."
    )

    create_api_card(
        doc,
        num="10",
        method="GET",
        endpoint="/api/soporte/kpis",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Calcular en tiempo real los indicadores clave de rendimiento (KPIs) gerenciales de la mesa de soporte técnico y satisfacción de clientes.",
        internal_logic="1. Consulta la tabla 'tickets_soporte' agrupando por estado (Pendiente, En Proceso, Resuelto).\n2. Calcula el porcentaje de resolución: (Resueltos / Total) * 100.\n3. Calcula el promedio de estrellas de satisfacción sobre los tickets que fueron calificados por los usuarios (1 a 5 estrellas).\n4. Retorna el resumen consolidado en formato de tarjetas KPI para el dashboard.",
        headers="Accept: application/json",
        payload="Ninguno.",
        response_ok='''{
  "success": true,
  "kpis": {
    "total_tickets": 28,
    "resueltos": 24,
    "pendientes": 3,
    "en_proceso": 1,
    "tasa_resolucion_pct": 85.7,
    "promedio_satisfaccion": 4.8,
    "tiempo_promedio_respuesta_horas": 1.4
  }
}''',
        errors="500 Internal Server Error.",
        consumer="Soporte.html (Tarjetas de métricas superiores del panel de control)."
    )

    create_api_card(
        doc,
        num="11",
        method="POST",
        endpoint="/api/soporte/tickets/<codigo>/calificar",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Registrar la calificación de servicio de 1 a 5 estrellas y comentarios otorgados por el usuario tras la atención de su ticket.",
        internal_logic="1. Extrae el código del ticket de la URL ('<codigo>').\n2. Valida que el parámetro 'estrellas' sea un número entero entre 1 y 5.\n3. Actualiza el campo 'calificacion' y 'comentario_satisfaccion' en MySQL.\n4. Recalcula automáticamente el KPI de satisfacción global del sistema.",
        headers="Content-Type: application/json",
        payload='''{"estrellas": 5, "comentario": "Excelente respuesta, me explicaron cómo enfocar mejor."}''',
        response_ok='''{"success": true, "message": "Calificación registrada con éxito. ¡Gracias por tu opinión!"}''',
        errors="400 Bad Request (estrellas fuera de rango 1-5)\n404 Not Found (código de ticket no encontrado en la base de datos).",
        consumer="Soporte.html (Modal de calificación de tickets resueltos)."
    )

    # ──────────────────────────────────────────────────────────────────────────
    # GRUPO 4: RED, TÚNEL NGROK Y PROXY (PUERTO 5000)
    # ──────────────────────────────────────────────────────────────────────────
    doc.add_heading("3.4. Módulo de Red, Túnel ngrok y Proxy Transparente (Puerto 5000)", level=2)

    create_api_card(
        doc,
        num="12",
        method="GET",
        endpoint="/api/ngrok_url",
        port="Servidor Principal (Puerto 5000 / ngrok)",
        purpose="Consultar en tiempo real la URL pública HTTPS generada por el túnel activo de ngrok para permitir la conexión automática de la app móvil y frontend web.",
        internal_logic="1. Consulta la API local de ngrok en 'http://127.0.0.1:4040/api/tunnels'.\n2. Filtra el túnel con protocolo 'https'.\n3. Si ngrok está activo, devuelve la URL pública actual.\n4. Si no está activo, lee el fallback de 'componentes_transversales/configuracion/ngrok_url.txt'.",
        headers="Accept: application/json",
        payload="Ninguno.",
        response_ok='''{"success": true, "ngrok_url": "https://b38d-181-53-12-63.ngrok-free.app"}''',
        errors="503 Service Unavailable (si ngrok no está corriendo localmente).",
        consumer="config.js, sincronizadores de GitHub y BilletesApp Android."
    )

    create_api_card(
        doc,
        num="13",
        method="ALL",
        endpoint="/api/historial  y  /api/historial/<subpath>",
        port="Servidor Principal (Puerto 5000) -> Proxy hacia Puerto 5001",
        purpose="Actuar como API Gateway / Proxy transparente. Permite que el cliente web y móvil solo tengan que conectarse al Puerto 5000 (o por ngrok), redirigiendo automáticamente las solicitudes de analítica hacia el microservicio en el Puerto 5001.",
        internal_logic="1. Intercepta cualquier método HTTP (GET, POST, DELETE, OPTIONS) dirigido a '/api/historial...'.\n2. Comprueba mediante un socket TCP si el puerto 5001 está respondiendo.\n3. Si el microservicio está apagado, invoca 'asegurar_microservicio_historial()', lo inicia como subproceso en segundo plano y espera 2 segundos.\n4. Reenvía la petición completa (con headers, query params y body JSON) a 'http://127.0.0.1:5001/api/historial/...'.\n5. Retorna la respuesta del microservicio al cliente sin alterar el formato ni las cabeceras CORS.",
        headers="Mismos que la petición original (soporta Content-Type, Authorization, etc.)",
        payload="Depende del subpath y método (reenvía exactamente la carga útil recibida).",
        response_ok="Devuelve exactamente la respuesta emitida por el microservicio en el puerto 5001.",
        errors="502 Bad Gateway (si el microservicio en el puerto 5001 no responde ni se pudo iniciar automáticamente).",
        consumer="Todos los clientes web y móviles cuando se conectan a través del túnel o servidor principal."
    )

    # ──────────────────────────────────────────────────────────────────────────
    # GRUPO 5: MICROSERVICIO DE HISTORIAL Y MÉTRICAS (PUERTO 5001)
    # ──────────────────────────────────────────────────────────────────────────
    doc.add_heading("3.5. Microservicio Independiente de Historial y Métricas (Puerto 5001)", level=2)

    create_api_card(
        doc,
        num="14",
        method="GET",
        endpoint="/api/historial/salud",
        port="Microservicio Independiente (Puerto 5001)",
        purpose="Health-check y monitoreo de disponibilidad del microservicio, reportando tiempo en línea (uptime) y conectividad directa con MySQL en XAMPP.",
        internal_logic="1. Ejecuta 'SELECT 1' en la conexión MySQL (192.168.0.12:3306).\n2. Calcula el tiempo de actividad desde que se inició el proceso en segundos.\n3. Inspecciona el estado de la memoria y devuelve estado HTTP 200.",
        headers="Accept: application/json",
        payload="Ninguno.",
        response_ok='''{
  "success": true,
  "servicio": "Microservicio de Historial y Métricas",
  "puerto": 5001,
  "estado": "ACTIVO_Y_SALUDABLE",
  "base_de_datos": "CONECTADO_A_MYSQL",
  "uptime_segundos": 3600
}''',
        errors="500 Internal Server Error (si se pierde la conexión física con el servidor MySQL de XAMPP).",
        consumer="Supervisor del Servidor Principal, herramientas de monitoreo DevOps."
    )

    create_api_card(
        doc,
        num="15",
        method="GET",
        endpoint="/api/historial/metricas  (Alias: /api/historial/resumen)",
        port="Microservicio Independiente (Puerto 5001)",
        purpose="Calcular y entregar en tiempo real las estadísticas financieras solicitadas: total de dinero escaneado hoy vs. acumulado histórico, cantidad de billetes, promedio de confianza y desglose por denominación.",
        internal_logic="1. Lee parámetros opcionales '?usuario_id=...' o '?usuario=...' para filtrar métricas individuales o globales.\n2. Ejecuta consulta SQL 1: 'COUNT(*)', 'SUM(valor_nominal)' y 'AVG(confianza)' filtrando 'WHERE DATE(fecha_hora) = CURDATE()'.\n3. Ejecuta consulta SQL 2: Mismos agregados sin restricción de fecha para obtener el acumulado histórico total.\n4. Ejecuta consulta SQL 3: Agrupación 'GROUP BY denominacion_texto' para obtener el conteo de cada billete escaneado en el día.\n5. Ejecuta consulta SQL 4: Desglose por método ('webcam', 'camara_movil', 'rafaga_burst').\n6. Retorna el payload JSON con montos en pesos colombianos formateados.",
        headers="Accept: application/json",
        payload="Query Params opcionales: ?usuario=juan_pineda  O  ?usuario_id=15",
        response_ok='''{
  "success": true,
  "usuario_consultado": "juan_pineda",
  "metricas_dia_actual": {
    "fecha": "2026-10-16",
    "cantidad_billetes": 8,
    "monto_total_cop": 210000,
    "monto_formateado": "$210.000 COP",
    "confianza_promedio_pct": 95.8
  },
  "metricas_historicas_acumuladas": {
    "cantidad_billetes": 54,
    "monto_total_cop": 1450000,
    "monto_formateado": "$1.450.000 COP",
    "confianza_promedio_pct": 96.2
  },
  "desglose_por_denominacion_hoy": [
    {"denominacion": "$50.000 COP", "cantidad": 3, "subtotal": 150000},
    {"denominacion": "$20.000 COP", "cantidad": 2, "subtotal": 40000},
    {"denominacion": "$10.000 COP", "cantidad": 2, "subtotal": 20000}
  ],
  "desglose_metodos": {
    "rafaga_burst": 6,
    "webcam": 2
  }
}''',
        errors="500 Internal Server Error (si falla la ejecución de las consultas de agregación en MySQL).",
        consumer="Menu_principal.html (Panel de Totales y Billetera Virtual), BilletesApp (Anuncio por Voz del Total), Soporte.html."
    )

    create_api_card(
        doc,
        num="16",
        method="GET",
        endpoint="/api/historial",
        port="Microservicio Independiente (Puerto 5001)",
        purpose="Consultar el listado paginado y detallado de cada escaneo registrado en el sistema, con filtros por fecha, usuario y denominación.",
        internal_logic="1. Parsea parámetros de paginación y filtros: 'pagina' (default 1), 'limite' (default 20), 'usuario', 'fecha_desde', 'fecha_hasta'.\n2. Ejecuta consulta SELECT con JOIN entre 'historial_escaneos' y 'usuarios'.\n3. Estructura cada elemento con id, fecha y hora formateada, valor nominal en número, denominación en texto, personaje histórico, confianza y latencia en ms.\n4. Retorna el array ordenado descendentemente por fecha.",
        headers="Accept: application/json",
        payload="Query Params: ?pagina=1&limite=10&usuario=juan_pineda",
        response_ok='''{
  "success": true,
  "total_registros": 54,
  "pagina_actual": 1,
  "registros": [
    {
      "id": 142,
      "usuario": "juan_pineda",
      "denominacion": "$50.000 COP",
      "valor_nominal": 50000,
      "personaje": "Gabriel García Márquez",
      "confianza_pct": 97.8,
      "latencia_ms": 42.1,
      "metodo": "rafaga_burst",
      "fecha_hora": "2026-10-16 19:28:15"
    }
  ]
}''',
        errors="400 Bad Request (parámetros de paginación inválidos)\n500 Internal Server Error.",
        consumer="Menu_principal.html (Tabla de Historial de Billetes y Auditoría)."
    )

    create_api_card(
        doc,
        num="17",
        method="POST",
        endpoint="/api/historial",
        port="Microservicio Independiente (Puerto 5001)",
        purpose="Registrar en la base de datos MySQL un nuevo evento de billete escaneado satisfactoriamente por la inteligencia artificial.",
        internal_logic="1. Extrae los datos obligatorios del body JSON: 'denominacion', 'valor_nominal' (o lo deduce automáticamente del texto), 'confianza', 'personaje' y 'metodo'.\n2. Resuelve el 'usuario_id' si se envía el nombre de usuario.\n3. Ejecuta INSERT INTO 'historial_escaneos' (usuario_id, denominacion_texto, valor_nominal, personaje, confianza_porcentaje, latencia_ms, metodo_escaneo, fecha_hora) VALUES (...).\n4. Retorna el ID autoincremental generado.",
        headers="Content-Type: application/json",
        payload='''{
  "usuario": "juan_pineda",
  "denominacion": "$50.000 COP",
  "valor_nominal": 50000,
  "personaje": "Gabriel García Márquez",
  "confianza": 97.8,
  "latencia_ms": 42.1,
  "metodo": "rafaga_burst"
}''',
        response_ok='''{
  "success": true,
  "message": "Escaneo registrado exitosamente en MySQL",
  "id_registro": 143,
  "monto_acumulado_hoy": 210000
}''',
        errors="400 Bad Request (denominación o valor nominal faltante)\n500 Internal Server Error (error en sentencia SQL INSERT).",
        consumer="Servidor Principal de IA (disparado asíncronamente tras /api/predict o /api/predict-burst)."
    )

    create_api_card(
        doc,
        num="18",
        method="DELETE",
        endpoint="/api/historial/limpiar  (Alias: POST /api/historial/limpiar)",
        port="Microservicio Independiente (Puerto 5001)",
        purpose="Permitir reiniciar la cuenta de dinero acumulada o purgar registros históricos de escaneo (por ejemplo, cuando el usuario invidente realiza un 'Toque Largo' en la app Android para reiniciar su cuenta a cero pesos).",
        internal_logic="1. Verifica los parámetros del request para determinar el alcance: '?usuario=...' o body 'solo_hoy: true/false'.\n2. Si 'solo_hoy' es true, ejecuta: 'DELETE FROM historial_escaneos WHERE usuario_id = ... AND DATE(fecha_hora) = CURDATE()'.\n3. Si es borrado total, elimina los registros del usuario especificado.\n4. Confirma la cantidad de filas afectadas y resetea el contador.",
        headers="Content-Type: application/json",
        payload='''{"usuario": "juan_pineda", "solo_hoy": true}''',
        response_ok='''{
  "success": true,
  "message": "Historial del día reiniciado a cero pesos exitosamente.",
  "registros_eliminados": 8
}''',
        errors="400 Bad Request (no se especificó usuario)\n500 Internal Server Error.",
        consumer="BilletesApp Android (Gestor de Toque Largo - Reinicio de Cuenta), Menu_principal.html (Botón 'Limpiar Historial')."
    )

    create_api_card(
        doc,
        num="19",
        method="GET",
        endpoint="/api/auth/ping  (y /api/metricas/ping)",
        port="Servicios Backend / Blueprints Modulares",
        purpose="Endpoints ligeros de liveness probe para micro-componentes de la arquitectura en caso de despliegue en contenedores Docker o Kubernetes.",
        internal_logic="Retorna de forma instantánea 'pong' y el timestamp actual sin interactuar con la base de datos ni con la GPU, para verificar la salud de los hilos de red.",
        headers="Accept: application/json",
        payload="Ninguno.",
        response_ok='''{"status": "ok", "service": "usuarios_auth_subsystem", "timestamp": 1729124400}''',
        errors="500 Internal Server Error.",
        consumer="Balanceadores de carga, health checks automatizados."
    )

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 4: TABLA COMPARATIVA CONSOLIDADA
    # ══════════════════════════════════════════════════════════════════════════
    h4 = doc.add_heading("4. Matriz Comparativa Consolidada de las 19 APIs", level=1)
    h4.runs[0].font.color.rgb = RGBColor(10, 22, 51)

    table_all = doc.add_table(rows=20, cols=5)
    table_all.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_all.autofit = False

    t_widths = [Inches(0.6), Inches(1.1), Inches(2.2), Inches(1.1), Inches(1.8)]
    for r in table_all.rows:
        for i, w in enumerate(t_widths):
            r.cells[i].width = w

    headers_tbl = ["#", "Método", "Endpoint / Ruta", "Puerto", "Propósito Principal"]
    for i, h_text in enumerate(headers_tbl):
        c = table_all.rows[0].cells[i]
        set_cell_background(c, "0A1633")
        set_cell_margins(c, 100, 100, 100, 100)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)

    matrix_data = [
        ("01", "GET", "/api/status", "5000", "Salud, modelo cargado, hardware CUDA y denominaciones"),
        ("02", "POST", "/api/predict", "5000", "Inferencia de billete individual con TTA 8 pasadas y color"),
        ("03", "POST", "/api/predict-burst", "5000", "Inferencia por ráfaga de 3 fotogramas con votación de consenso"),
        ("04", "POST", "/api/auth/registro", "5000", "Registro de cuenta con hash y generación de secreto 2FA"),
        ("05", "GET", "/api/auth/obtener-2fa-qr", "5000", "Generación de código QR en base64 para Google Authenticator"),
        ("06", "POST", "/api/auth/login", "5000", "Login seguro atómico (usuario, contraseña y código 2FA)"),
        ("07", "POST", "/api/auth/verificar-2fa", "5000", "Validación desacoplada de tokens TOTP de 6 dígitos"),
        ("08", "POST", "/api/soporte/tickets", "5000", "Radicación de tickets PQRS con código único TK-XXXX"),
        ("09", "GET", "/api/soporte/tickets", "5000", "Listado y seguimiento de tickets filtrados por usuario/estado"),
        ("10", "GET", "/api/soporte/kpis", "5000", "Cálculo en tiempo real de satisfacción y resolución de soporte"),
        ("11", "POST", "/api/soporte/tickets/<c>/calificar", "5000", "Registro de calificación de 1 a 5 estrellas para tickets"),
        ("12", "GET", "/api/ngrok_url", "5000", "Obtención de URL pública https activa del túnel ngrok"),
        ("13", "ALL", "/api/historial/* (Proxy)", "5000 -> 5001", "Proxy transparente con auto-healing hacia el puerto 5001"),
        ("14", "GET", "/api/historial/salud", "5001", "Health-check del microservicio y conectividad a MySQL"),
        ("15", "GET", "/api/historial/metricas", "5001", "KPIs de dinero escaneado hoy vs acumulado histórico y desglose"),
        ("16", "GET", "/api/historial", "5001", "Listado paginado de auditoría de escaneos guardados"),
        ("17", "POST", "/api/historial", "5001", "Inserción atómica de nuevo billete escaneado en MySQL"),
        ("18", "DELETE", "/api/historial/limpiar", "5001", "Reinicio de cuenta acumulada o depuración de registros"),
        ("19", "GET", "/api/auth/ping", "5000", "Liveness probe para monitorización de subcomponentes")
    ]

    for row_idx, row_data in enumerate(matrix_data, start=1):
        row = table_all.rows[row_idx]
        bg = "F8FAFC" if row_idx % 2 == 0 else "EDF2F7"
        for col_idx, cell_value in enumerate(row_data):
            cell = row.cells[col_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, 80, 80, 90, 90)
            p = cell.paragraphs[0]
            if col_idx in [0, 1, 3]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(cell_value)
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(30, 41, 59)
            if col_idx == 1:
                r.font.bold = True
                if cell_value == "POST":
                    r.font.color.rgb = RGBColor(16, 185, 129)
                elif cell_value == "DELETE":
                    r.font.color.rgb = RGBColor(239, 68, 68)
                elif cell_value in ["ALL", "PROXY"]:
                    r.font.color.rgb = RGBColor(245, 158, 11)
                else:
                    r.font.color.rgb = RGBColor(47, 123, 255)
            elif col_idx == 2:
                r.font.name = "Consolas"
                r.font.size = Pt(8)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 5: ESQUEMA DE BASE DE DATOS MYSQL (XAMPP)
    # ══════════════════════════════════════════════════════════════════════════
    h5 = doc.add_heading("5. Diccionario y Estructura de la Base de Datos (`visioncash_db`)", level=1)
    h5.runs[0].font.color.rgb = RGBColor(10, 22, 51)

    doc.add_paragraph(
        "El sistema persiste su información en una base de datos relacional MySQL alojada en el servidor XAMPP "
        "(Host: 192.168.0.12 o 127.0.0.1, Puerto: 3306). Está normalizada para garantizar integridad referencial "
        "y transaccionalidad atómica:"
    )

    t_db = doc.add_table(rows=5, cols=3)
    t_db.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r in t_db.rows:
        r.cells[0].width = Inches(1.8)
        r.cells[1].width = Inches(2.2)
        r.cells[2].width = Inches(2.8)

    db_headers = ["Tabla MySQL", "Columnas Principales", "Función y Relaciones"]
    for i, h_text in enumerate(db_headers):
        c = t_db.rows[0].cells[i]
        set_cell_background(c, "10214A")
        set_cell_margins(c, 100, 100, 100, 100)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)

    db_rows = [
        ("usuarios", "id, nombre_usuario, correo, password_hash, telefono, rol, secreto_2fa, activo, fecha_registro", "Catálogo de usuarios registrados. Almacena las contraseñas hasheadas y la clave Base32 para TOTP."),
        ("historial_escaneos", "id, usuario_id, usuario_nombre, denominacion_texto, valor_nominal, personaje, confianza_porcentaje, latencia_ms, metodo_escaneo, fecha_hora", "Bitácora de cada billete procesado. 'valor_nominal' permite sumar los subtotales en las consultas de métricas."),
        ("tickets_soporte", "id, codigo_ticket, usuario, tipo_solicitud, asunto, mensaje, prioridad, estado, respuesta_tecnica, calificacion, fecha_creacion", "Mesa de ayuda y PQRS. Vinculado al módulo de KPIs gerenciales y satisfacción de clientes."),
        ("sesiones_activas", "id, usuario_id, token_sesion, ip_cliente, user_agent, fecha_inicio, expira_en", "Auditoría de seguridad y control de sesiones web simultáneas.")
    ]

    for idx, (t_name, t_cols, t_desc) in enumerate(db_rows, start=1):
        row = t_db.rows[idx]
        bg = "F8FAFC" if idx % 2 == 0 else "EDF2F7"
        for c_idx, val in enumerate([t_name, t_cols, t_desc]):
            cell = row.cells[c_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, 80, 80, 90, 90)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(30, 41, 59)
            if c_idx == 0:
                r.font.bold = True
            elif c_idx == 1:
                r.font.name = "Consolas"
                r.font.size = Pt(8)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 6: GUÍA DE EJECUCIÓN DEL SISTEMA
    # ══════════════════════════════════════════════════════════════════════════
    h6 = doc.add_heading("6. Guía Rápida de Puesta en Marcha y Ejecución", level=1)
    h6.runs[0].font.color.rgb = RGBColor(10, 22, 51)

    p_run = doc.add_paragraph()
    p_run.add_run("Paso 1: Iniciar MySQL en XAMPP\n").bold = True
    p_run.add_run("Abre el panel de control de XAMPP y presiona 'Start' en el módulo MySQL (puerto 3306).\n\n")
    p_run.add_run("Paso 2: Iniciar los Servicios de VisionCash con un Solo Clic\n").bold = True
    p_run.add_run("Haz doble clic en el script:\n")
    p_run.add_run("   'componentes_transversales/configuracion/iniciar_servicios.bat'\n").bold = True
    p_run.add_run("Este script automatizado levantará automáticamente:\n")
    p_run.add_run("   1. El Microservicio de Historial en http://localhost:5001\n")
    p_run.add_run("   2. El Servidor Principal de IA en http://localhost:5000\n")
    p_run.add_run("   3. El túnel seguro de ngrok para acceso público en internet y sincronización con GitHub.\n\n")
    p_run.add_run("Paso 3: Abrir la Aplicación\n").bold = True
    p_run.add_run("• En la Web: Ingresa a 'https://jdpinedagarzon-hash.github.io/Billetes/' o en tu navegador local en 'http://localhost:5000/Menu_principal_2.html'.\n")
    p_run.add_run("• En Android: Abre 'BilletesApp' en el celular. Se conectará automáticamente al túnel ngrok activo.")

    # Guardar documento
    doc.save(str(output_path))
    print(f"[OK] Documento generado exitosamente en: {output_path}")

if __name__ == "__main__":
    out_dir = Path(r"d:\proyecto\Lo que hay en google\documentacion")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    file_apis = out_dir / "VisionCash_Documentacion_Oficial_APIs_y_Microservicios.docx"
    file_tech = out_dir / "Documentacion_Tecnica_VisionCash_Arquitectura_y_APIs.docx"
    
    build_full_documentation(file_apis)
    build_full_documentation(file_tech)
