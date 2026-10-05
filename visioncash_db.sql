-- ============================================================================
-- BASE DE DATOS: visioncash_db
-- Sistema: VisionCash / BilletIA - Reconocimiento de Billetes Colombianos
-- Servidor: MySQL / MariaDB (XAMPP - 192.168.0.12)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `visioncash_db`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `visioncash_db`;

-- ----------------------------------------------------------------------------
-- 1. TABLA: usuarios (Registro, Acceso y Seguridad)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `historial_escaneos`;
DROP TABLE IF EXISTS `mesa_ayuda_tickets`;
DROP TABLE IF EXISTS `usuarios`;

CREATE TABLE `usuarios` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(100) NOT NULL COMMENT 'Nombres del usuario',
  `apellido` VARCHAR(100) NOT NULL COMMENT 'Apellidos del usuario',
  `nombre_usuario` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Identificador único de acceso',
  `correo` VARCHAR(120) NOT NULL UNIQUE COMMENT 'Correo institucional o personal',
  `contrasena_hash` VARCHAR(255) NOT NULL COMMENT 'Contraseña encriptada (SHA-256 / bcrypt)',
  `codigo_2fa` VARCHAR(6) DEFAULT '123456' COMMENT 'Código temporal para doble factor',
  `es_2fa_activo` TINYINT(1) DEFAULT 1 COMMENT '1 = Requiere 2FA, 0 = Desactivado',
  `rol` ENUM('usuario', 'administrador', 'soporte') DEFAULT 'usuario' COMMENT 'Rol en la plataforma',
  `activo` TINYINT(1) DEFAULT 1 COMMENT '1 = Activo, 0 = Bloqueado',
  `fecha_registro` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `ultimo_login` DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 2. TABLA: denominaciones_billetes (Catálogo oficial de billetes colombianos)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `denominaciones_billetes`;

CREATE TABLE `denominaciones_billetes` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `codigo_clase` VARCHAR(20) NOT NULL UNIQUE COMMENT 'Nombre de clase en la IA (2.000, 5.000, etc.)',
  `valor_nominal` INT NOT NULL COMMENT 'Valor numérico para cálculos (ej: 2000, 50000)',
  `denominacion` VARCHAR(50) NOT NULL COMMENT 'Formato texto ($2.000 COP)',
  `nombre_comun` VARCHAR(100) NOT NULL COMMENT 'Nombre descriptivo completo',
  `personaje_principal` VARCHAR(150) NOT NULL COMMENT 'Personaje histórico en el anverso',
  `reverso` VARCHAR(255) NOT NULL COMMENT 'Paisaje o símbolo en el reverso',
  `elementos_seguridad` TEXT NOT NULL COMMENT 'Características de seguridad para autenticación',
  `color_hex` VARCHAR(20) DEFAULT '#2563eb' COMMENT 'Color representativo en la interfaz',
  `activo` TINYINT(1) DEFAULT 1 COMMENT '1 = En circulación / soportado por el modelo',
  `fecha_creacion` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 3. TABLA: historial_escaneos (Gestionada por el Microservicio de Historial)
-- ----------------------------------------------------------------------------
CREATE TABLE `historial_escaneos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NULL COMMENT 'Usuario que realizó el escaneo (NULL = Invitado)',
  `denominacion_id` INT NULL COMMENT 'Relación con el catálogo de billetes',
  `denominacion_texto` VARCHAR(60) NOT NULL COMMENT 'Texto devuelto por la IA ($50.000 COP)',
  `valor_nominal` INT DEFAULT 0 COMMENT 'Valor entero para cálculo de sumas diarias',
  `confianza_porcentaje` DECIMAL(5,2) NOT NULL COMMENT 'Nivel de certeza de la IA (0.00 - 100.00)',
  `metodo_escaneo` ENUM('Subida de foto', 'Cámara en vivo', 'Captura manual') DEFAULT 'Subida de foto',
  `latencia_ms` DECIMAL(7,2) DEFAULT 0.00 COMMENT 'Tiempo de procesamiento del modelo',
  `resultado_estado` ENUM('exitoso', 'dudoso', 'no_reconocido') DEFAULT 'exitoso',
  `ip_origen` VARCHAR(45) DEFAULT '127.0.0.1' COMMENT 'Dirección IP del cliente',
  `fecha_hora` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Momento exacto del escaneo',
  INDEX `idx_fecha_hora` (`fecha_hora`),
  INDEX `idx_usuario_id` (`usuario_id`),
  INDEX `idx_denominacion_id` (`denominacion_id`),
  CONSTRAINT `fk_historial_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_historial_denominacion` FOREIGN KEY (`denominacion_id`) REFERENCES `denominaciones_billetes` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 4. TABLA: mesa_ayuda_tickets (Gestión de Incidencias, Requerimientos y KPIs)
-- ----------------------------------------------------------------------------
CREATE TABLE `mesa_ayuda_tickets` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `codigo_ticket` VARCHAR(25) NOT NULL UNIQUE COMMENT 'Código único visible (ej: CAS-104928)',
  `usuario_id` INT NULL COMMENT 'Usuario que registró la solicitud',
  `tipo` ENUM('incidencia', 'requerimiento') NOT NULL COMMENT 'Incidencia técnica o Requerimiento de mejora',
  `categoria` VARCHAR(60) DEFAULT 'Reconocimiento IA' COMMENT 'Categoría del caso',
  `titulo` VARCHAR(200) NOT NULL COMMENT 'Asunto corto del ticket',
  `descripcion` TEXT NOT NULL COMMENT 'Detalle completo del problema o solicitud',
  `prioridad` ENUM('baja', 'media', 'alta', 'critica') DEFAULT 'media',
  `sla_horas_limite` INT DEFAULT 24 COMMENT 'SLA: Tiempo máximo comprometido de respuesta en horas',
  `estado` ENUM('abierto', 'en_proceso', 'resuelto', 'cerrado') DEFAULT 'abierto',
  `calificacion_csat` INT NULL COMMENT 'KPI CSAT: Satisfacción del cliente (1 a 5 estrellas)',
  `comentarios_resolucion` TEXT NULL COMMENT 'Respuesta o solución dada por el equipo',
  `fecha_creacion` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `fecha_actualizacion` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `fecha_resolucion` DATETIME NULL COMMENT 'Momento en que se dio solución al caso',
  `tiempo_resolucion_minutos` INT NULL COMMENT 'KPI MTTR: Minutos transcurridos hasta la resolución',
  INDEX `idx_ticket_estado` (`estado`),
  INDEX `idx_ticket_tipo` (`tipo`),
  INDEX `idx_ticket_usuario` (`usuario_id`),
  CONSTRAINT `fk_ticket_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 5. VISTAS SQL PARA MÉTRICAS Y KPIS DE MESA DE AYUDA
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `v_kpis_mesa_ayuda` AS
SELECT
  COUNT(*) AS total_tickets,
  SUM(CASE WHEN tipo = 'incidencia' THEN 1 ELSE 0 END) AS total_incidencias,
  SUM(CASE WHEN tipo = 'requerimiento' THEN 1 ELSE 0 END) AS total_requerimientos,
  SUM(CASE WHEN estado = 'abierto' THEN 1 ELSE 0 END) AS tickets_abiertos,
  SUM(CASE WHEN estado = 'en_proceso' THEN 1 ELSE 0 END) AS tickets_en_proceso,
  SUM(CASE WHEN estado IN ('resuelto', 'cerrado') THEN 1 ELSE 0 END) AS tickets_resueltos,
  -- Tasa de resolución (%)
  ROUND((SUM(CASE WHEN estado IN ('resuelto', 'cerrado') THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(*), 0), 1) AS tasa_resolucion_pct,
  -- Cumplimiento de SLA (% de casos resueltos dentro del tiempo límite)
  ROUND((SUM(CASE WHEN estado IN ('resuelto', 'cerrado') AND (tiempo_resolucion_minutos <= sla_horas_limite * 60) THEN 1 ELSE 0 END) * 100.0) /
        NULLIF(SUM(CASE WHEN estado IN ('resuelto', 'cerrado') THEN 1 ELSE 0 END), 0), 1) AS cumplimiento_sla_pct,
  -- MTTR: Tiempo medio de resolución en horas
  ROUND(AVG(CASE WHEN estado IN ('resuelto', 'cerrado') THEN tiempo_resolucion_minutos / 60.0 ELSE NULL END), 1) AS mttr_horas_promedio,
  -- CSAT Promedio (Customer Satisfaction Score 1 a 5)
  ROUND(AVG(calificacion_csat), 2) AS csat_promedio
FROM `mesa_ayuda_tickets`;

-- ----------------------------------------------------------------------------
-- 6. DATOS INICIALES (SEMILLAS)
-- ----------------------------------------------------------------------------

-- A) Catálogo oficial de billetes colombianos
INSERT INTO `denominaciones_billetes` 
(`codigo_clase`, `valor_nominal`, `denominacion`, `nombre_comun`, `personaje_principal`, `reverso`, `elementos_seguridad`, `color_hex`) VALUES
('2.000', 2000, '$2.000 COP', 'Billete de $2.000 COP', 'Débora Arango', 'Caño Cristales (Río de los siete colores)', 'Franja vertical con cambio de color verde a azul y texto de seguridad.', '#3b82f6'),
('5.000', 5000, '$5.000 COP', 'Billete de $5.000 COP', 'José Asunción Silva', 'Páramos colombianos y planta de puya', 'Poema Melancolía en microtexto y flor de puya visible al trasluz.', '#9333ea'),
('10.000', 10000, '$10.000 COP', 'Billete de $10.000 COP', 'Virginia Gutiérrez', 'Región Amazónica y flor de la Victoria Regia', 'Impresión en alto relieve táctil y marca de agua con el rostro de Virginia Gutiérrez.', '#ea580c'),
('20.000', 20000, '$20.000 COP', 'Billete de $20.000 COP', 'Alfonso López Michelsen', 'Canales de La Mojana y Sombrero Vueltiao', 'Fruto del anón con cambio de color verde a azul y textura táctil en el sombrero vueltiao.', '#0d9488'),
('50000', 50000, '$50.000 COP', 'Billete de $50.000 COP', 'Gabriel García Márquez', 'Ciudad Perdida (Sierra Nevada de Santa Marta)', 'Colibrí picando flor con efecto de movimiento y mariposas amarillas fluorescentes.', '#2563eb'),
('100.000', 100000, '$100.000 COP', 'Billete de $100.000 COP', 'Carlos Lleras Restrepo', 'Valle de Cocora y Palma de Cera', 'Flor del sietecueros que cambia de color verde a azul y cinta de seguridad.', '#16a34a');

-- B) Usuarios de prueba (contraseña por defecto '12345678' con hash SHA-256)
-- Hash de 'Admin123!': a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3 (ejemplo)
INSERT INTO `usuarios` (`nombre`, `apellido`, `nombre_usuario`, `correo`, `contrasena_hash`, `codigo_2fa`, `rol`) VALUES
('Juan', 'Pérez', 'Usuario1', 'usuario1@visioncash.com', 'Admin123!', '123456', 'usuario'),
('Carlos', 'Gómez', 'AdminVision', 'admin@visioncash.com', 'Admin123!', '654321', 'administrador'),
('María', 'Rodríguez', 'MariaSoporte', 'soporte@visioncash.com', 'Admin123!', '112233', 'soporte');

-- C) Historial inicial de escaneos (incluyendo escaneos de hoy y de días anteriores para probar métricas)
INSERT INTO `historial_escaneos` 
(`usuario_id`, `denominacion_id`, `denominacion_texto`, `valor_nominal`, `confianza_porcentaje`, `metodo_escaneo`, `latencia_ms`, `fecha_hora`) VALUES
(1, 5, 'Billete de $50.000 COP', 50000, 98.40, 'Subida de foto', 145.20, NOW() - INTERVAL 1 HOUR),
(1, 4, 'Billete de $20.000 COP', 20000, 96.80, 'Cámara en vivo', 82.50, NOW() - INTERVAL 30 MINUTE),
(1, 3, 'Billete de $10.000 COP', 10000, 99.10, 'Subida de foto', 130.00, NOW() - INTERVAL 10 MINUTE),
(1, 1, 'Billete de $2.000 COP', 2000, 95.50, 'Cámara en vivo', 79.10, NOW() - INTERVAL 5 MINUTE),
(1, 2, 'Billete de $5.000 COP', 5000, 97.20, 'Subida de foto', 120.30, NOW() - INTERVAL 1 DAY),
(2, 5, 'Billete de $50.000 COP', 50000, 98.90, 'Cámara en vivo', 85.00, NOW() - INTERVAL 2 DAY);

-- D) Tickets iniciales en Mesa de Ayuda (para visualizar KPIs y gestión de casos)
INSERT INTO `mesa_ayuda_tickets`
(`codigo_ticket`, `usuario_id`, `tipo`, `categoria`, `titulo`, `descripcion`, `prioridad`, `sla_horas_limite`, `estado`, `calificacion_csat`, `fecha_creacion`, `fecha_resolucion`, `tiempo_resolucion_minutos`, `comentarios_resolucion`) VALUES
('CAS-003921', 1, 'incidencia', 'Cámara y Detección', 'Dificultad para enfocar billete de $10.000 en baja luz', 'Al escanear en ambientes con poca luz el billete de 10.000 confunde con 20.000.', 'alta', 12, 'en_proceso', NULL, NOW() - INTERVAL 5 HOUR, NULL, NULL, 'Se recomendó activar la normalización de brillo adaptativo en el modelo.'),
('CAS-002480', 1, 'requerimiento', 'Exportación y Reportes', 'Solicitud de exportar historial a formato PDF', 'Me gustaría poder descargar un reporte semanal de billetes escaneados con sus valores.', 'media', 48, 'resuelto', 5, NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 2 DAY, 1440, 'Funcionalidad planificada e integrada mediante el microservicio de historial.'),
('CAS-001904', 1, 'incidencia', 'Interfaz de Usuario', 'El contador de FPS parpadea en teléfonos móviles', 'En un teléfono Redmi Note 11 el número de FPS oscilaba bruscamente.', 'baja', 24, 'resuelto', 4, NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 4 DAY, 960, 'Se ajustó el intervalo de refresco a 1000ms.');
