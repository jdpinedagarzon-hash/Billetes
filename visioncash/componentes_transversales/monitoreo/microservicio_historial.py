"""
══════════════════════════════════════════════════════════════════════════════
MICROSERVICIO DE HISTORIAL Y MÉTRICAS (VisionCash)
══════════════════════════════════════════════════════════════════════════════
Este microservicio desacoplado se encarga exclusivamente de:
1. Registrar escaneos de billetes en la base de datos MySQL (XAMPP).
2. Consultar el historial con fecha y hora completa, usuario y denominación.
3. Calcular métricas en tiempo real:
   - Cuántos billetes se escanearon en el día de hoy (cantidad y monto en $ COP).
   - El total histórico acumulado (cantidad y monto total en $ COP).
   - Promedio de confianza y desglose por denominación.
4. Exponer una API REST ligera e independiente en el puerto 5001.
══════════════════════════════════════════════════════════════════════════════
"""

import os
import re
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from conexion_bd import obtener_conexion, probar_conexion

app = Flask(__name__)
CORS(app)

PUERTO = 5001


def formatear_pesos_cop(valor):
    """Convierte un entero a formato de moneda colombiana: 50000 -> $50.000 COP."""
    try:
        val_int = int(valor or 0)
        return f"${val_int:,.0f} COP".replace(",", ".")
    except Exception:
        return "$0 COP"


def extraer_valor_nominal(texto_denominacion):
    """
    Extrae el número de la denominación si viene como texto.
    Ejemplo: 'Billete de $50.000 COP' -> 50000, '$2.000 COP' -> 2000
    """
    if not texto_denominacion:
        return 0
    # Si ya contiene dígitos
    limpio = str(texto_denominacion).replace("$", "").replace("COP", "").replace("Billete de", "").strip()
    match = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)", limpio)
    if match:
        num_str = match.group(1).replace(".", "")
        try:
            return int(num_str)
        except ValueError:
            return 0
    return 0


# ─── 1. ENDPOINT: Salud del Microservicio (Healthcheck) ──────────────────────
@app.route("/api/historial/salud", methods=["GET"])
def healthcheck():
    bd_ok, msg_bd = probar_conexion()
    return jsonify({
        "servicio": "Microservicio de Historial VisionCash",
        "estado": "ACTIVO",
        "puerto": PUERTO,
        "base_datos_conectada": bd_ok,
        "detalle_bd": msg_bd,
        "timestamp": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }), (200 if bd_ok else 503)


# ─── 2. ENDPOINT: Métricas y Resumen (Día actual vs Total histórico) ─────────
@app.route("/api/historial/resumen", methods=["GET"])
@app.route("/api/historial/metricas", methods=["GET"])
def obtener_resumen_metricas():
    """
    Devuelve los KPIs del historial solicitados para la universidad:
    - Cuánto se escaneó en el día (cantidad de billetes y monto total).
    - Cuánto se ha escaneado en total histórico (cantidad y monto acumulado).
    - Desglose por billete y promedio de certeza de la IA.
    """
    usuario_id = request.args.get("usuario_id", default=None, type=int)
    usuario_nombre = request.args.get("usuario", default="", type=str).strip()

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            # Construir cláusulas WHERE según si se consulta por usuario individual o global
            if usuario_id:
                filtro_hoy = "WHERE DATE(h.fecha_hora) = CURDATE() AND h.usuario_id = %s"
                filtro_tot = "WHERE h.usuario_id = %s"
                params_hoy = (usuario_id,)
                params_tot = (usuario_id,)
            elif usuario_nombre and usuario_nombre.lower() != "todos":
                filtro_hoy = "WHERE DATE(h.fecha_hora) = CURDATE() AND (h.usuario_nombre = %s OR u.nombre_usuario = %s)"
                filtro_tot = "WHERE (h.usuario_nombre = %s OR u.nombre_usuario = %s)"
                params_hoy = (usuario_nombre, usuario_nombre)
                params_tot = (usuario_nombre, usuario_nombre)
            else:
                filtro_hoy = "WHERE DATE(h.fecha_hora) = CURDATE()"
                filtro_tot = ""
                params_hoy = ()
                params_tot = ()

            # 1. Billetes escaneados HOY
            sql_hoy = f"""
                SELECT 
                    COUNT(*) AS cantidad_hoy,
                    COALESCE(SUM(h.valor_nominal), 0) AS monto_hoy,
                    COALESCE(AVG(h.confianza_porcentaje), 0) AS confianza_hoy
                FROM historial_escaneos h
                LEFT JOIN usuarios u ON h.usuario_id = u.id
                {filtro_hoy};
            """
            cur.execute(sql_hoy, params_hoy)
            datos_hoy = cur.fetchone()

            # 2. Total acumulado HISTÓRICO
            sql_tot = f"""
                SELECT 
                    COUNT(*) AS cantidad_total,
                    COALESCE(SUM(h.valor_nominal), 0) AS monto_total,
                    COALESCE(AVG(h.confianza_porcentaje), 0) AS confianza_total
                FROM historial_escaneos h
                LEFT JOIN usuarios u ON h.usuario_id = u.id
                {filtro_tot};
            """
            cur.execute(sql_tot, params_tot)
            datos_total = cur.fetchone()

            # 3. Desglose de billetes escaneados HOY por denominación
            sql_desglose = f"""
                SELECT 
                    h.denominacion_texto,
                    COUNT(*) AS cantidad,
                    COALESCE(SUM(h.valor_nominal), 0) AS subtotal
                FROM historial_escaneos h
                LEFT JOIN usuarios u ON h.usuario_id = u.id
                {filtro_hoy}
                GROUP BY h.denominacion_texto
                ORDER BY cantidad DESC;
            """
            cur.execute(sql_desglose, params_hoy)
            desglose_hoy = cur.fetchall()

            # 4. Desglose por método de escaneo
            sql_metodos = f"""
                SELECT 
                    h.metodo_escaneo,
                    COUNT(*) AS cantidad
                FROM historial_escaneos h
                LEFT JOIN usuarios u ON h.usuario_id = u.id
                {filtro_tot}
                GROUP BY h.metodo_escaneo;
            """
            cur.execute(sql_metodos, params_tot)
            desglose_metodos = cur.fetchall()

        conn.close()

        cant_hoy   = int(datos_hoy["cantidad_hoy"] or 0)
        monto_hoy  = int(datos_hoy["monto_hoy"] or 0)
        cant_tot   = int(datos_total["cantidad_total"] or 0)
        monto_tot  = int(datos_total["monto_total"] or 0)
        conf_hoy   = round(float(datos_hoy["confianza_hoy"] or 0.0), 1)
        conf_tot   = round(float(datos_total["confianza_total"] or 0.0), 1)

        msg_usuario = f" para {usuario_nombre}" if usuario_nombre and usuario_nombre.lower() != "todos" else ""

        return jsonify({
            "success": True,
            "microservicio": "Historial & Métricas",
            "usuario": usuario_nombre or "Todos",
            "resumen": {
                "hoy": {
                    "escaneos_cantidad": cant_hoy,
                    "monto_total_num": monto_hoy,
                    "monto_total_formato": formatear_pesos_cop(monto_hoy),
                    "confianza_promedio": conf_hoy,
                    "mensaje": f"Hoy se escanearon {cant_hoy} billetes por un total de {formatear_pesos_cop(monto_hoy)}{msg_usuario}."
                },
                "historico": {
                    "escaneos_cantidad": cant_tot,
                    "monto_total_num": monto_tot,
                    "monto_total_formato": formatear_pesos_cop(monto_tot),
                    "confianza_promedio": conf_tot,
                    "mensaje": f"En total se han registrado {cant_tot} escaneos por {formatear_pesos_cop(monto_tot)}{msg_usuario}."
                },
                "desglose_hoy": desglose_hoy,
                "desglose_metodos": desglose_metodos
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error al calcular métricas en el microservicio: {str(e)}"
        }), 500



# ─── 3. ENDPOINT: Obtener Lista del Historial ─────────────────────────────────
@app.route("/api/historial", methods=["GET"])
def listar_historial():
    """
    Retorna los últimos registros de escaneos con fecha y hora completa,
    usuario que escaneó, denominación, monto, método y porcentaje de confianza.
    """
    limite = request.args.get("limite", default=30, type=int)
    usuario_id = request.args.get("usuario_id", default=None, type=int)
    usuario_nombre = request.args.get("usuario", default="", type=str).strip()

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            # Traemos la columna fecha_hora directamente y la formateamos en Python
            # para evitar choques con el formateador de PyMySQL (%d)
            if usuario_id:
                cur.execute("""
                    SELECT 
                        h.id,
                        h.denominacion_texto AS denom,
                        h.valor_nominal,
                        h.confianza_porcentaje,
                        h.metodo_escaneo AS method,
                        h.latencia_ms,
                        h.fecha_hora,
                        COALESCE(h.usuario_nombre, u.nombre_usuario, 'Invitado') AS usuario
                    FROM historial_escaneos h
                    LEFT JOIN usuarios u ON h.usuario_id = u.id
                    WHERE h.usuario_id = %s
                    ORDER BY h.fecha_hora DESC
                    LIMIT %s;
                """, (usuario_id, limite))
            elif usuario_nombre and usuario_nombre.lower() != "todos":
                cur.execute("""
                    SELECT 
                        h.id,
                        h.denominacion_texto AS denom,
                        h.valor_nominal,
                        h.confianza_porcentaje,
                        h.metodo_escaneo AS method,
                        h.latencia_ms,
                        h.fecha_hora,
                        COALESCE(h.usuario_nombre, u.nombre_usuario, 'Invitado') AS usuario
                    FROM historial_escaneos h
                    LEFT JOIN usuarios u ON h.usuario_id = u.id
                    WHERE h.usuario_nombre = %s OR u.nombre_usuario = %s
                    ORDER BY h.fecha_hora DESC
                    LIMIT %s;
                """, (usuario_nombre, usuario_nombre, limite))
            else:
                cur.execute("""
                    SELECT 
                        h.id,
                        h.denominacion_texto AS denom,
                        h.valor_nominal,
                        h.confianza_porcentaje,
                        h.metodo_escaneo AS method,
                        h.latencia_ms,
                        h.fecha_hora,
                        COALESCE(h.usuario_nombre, u.nombre_usuario, 'Invitado') AS usuario
                    FROM historial_escaneos h
                    LEFT JOIN usuarios u ON h.usuario_id = u.id
                    ORDER BY h.fecha_hora DESC
                    LIMIT %s;
                """, (limite,))

            registros = cur.fetchall()
        conn.close()

        # Dar formato amigable de fecha y moneda para la vista
        for r in registros:
            fh = r.get("fecha_hora")
            if isinstance(fh, (datetime.datetime, datetime.date)):
                r["time"] = fh.strftime("%d/%m/%Y %H:%M:%S")
            else:
                r["time"] = str(fh or "--")
            
            r["conf"] = f"{float(r.get('confianza_porcentaje') or 0.0):.1f}%"
            r["monto_formato"] = formatear_pesos_cop(r.get("valor_nominal") or 0)
            if not r.get("usuario"):
                r["usuario"] = "Invitado"

        return jsonify({
            "success": True,
            "total": len(registros),
            "registros": registros
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error al consultar historial: {str(e)}"
        }), 500


# ─── 4. ENDPOINT: Registrar un nuevo escaneo en MySQL ─────────────────────────
@app.route("/api/historial", methods=["POST"])
def registrar_escaneo():
    """
    Registra un escaneo en la base de datos MySQL (XAMPP).
    Recibe JSON con:
    - denominacion: string (ej: 'Billete de $50.000 COP' o '$2.000 COP')
    - confianza: float o string (ej: 98.4 o '98.4%')
    - metodo: 'Cámara en vivo' | 'Subida de foto' | 'Captura manual'
    - usuario: string con nombre de usuario
    - latencia_ms: float (opcional)
    """
    datos = request.get_json() or {}
    denom = str(datos.get("denominacion", "")).strip()
    if not denom:
        return jsonify({"success": False, "error": "Falta el campo 'denominacion'."}), 400

    # Extraer porcentaje numérico
    conf_raw = str(datos.get("confianza", "95.0")).replace("%", "").strip()
    try:
        confianza_float = round(float(conf_raw), 2)
    except ValueError:
        confianza_float = 90.00

    metodo = datos.get("metodo", "Subida de foto")
    if metodo not in ["Subida de foto", "Cámara en vivo", "Captura manual"]:
        metodo = "Subida de foto"

    latencia = float(datos.get("latencia_ms", 0.0) or 0.0)
    usuario_nombre = str(datos.get("usuario", "")).strip()
    if not usuario_nombre or usuario_nombre.lower() in ["invitado", "null", "undefined"]:
        usuario_nombre = "Usuario"
    ip_cliente = request.remote_addr or "127.0.0.1"

    # Valor nominal numérico
    valor_nominal = datos.get("valor_nominal")
    if not valor_nominal:
        valor_nominal = extraer_valor_nominal(denom)

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            # Buscar ID de usuario si existe en la tabla usuarios
            usuario_id = None
            if usuario_nombre:
                cur.execute("SELECT id FROM usuarios WHERE nombre_usuario = %s LIMIT 1;", (usuario_nombre,))
                u_res = cur.fetchone()
                if u_res:
                    usuario_id = u_res["id"]

            # Buscar denominacion_id en el catálogo
            cur.execute("""
                SELECT id FROM denominaciones_billetes 
                WHERE valor_nominal = %s OR denominacion LIKE %s OR nombre_comun LIKE %s
                LIMIT 1;
            """, (valor_nominal, f"%{valor_nominal}%", f"%{denom}%"))
            d_res = cur.fetchone()
            denom_id = d_res["id"] if d_res else None

            # Insertar en la tabla historial_escaneos con usuario_nombre explícito
            cur.execute("""
                INSERT INTO historial_escaneos 
                (usuario_id, usuario_nombre, denominacion_id, denominacion_texto, valor_nominal, confianza_porcentaje, metodo_escaneo, latencia_ms, ip_origen, fecha_hora)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """, (usuario_id, usuario_nombre, denom_id, denom, valor_nominal, confianza_float, metodo, latencia, ip_cliente))

            nuevo_id = cur.lastrowid
        conn.close()

        ahora_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return jsonify({
            "success": True,
            "mensaje": "Escaneo registrado exitosamente en MySQL.",
            "registro": {
                "id": nuevo_id,
                "usuario": usuario_nombre,
                "denominacion": denom,
                "valor_nominal": valor_nominal,
                "valor_formato": formatear_pesos_cop(valor_nominal),
                "confianza": f"{confianza_float}%",
                "metodo": metodo,
                "fecha_hora": ahora_str,
                "time": ahora_str
            }
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error al guardar escaneo en la base de datos: {str(e)}"
        }), 500


@app.route("/api/historial/limpiar", methods=["DELETE", "POST"])
def limpiar_historial():
    """Permite reiniciar el historial si el usuario lo requiere (individual o completo)."""
    usuario = request.args.get("usuario", default="", type=str).strip()
    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            if usuario and usuario.lower() != "todos":
                cur.execute("DELETE FROM historial_escaneos WHERE usuario_nombre = %s;", (usuario,))
                msg = f"Historial del usuario '{usuario}' limpiado correctamente."
            else:
                cur.execute("TRUNCATE TABLE historial_escaneos;")
                msg = "Historial completo limpiado correctamente en MySQL."
        conn.close()
        return jsonify({"success": True, "mensaje": msg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print(" >>> MICROSERVICIO DE HISTORIAL & MÉTRICAS (VisionCash)")
    print(f" >>> Puerto: http://localhost:{PUERTO}")
    print(" >>> Base de datos: MySQL en XAMPP (192.168.0.12:3306)")
    print(" >>> Endpoints:")
    print(f"     - GET  http://localhost:{PUERTO}/api/historial/metricas (Día vs Total)")
    print(f"     - GET  http://localhost:{PUERTO}/api/historial          (Lista con fecha, hora y usuario)")
    print(f"     - POST http://localhost:{PUERTO}/api/historial          (Registrar escaneo)")
    print(f"     - GET  http://localhost:{PUERTO}/api/historial/salud    (Healthcheck)")
    print("=" * 65 + "\n")
    app.run(host="0.0.0.0", port=PUERTO, debug=False)
