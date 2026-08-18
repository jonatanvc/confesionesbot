import sqlite3
import os
from threading import Lock
from datetime import datetime, timedelta
from config import USE_POSTGRES, DB_FILE, DB_DIR, DATABASE_URL

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    import socket

lock = Lock()

def get_connection():
    """Devuelve conexión a PostgreSQL o SQLite según configuración"""
    if USE_POSTGRES:
        try:
            return psycopg2.connect(DATABASE_URL)
        except Exception:
            old_getaddrinfo = socket.getaddrinfo
            def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
                return old_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
            socket.getaddrinfo = getaddrinfo_ipv4
            try:
                conn = psycopg2.connect(DATABASE_URL)
                return conn
            finally:
                socket.getaddrinfo = old_getaddrinfo
    else:
        os.makedirs(DB_DIR, exist_ok=True)
        return sqlite3.connect(DB_FILE)

def init_db():
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if USE_POSTGRES:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id BIGINT PRIMARY KEY,
                        username TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS confesiones (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        fecha TIMESTAMP,
                        confesion TEXT,
                        estado TEXT,
                        tipo TEXT,
                        file_id TEXT,
                        poll_options TEXT,
                        extra TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS advertencias (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        razon TEXT,
                        fecha TIMESTAMP,
                        admin_id BIGINT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usuarios_baneados (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        razon TEXT,
                        fecha_ban TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS appeals (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        confesion_id INTEGER,
                        razon TEXT,
                        fecha TIMESTAMP,
                        estado TEXT DEFAULT 'pendiente',
                        admin_id BIGINT,
                        nota_admin TEXT
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY,
                        username TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS confesiones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        fecha TEXT,
                        confesion TEXT,
                        estado TEXT,
                        tipo TEXT,
                        file_id TEXT,
                        poll_options TEXT,
                        extra TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS advertencias (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        razon TEXT,
                        fecha TEXT,
                        admin_id INTEGER
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usuarios_baneados (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        razon TEXT,
                        fecha_ban TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS appeals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        confesion_id INTEGER,
                        razon TEXT,
                        fecha TEXT,
                        estado TEXT DEFAULT 'pendiente',
                        admin_id INTEGER,
                        nota_admin TEXT
                    )
                """)
            conn.commit()
        finally:
            conn.close()

def execute_query(query, params=(), fetchone=False, fetchall=False, returning_id=False):
    """Helper para ejecutar queries de forma segura cerrando siempre la conexión"""
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if not USE_POSTGRES:
                query = query.replace('%s', '?').replace('RETURNING id', '')

            cursor.execute(query, params)
            result = None
            if returning_id:
                if USE_POSTGRES:
                    row = cursor.fetchone()
                    result = row[0] if row else None
                else:
                    result = cursor.lastrowid
            elif fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()

            conn.commit()
            return result
        finally:
            conn.close()

def registrar_usuario(user_id, username):
    if USE_POSTGRES:
        query = """
            INSERT INTO usuarios(id, username) VALUES(%s, %s)
            ON CONFLICT (id) DO UPDATE SET username = EXCLUDED.username
        """
    else:
        query = "INSERT OR REPLACE INTO usuarios(id, username) VALUES(?, ?)"
    execute_query(query, (user_id, username))

def obtener_user_id_por_username(username):
    username = username.lstrip('@')
    placeholder = '%s' if USE_POSTGRES else '?'
    result = execute_query(f"SELECT id FROM usuarios WHERE LOWER(username) = LOWER({placeholder})", (username,), fetchone=True)
    return result[0] if result else None

def obtener_username_por_user_id(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    result = execute_query(f"SELECT username FROM usuarios WHERE id={placeholder}", (user_id,), fetchone=True)
    return result[0] if result else None

def guardar_confesion(user_id, username, fecha, confesion, estado):
    if USE_POSTGRES:
        query = """
            INSERT INTO confesiones(user_id, username, fecha, confesion, estado, tipo, file_id, extra)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """
    else:
        query = """
            INSERT INTO confesiones(user_id, username, fecha, confesion, estado, tipo, file_id, extra)
            VALUES(?,?,?,?,?,?,?,?)
        """
    return execute_query(query, (user_id, username, fecha, confesion, estado, 'text', None, None), returning_id=True)

def guardar_confesion_media(user_id, username, fecha, estado, tipo, file_id, confesion, extra=None):
    if USE_POSTGRES:
        query = """
            INSERT INTO confesiones(user_id, username, fecha, confesion, estado, tipo, file_id, extra)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """
    else:
        query = """
            INSERT INTO confesiones(user_id, username, fecha, confesion, estado, tipo, file_id, extra)
            VALUES(?,?,?,?,?,?,?,?)
        """
    return execute_query(query, (user_id, username, fecha, confesion, estado, tipo, file_id, extra), returning_id=True)

def actualizar_estado_confesion(conf_id, nuevo_estado, motivo=None):
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            placeholder = '%s' if USE_POSTGRES else '?'
            if motivo:
                cursor.execute(f"UPDATE confesiones SET estado={placeholder}, extra={placeholder} WHERE id={placeholder}", (nuevo_estado, motivo, conf_id))
            else:
                cursor.execute(f"UPDATE confesiones SET estado={placeholder} WHERE id={placeholder}", (nuevo_estado, conf_id))
            conn.commit()
            cursor.execute(f"SELECT id, user_id, username, fecha, confesion, estado, tipo, file_id, extra FROM confesiones WHERE id={placeholder}", (conf_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "username": row[2],
                    "fecha": str(row[3]),
                    "confesion": row[4],
                    "estado": row[5],
                    "tipo": row[6],
                    "file_id": row[7],
                    "extra": row[8]
                }
            return None
        finally:
            conn.close()

def obtener_confesiones_usuario(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    rows = execute_query(f"SELECT id, fecha, confesion, estado, tipo, file_id FROM confesiones WHERE user_id={placeholder} ORDER BY id DESC LIMIT 10", (user_id,), fetchall=True)
    return [{"id": r[0], "fecha": str(r[1]), "confesion": r[2], "estado": r[3], "tipo": r[4], "file_id": r[5]} for r in rows]

def contar_confesiones_usuario(user_id):
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            placeholder = '%s' if USE_POSTGRES else '?'
            cursor.execute(f"SELECT COUNT(*) FROM confesiones WHERE user_id={placeholder}", (user_id,))
            total = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM confesiones WHERE user_id={placeholder} AND estado='pendiente'", (user_id,))
            pendientes = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM confesiones WHERE user_id={placeholder} AND estado='aceptada'", (user_id,))
            aceptadas = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM confesiones WHERE user_id={placeholder} AND estado='rechazada'", (user_id,))
            rechazadas = cursor.fetchone()[0]
            return {"total": total, "pendientes": pendientes, "aceptadas": aceptadas, "rechazadas": rechazadas}
        finally:
            conn.close()

def contar_confesiones_por_tipo():
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(tipo, 'text') as t, COUNT(*) FROM confesiones GROUP BY t")
            data = cursor.fetchall()
            result = {"text": 0, "photo": 0, "poll": 0}
            for t, c in data:
                result[t] = c
            return result
        finally:
            conn.close()

def contar_confesiones():
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM confesiones")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM confesiones WHERE estado='pendiente'")
            pendientes = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM confesiones WHERE estado='aceptada'")
            aceptadas = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM confesiones WHERE estado='rechazada'")
            rechazadas = cursor.fetchone()[0]
            return {"total": total, "pendientes": pendientes, "aceptadas": aceptadas, "rechazadas": rechazadas}
        finally:
            conn.close()

def obtener_todos_usuarios():
    rows = execute_query("SELECT id FROM usuarios", fetchall=True)
    return [r[0] for r in rows]

def contar_usuarios():
    result = execute_query("SELECT COUNT(*) FROM usuarios", fetchone=True)
    return result[0] if result else 0

def limpiar_confesiones_antiguas(dias: int):
    limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            placeholder = '%s' if USE_POSTGRES else '?'
            if USE_POSTGRES:
                cursor.execute(f"DELETE FROM confesiones WHERE fecha < {placeholder}::timestamp", (limite,))
            else:
                cursor.execute(f"DELETE FROM confesiones WHERE fecha < {placeholder}", (limite,))
            rowcount = cursor.rowcount
            conn.commit()
            return rowcount
        finally:
            conn.close()

def agregar_advertencia(user_id, username, razon, admin_id):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if USE_POSTGRES:
        query = "INSERT INTO advertencias(user_id, username, razon, fecha, admin_id) VALUES(%s,%s,%s,%s,%s) RETURNING id"
    else:
        query = "INSERT INTO advertencias(user_id, username, razon, fecha, admin_id) VALUES(?,?,?,?,?)"
    return execute_query(query, (user_id, username, razon, fecha, admin_id), returning_id=True)

def obtener_advertencias_usuario(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    return execute_query(f"SELECT id, razon, fecha FROM advertencias WHERE user_id={placeholder} ORDER BY fecha DESC", (user_id,), fetchall=True)

def contar_advertencias_usuario(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    result = execute_query(f"SELECT COUNT(*) FROM advertencias WHERE user_id={placeholder}", (user_id,), fetchone=True)
    return result[0] if result else 0

def banear_usuario(user_id, username, razon):
    fecha_ban = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if USE_POSTGRES:
        query = """
            INSERT INTO usuarios_baneados(user_id, username, razon, fecha_ban) VALUES(%s,%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, razon = EXCLUDED.razon, fecha_ban = EXCLUDED.fecha_ban
        """
    else:
        query = "INSERT OR REPLACE INTO usuarios_baneados(user_id, username, razon, fecha_ban) VALUES(?,?,?,?)"
    execute_query(query, (user_id, username, razon, fecha_ban))

def usuario_esta_baneado(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    result = execute_query(f"SELECT user_id FROM usuarios_baneados WHERE user_id={placeholder}", (user_id,), fetchone=True)
    return result is not None

def obtener_razon_ban(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    result = execute_query(f"SELECT razon FROM usuarios_baneados WHERE user_id={placeholder}", (user_id,), fetchone=True)
    return result[0] if result else None

def desbanear_usuario(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    execute_query(f"DELETE FROM usuarios_baneados WHERE user_id={placeholder}", (user_id,))

def limpiar_advertencias_usuario(user_id):
    placeholder = '%s' if USE_POSTGRES else '?'
    execute_query(f"DELETE FROM advertencias WHERE user_id={placeholder}", (user_id,))

def crear_appeal(user_id, username, confesion_id, razon):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if USE_POSTGRES:
        query = "INSERT INTO appeals(user_id, username, confesion_id, razon, fecha, estado) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id"
    else:
        query = "INSERT INTO appeals(user_id, username, confesion_id, razon, fecha, estado) VALUES(?,?,?,?,?,?)"
    return execute_query(query, (user_id, username, confesion_id, razon, fecha, 'pendiente'), returning_id=True)

def obtener_appeals_pendientes():
    rows = execute_query("SELECT id, user_id, username, confesion_id, razon, fecha FROM appeals WHERE estado='pendiente' ORDER BY fecha ASC", fetchall=True)
    return [{"id": r[0], "user_id": r[1], "username": r[2], "confesion_id": r[3], "razon": r[4], "fecha": str(r[5])} for r in rows]

def resolver_appeal(appeal_id, admin_id, decision, nota_admin=None):
    estado = 'aceptada' if decision == 'aceptar' else 'rechazada'
    with lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            placeholder = '%s' if USE_POSTGRES else '?'
            cursor.execute(f"UPDATE appeals SET estado={placeholder}, admin_id={placeholder}, nota_admin={placeholder} WHERE id={placeholder}",
                          (estado, admin_id, nota_admin, appeal_id))
            rowcount = cursor.rowcount
            conn.commit()
            return rowcount
        finally:
            conn.close()
