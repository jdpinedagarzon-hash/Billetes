# VisionCash — Estructura del Proyecto

Sistema de reconocimiento de billetes colombianos para personas con discapacidad visual.
Utiliza visión artificial (PyTorch EfficientNetV2-S) con interfaz web accesible y app Android.

---

## Arquitectura de Carpetas

```
visioncash/
│
├── presentacion/                  # Capa de Presentación (Interfaz de Usuario)
│   ├── publico/                   # Archivos públicos descargables (APK, imágenes)
│   │   ├── BilletesApp.apk        # App Android para personas con discapacidad visual
│   │   ├── billetia-logo.png
│   │   └── hero-bill-scan.png
│   │
│   └── codigo_fuente/
│       ├── componentes/
│       │   └── camara_hud_accesible.js  # HUD de cámara con accesibilidad (TTS)
│       ├── vistas/                # Páginas HTML del sistema web
│       │   ├── index.html         # Página de inicio / landing
│       │   ├── Menu_principal.html      # Escáner web principal
│       │   ├── Menu_principal_2.html    # Login
│       │   ├── Menu_principal_3.html    # Registro de usuario
│       │   ├── verificar_2fa.html       # Verificación 2FA (Google Authenticator)
│       │   ├── Soporte.html       # Mesa de ayuda y métricas KPI
│       │   ├── Contacto.html
│       │   ├── Politicas.html
│       │   ├── Terminos.html
│       │   └── acerca_nosotros.html
│       ├── servicios_api/
│       │   └── config.js          # Config central: URL ngrok, endpoints, ajustes
│       └── utilidades/
│           └── sesion.js          # Gestión de sesión de usuario (localStorage)
│
├── servicios_backend/             # Capa de Servicios (Servidor Flask + IA)
│   ├── iniciar_servidor.py        # Servidor Flask principal (puerto 5000)
│   ├── dependencias.txt           # requirements.txt del sistema
│   └── aplicacion/
│       ├── api/                   # Endpoints REST
│       ├── logica_negocio/        # Procesamiento de imágenes y usuarios
│       ├── integracion/           # Intermediarios externos
│       └── modelos_db/            # Esquemas de datos
│
├── motor_ia/                      # Capa de IA (Entrenamiento y Modelos)
│   ├── modelos_entrenados/
│   │   ├── banknote_efficientnetv2s.pt   # Modelo PyTorch entrenado (RTX 5060 Ti)
│   │   └── classes.json                  # Mapa de clases con info de billetes
│   ├── entrenamiento/
│   │   ├── train.py               # Script de entrenamiento con CUDA
│   │   └── run_pipeline.bat       # Pipeline completo: augment → train
│   └── utilidades_imagenes/
│       └── augment.py             # Augmentación de dataset de imágenes
│
├── capa_datos/                    # Capa de Datos (Base de Datos)
│   ├── base_de_datos/
│   │   ├── conexion_bd.py         # Conexión MySQL (XAMPP 192.168.0.12)
│   │   ├── inicializar_bd.py      # Script de inicialización de tablas
│   │   └── visioncash_db.sql      # Esquema SQL completo de la base de datos
│   └── almacenamiento_imagenes/
│       └── README.md
│
└── componentes_transversales/     # Componentes Compartidos y Configuración
    ├── configuracion/
    │   ├── iniciar_servicios.bat  # Script de inicio de todos los servicios
    │   ├── actualizar_ngrok.bat   # Actualización manual de URL ngrok
    │   ├── actualizar_ngrok.ps1   # Actualización ngrok en PowerShell
    │   └── ngrok_url.txt          # URL activa del túnel ngrok (auto-actualizada)
    ├── monitoreo/
    │   └── microservicio_historial.py  # Microservicio de historial (puerto 5001)
    ├── respaldos/
    │   └── backup_bd.py           # Script de respaldo de la base de datos
    └── seguridad/
        └── autenticacion_seguridad.py  # Utilidades de seguridad y autenticación
```

---

## Como Iniciar el Sistema

### Opcion 1 — Script automatico (recomendado)
```
Doble clic en:
visioncash\componentes_transversales\configuracion\iniciar_servicios.bat
```
Esto inicia automaticamente:
1. Microservicio de historial (puerto 5001)
2. Servidor Flask + IA (puerto 5000)
3. Tunel ngrok (actualizacion automatica cada 15s en GitHub)

### Opcion 2 — Manual
```bash
# Desde la raiz del proyecto (Lo que hay en google\)
python visioncash\servicios_backend\iniciar_servidor.py
python visioncash\componentes_transversales\monitoreo\microservicio_historial.py
ngrok.exe http 5000
```

---

## Accesos del Sistema

| Servicio | URL |
|---|---|
| App Web Local | http://localhost:5000/Menu_principal.html |
| GitHub Pages (publico) | https://jdpinedagarzon-hash.github.io/Billetes/ |
| API Estado | http://localhost:5000/api/status |
| Historial / KPIs | http://localhost:5001/api/historial/metricas |
| Base de Datos (XAMPP) | http://192.168.0.12/phpmyadmin/ |

---

## App Android

La aplicacion BilletesApp.apk en presentacion/publico/ esta disenada para personas con discapacidad visual:
- Detecta el billete automaticamente sin necesidad de tocar pantalla
- Anuncia el resultado por voz (Text-to-Speech)
- Obtiene la URL del servidor automaticamente desde GitHub (no requiere configuracion manual)

---

## Tecnologias

| Componente | Tecnologia |
|---|---|
| Modelo IA | PyTorch - EfficientNetV2-S - CUDA 12.8 |
| Backend | Python - Flask - Flask-CORS |
| Base de Datos | MySQL (XAMPP) - PyMySQL |
| Autenticacion 2FA | pyotp (TOTP RFC 6238) - Google Authenticator |
| Acceso remoto | ngrok (tunel HTTPS) - GitHub Pages |
| App Movil | Android (Kotlin) - CameraX - OkHttp |
