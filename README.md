# VisionCash — Reconocimiento Inteligente de Billetes Colombianos

Sistema de reconocimiento de billetes colombianos con inteligencia artificial (PyTorch EfficientNetV2-S con GPU RTX 5060 Ti / CUDA 12.8), interfaz web accesible y aplicación móvil nativa Android para personas con discapacidad visual.

---

## Arquitectura de Carpetas

```
Lo que hay en google/
│
├── presentacion/                  # Capa de Presentación (Interfaz de Usuario)
│   ├── publico/                   # Archivos públicos descargables (APK, imágenes)
│   │   ├── BilletesApp.apk        # App Android para personas con discapacidad visual
│   │   ├── billetia-logo.png      # Logo oficial
│   │   └── hero-bill-scan.png     # Banner de portada
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
│       ├── api/                   # Endpoints REST (rutas_reconocimiento, metricas, usuarios)
│       ├── logica_negocio/        # Procesamiento de imágenes (OpenCV) y gestión de usuarios
│       ├── integracion/           # Intermediarios de autenticación
│       └── modelos_db/            # Esquemas de datos
│
├── motor_ia/                      # Capa de IA (Entrenamiento y Modelos)
│   ├── modelos_entrenados/
│   │   ├── banknote_efficientnetv2s.pt   # Modelo PyTorch entrenado (RTX 5060 Ti)
│   │   └── classes.json                  # Mapa de clases con info de billetes
│   ├── entrenamiento/
│   │   ├── train.py               # Script de entrenamiento con CUDA
│   │   └── run_pipeline.bat       # Pipeline completo: augment → train
│   ├── utilidades_imagenes/
│   │   └── augment.py             # Augmentación de dataset de imágenes
│   └── augmented_dataset/         # Dataset procesado por clases
│
├── capa_datos/                    # Capa de Datos (Base de Datos)
│   ├── base_de_datos/
│   │   ├── conexion_bd.py         # Conexión MySQL (XAMPP 192.168.0.12)
│   │   ├── inicializar_bd.py      # Script de inicialización de tablas
│   │   └── visioncash_db.sql      # Esquema SQL completo de la base de datos
│   └── almacenamiento_imagenes/
│       └── README.md
│
├── componentes_transversales/     # Componentes Compartidos y Configuración
│   ├── configuracion/
│   │   ├── iniciar_servicios.bat  # Script de inicio de todos los servicios
│   │   ├── actualizar_ngrok.bat   # Actualización manual de URL ngrok
│   │   ├── actualizar_ngrok.ps1   # Actualización ngrok en PowerShell
│   │   └── ngrok_url.txt          # URL activa del túnel ngrok (auto-actualizada)
│   ├── monitoreo/
│   │   └── microservicio_historial.py  # Microservicio de historial (puerto 5001)
│   ├── respaldos/
│   │   └── backup_bd.py           # Script de respaldo de la base de datos
│   └── seguridad/
│       └── autenticacion_seguridad.py  # Utilidades de seguridad y autenticación
│
└── documentacion/                 # Documentación Técnica Integral
    └── Documentacion_Tecnica_VisionCash_Arquitectura_y_APIs.docx
```

---

## Cómo Iniciar el Sistema

### Opción 1 — Script automático (recomendado)
```cmd
Doble clic en:
componentes_transversales\configuracion\iniciar_servicios.bat
```
Esto inicia automáticamente:
1. Microservicio de historial (puerto 5001)
2. Servidor Flask + IA (puerto 5000)
3. Túnel ngrok (actualización automática cada 15s en GitHub)

### Opción 2 — Manual desde la raíz (`Lo que hay en google\`):
```bash
python componentes_transversales\monitoreo\microservicio_historial.py
python servicios_backend\iniciar_servidor.py
ngrok.exe http 5000
```

---

## Accesos del Sistema

| Servicio | URL |
|---|---|
| App Web Local | http://localhost:5000/Menu_principal.html |
| Landing Informativa | http://localhost:5000/index.html |
| Mesa de Ayuda & KPIs | http://localhost:5000/Soporte.html |
| API Estado del Servidor | http://localhost:5000/api/status |
| Microservicio Historial | http://localhost:5001/api/historial/metricas |
| Descarga de APK | http://localhost:5000/BilletesApp.apk |
