import mysql.connector
from mysql.connector import Error

try:
    print("🟢 Intentando conectar...")
    conn = mysql.connector.connect(
        host="10.0.0.33",
        database="dbFacturacion_20250122",
        user="root",
        password="root",
        port="3306"
    )
    if conn.is_connected():
        print("✅ Conexión establecida con éxito")
    else:
        print("⚠️ La conexión no se pudo establecer.")
except Error as e:
    print(f"❌ Error de conexión: {e}")
except Exception as ex:
    print(f"⚠️ Error inesperado: {ex}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
        print("🔴 Conexión cerrada correctamente.")