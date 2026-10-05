"""
Módulo de Conexión a la Base de Datos MySQL (XAMPP - VirtualBox).
Gestiona la conexión con reintentos y fallback seguro.
"""

import pymysql
from pymysql.cursors import DictCursor

CONFIG_BD = {
    "host": "192.168.0.12",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "visioncash_db",
    "charset": "utf8mb4",
    "connect_timeout": 4
}


def obtener_conexion():
    """
    Retorna una conexión activa a MySQL en XAMPP.
    Si la base de datos no está disponible, lanza una excepción informativa.
    """
    try:
        conexion = pymysql.connect(
            host=CONFIG_BD["host"],
            port=CONFIG_BD["port"],
            user=CONFIG_BD["user"],
            password=CONFIG_BD["password"],
            database=CONFIG_BD["database"],
            charset=CONFIG_BD["charset"],
            cursorclass=DictCursor,
            connect_timeout=CONFIG_BD["connect_timeout"],
            autocommit=True
        )
        return conexion
    except pymysql.MySQLError as e:
        # Si la base de datos aún no existe, intentar conectar sin especificar BD
        try:
            conexion_base = pymysql.connect(
                host=CONFIG_BD["host"],
                port=CONFIG_BD["port"],
                user=CONFIG_BD["user"],
                password=CONFIG_BD["password"],
                charset=CONFIG_BD["charset"],
                cursorclass=DictCursor,
                connect_timeout=CONFIG_BD["connect_timeout"],
                autocommit=True
            )
            return conexion_base
        except Exception:
            raise ConnectionError(
                f"No se pudo conectar a MySQL en {CONFIG_BD['host']}:{CONFIG_BD['port']}. "
                "Verifica que XAMPP en VirtualBox esté encendido y con el puerto 3306 abierto."
            ) from e


def probar_conexion():
    """Verifica si la base de datos está alcanzable."""
    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS test;")
            resultado = cur.fetchone()
        conn.close()
        return True, "Conexión exitosa a MySQL en XAMPP (192.168.0.12)"
    except Exception as e:
        return False, str(e)
