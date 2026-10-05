"""
Script de inicialización y verificación de la base de datos MySQL en XAMPP.
Conecta a la máquina virtual (192.168.0.12:3306) y ejecuta el script visioncash_db.sql.
"""

import sys
import pymysql
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
SQL_FILE = BASE_DIR / "visioncash_db.sql"

# Configuración de conexión a XAMPP en VirtualBox
CONFIG_MYSQL = {
    "host": "192.168.0.12",
    "port": 3306,
    "user": "root",
    "password": "",
    "charset": "utf8mb4",
    "connect_timeout": 5
}

def inicializar_base_datos():
    print("=" * 60)
    print(" >>> Inicializando Base de Datos VisionCash en XAMPP (192.168.0.12)")
    print("=" * 60)

    if not SQL_FILE.exists():
        print(f"[ERROR] No se encontró el archivo SQL en: {SQL_FILE}")
        return False

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    try:
        # 1. Conectar al servidor MySQL
        print(f"[*] Conectando a MySQL en {CONFIG_MYSQL['host']}:{CONFIG_MYSQL['port']}...")
        conexion = pymysql.connect(
            host=CONFIG_MYSQL["host"],
            port=CONFIG_MYSQL["port"],
            user=CONFIG_MYSQL["user"],
            password=CONFIG_MYSQL["password"],
            charset=CONFIG_MYSQL["charset"],
            connect_timeout=CONFIG_MYSQL["connect_timeout"],
            autocommit=True
        )

        with conexion.cursor() as cursor:
            # Dividir comandos por punto y coma (manejando vistas y consultas)
            comandos = []
            buffer = []
            for linea in sql_content.splitlines():
                linea_strip = linea.strip()
                if linea_strip.startswith("--") or not linea_strip:
                    continue
                buffer.append(linea)
                if linea_strip.endswith(";"):
                    comandos.append("\n".join(buffer))
                    buffer = []

            print(f"[*] Ejecutando {len(comandos)} sentencias SQL...")
            for i, cmd in enumerate(comandos, 1):
                cmd_clean = cmd.strip()
                if cmd_clean:
                    cursor.execute(cmd_clean)

            print("[OK] Esquema y tablas creadas exitosamente.")

            # 2. Verificar datos cargados
            cursor.execute("USE visioncash_db;")
            cursor.execute("SHOW TABLES;")
            tablas = [t[0] for t in cursor.fetchall()]
            print(f"\n[+] Tablas en 'visioncash_db': {tablas}")

            # Conteo de registros
            for tabla in ["usuarios", "denominaciones_billetes", "historial_escaneos", "mesa_ayuda_tickets"]:
                cursor.execute(f"SELECT COUNT(*) FROM `{tabla}`;")
                conteo = cursor.fetchone()[0]
                print(f"    - Tabla `{tabla}`: {conteo} registros")

            # Verificación de vista de KPIs
            cursor.execute("SELECT * FROM `v_kpis_mesa_ayuda`;")
            kpis = cursor.fetchone()
            print(f"\n[+] Métricas KPI iniciales calculadas con éxito:")
            print(f"    - Total tickets: {kpis[0]}")
            print(f"    - Incidencias: {kpis[1]} | Requerimientos: {kpis[2]}")
            print(f"    - Tasa de resolución: {kpis[6]}%")
            print(f"    - Cumplimiento de SLA: {kpis[7]}%")
            print(f"    - MTTR promedio: {kpis[8]} horas")
            print(f"    - CSAT promedio: {kpis[9]} / 5.0")

        conexion.close()
        print("\n" + "=" * 60)
        print(" >>> BASE DE DATOS 'visioncash_db' LISTA EN PHPMYADMIN!")
        print(" >>> URL: http://192.168.0.12/phpmyadmin/")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] Fallo al inicializar la base de datos: {e}")
        return False

if __name__ == "__main__":
    exito = inicializar_base_datos()
    sys.exit(0 if exito else 1)
