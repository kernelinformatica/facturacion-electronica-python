import os
import unittest
import xml.etree.ElementTree as ET
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import jsonify

from conectorManagerDB import ConectorManagerDB
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
import config
# Cargar variables de entorno desde el archivo .env

load_dotenv()

class TestWSAA(unittest.TestCase, ConectorManagerDB):
    def __init__(self, methodName: str = "runTest"):
        super().__init__(methodName)


    def setUp(self):
        """🔹 Configura datos de prueba antes de ejecutar cada test."""
        self.cms_valido = """<loginTicketResponse version="1.0">
    <header>
        <source>CN=wsaa, O=AFIP, C=AR, SERIALNUMBER=CUIT 33693450239</source>
        <destination>C=ar, O=kernel informatica coop de trabajo ltda, SERIALNUMBER=CUIT 30711536813, CN=kernel</destination>
        <uniqueId>1836546849</uniqueId>
        <generationTime>2025-05-08T14:35:23.974-03:00</generationTime>
        <expirationTime>2025-05-09T02:35:23.974-03:00</expirationTime>
    </header>
    <credentials>
        <token>PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9InllcyI/Pgo8c3NvIHZlcnNpb249IjIuMCI+CiAgICA8aWQgc3JjPSJDTj13c2FhLCBPPUFGSVAsIEM9QVIsIFNFUklBTE5VTUJFUj1DVUlUIDMzNjkzNDUwMjM5IiBkc3Q9IkNOPXdzZmUsIE89QUZJUCwgQz1BUiIgdW5pcXVlX2lkPSIzNTk5ODA3NzQiIGdlbl90aW1lPSIxNzQ2NzI1NjYzIiBleHBfdGltZT0iMTc0Njc2ODkyMyIvPgogICAgPG9wZXJhdGlvbiB0eXBlPSJsb2dpbiIgdmFsdWU9ImdyYW50ZWQiPgogICAgICAgIDxsb2dpbiBlbnRpdHk9IjMzNjkzNDUwMjM5IiBzZXJ2aWNlPSJ3c2ZlIiB1aWQ9IkM9YXIsIE89a2VybmVsIGluZm9ybWF0aWNhIGNvb3AgZGUgdHJhYmFqbyBsdGRhLCBTRVJJQUxOVU1CRVI9Q1VJVCAzMDcxMTUzNjgxMywgQ049a2VybmVsIiBhdXRobWV0aG9kPSJjbXMiIHJlZ21ldGhvZD0iMjIiPgogICAgICAgICAgICA8cmVsYXRpb25zPgogICAgICAgICAgICAgICAgPHJlbGF0aW9uIGtleT0iMzA3MTE1MzY4MTMiIHJlbHR5cGU9IjQiLz4KICAgICAgICAgICAgPC9yZWxhdGlvbnM+CiAgICAgICAgPC9sb2dpbj4KICAgIDwvb3BlcmF0aW9uPgo8L3Nzbz4K</token>
        <sign>bLmHQqtqsH5YKIfIboRDt6TOZp/OyYX0V8EM0w1ANJzyRxeuEJvVUPHOL2xl90Zz/ZMiXU8YxuMpyWRBPN5HmN4w59dyBw74BbiWAaBbQvTPEbJX0MJE9x5cgM7rCc1Kka0uRKerTq11tkfFW3aDrzWKpEjNpQavQt6tmyTwjWA=</sign>
    </credentials>
</loginTicketResponse>
"""

        self.cms_error = {"control": "ERROR", "mensaje": "Error de WSAA"}

    def test_extraer_token_y_sign(self):
        """🔹 Verifica que el token y sign se extraigan correctamente."""
        root = ET.fromstring(self.cms_valido)
        # Header #
        source = root.find(".//source").text if root.find(".//source") is not None else "N/A"
        destination = root.find(".//destination").text if root.find(".//destination") is not None else "N/A"
        uniqueId = root.find(".//uniqueId").text if root.find(".//uniqueId") is not None else "N/A"
        generationTime = root.find(".//generationTime").text if root.find(".//generationTime") is not None else "N/A"
        expirationTime = root.find(".//expirationTime").text if root.find(".//expirationTime") is not None else "N/A"


        # Credenciales #
        token = root.find(".//token").text if root.find(".//token") is not None else "N/A"
        sign = root.find(".//sign").text if root.find(".//sign") is not None else "N/A"
        # Verifica que los valores extraídos no sean "N/A"
        self.assertNotEqual(source, "N/A")
        self.assertNotEqual(destination, "N/A")
        self.assertNotEqual(uniqueId, "N/A")
        self.assertNotEqual(generationTime, "N/A")
        self.assertNotEqual(expirationTime, "N/A")
        self.assertNotEqual(token, "N/A")
        self.assertNotEqual(sign, "N/A")
        self.grabarToken(62, source, destination, uniqueId, generationTime, expirationTime, token, sign)




        #self.assertEqual(token, "TEST-TOKEN-123")
        #self.assertEqual(sign, "TEST-SIGN-456")

    import logging
    from datetime import datetime

    def grabarToken(self, id_usuario, source, destination, uniqueId, generationTime, expirationTime, token, sign):
        """🔹 Graba el token y sign en la tabla AfipWsaaTa."""
        try:
            # Crear una instancia de la conexión a la base de datos
            plataforma = int(os.getenv("PLATAFORMA", 1))
            manager = ConectorManagerDB(plataforma)
            db_connection = manager.get_connection()
            _testSn = os.getenv("WS_TEST", "True")
            if _testSn == True:
                testSn = "S"
            else:
                testSn = "N"
            activo = "S"
            
            # Verificar si la conexión es válida
            if db_connection.conn is None:
                logging.error("❌ No se pudo establecer la conexión con la base de datos.")
                return {"control": "ERROR", "mensaje": "Error de conexión con la base de datos."}

            # Crear un cursor para ejecutar las consultas
            cursor = db_connection.conn.cursor()

            # 🔹 Verificar si el token ya existe
            # Esto es para la conección web (mysql)
            if plataforma == 1:
                query_check = "SELECT COUNT(*) FROM AfipWsaaTa WHERE uid = %s"
                cursor.execute(query_check, (uniqueId,))
                resultado = cursor.fetchone()  # Leer el resultado de la consulta
                existe = resultado[0] if resultado else 0

                # 🔹 Si el registro existe, eliminarlo antes de insertar
                if existe > 0:
                    cursor.execute("DELETE FROM AfipWsaaTa WHERE uid = %s", (uniqueId,))
                    logging.warning(f"⚠ Token existente con UID {uniqueId}, eliminado antes de insertar.")

                # 🔹 Formatear fechas correctamente para MySQL
                genTime_f = datetime.strptime(generationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                expTime_f = datetime.strptime(expirationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

                # 🔹 Insertar nuevo token
                query_insert = """
                INSERT INTO AfipWsaaTa (uid, genTime, expTime, token, sign, source, destination, idUsuario, activo, testSN, ultActualizacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                values = (uniqueId, genTime_f, expTime_f, token, sign, source, destination, id_usuario, activo, testSn)
                cursor.execute(query_insert, values)

                # Confirmar los cambios
                db_connection.conn.commit()
                #return jsonify({"control": "OK", "mensaje": "Token y sign grabados en la tabla AfipWsaaTa correctamente.", "token": str(token)+", sign:"+str(sign) }), 200
                logging.info("✅ Token y sign grabados en la tabla AfipWsaaTa correctamente.")
                logging.info(f"Token: {token}, Sign: {sign}")
            elif plataforma == 2 :
                # Sybase
                logging.info(":: Conexión a Sybase ::")

                # Verificar si el token ya existe
                query_check = "SELECT COUNT(*) FROM afipws_fe_wsaa_TA WHERE uid = "+uniqueId+""
                cursor.execute(query_check)
                resultado = cursor.fetchone()  # Leer el resultado de la consulta
                existe = resultado[0] if resultado else 0

                # Si el registro existe, eliminarlo antes de insertar
                if existe > 0:
                    cursor.execute("DELETE FROM afipws_fe_wsaa_TA WHERE uid = "+uniqueId+"")
                    logging.warning(f"⚠ Token existente con UID {uniqueId}, eliminado antes de insertar.")


                genTime_f = datetime.strptime(generationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                expTime_f = datetime.strptime(expirationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

                query_insert = "INSERT INTO afipws_fe_wsaa_TA (uid, genTime, expTime, token, sign, source, destination, operador_codigo, activo, testSN, ultActualizacion) VALUES ("+uniqueId+", '"+str(genTime_f)+"', '"+str(expTime_f)+"', '"+str(token)+"', '"+str(sign)+"', '"+str(source)+"', '"+str(destination)+"', '"+str(id_usuario)+"', '"+str(activo)+"', '"+str(testSn)+"', NOW())"

                cursor.execute(query_insert)

              
                db_connection.conn.commit()
                logging.info("✅ Token y sign grabados en la tabla afipws_fe_wsaa_TA correctamente.")
                logging.info(f"Token: {token}, Sign: {sign}")
            else:
                logging.error(":: Plataforma no soportada ::")


        except Exception as e:
            logging.error(f"⚠ Excepción al grabar el token y sign: {str(e)}")
        finally:
            # Cerrar el cursor y la conexión
            if cursor:
                cursor.close()
            db_connection.close_connection()

    def test_manejo_error_wsaa(self):
        """🔹 Verifica que se maneje correctamente un error WSAA."""
        cms = self.cms_error

        if isinstance(cms, dict) and "control" in cms:
            if cms["control"] == "ERROR":
                resultado = {"control": "ERROR", "codigo": "404", "mensaje": cms['mensaje']}
            else:
                resultado = {"control": "OK", "mensaje": "Autenticación exitosa"}

        self.assertEqual(resultado["control"], "ERROR")
        self.assertEqual(resultado["codigo"], "404")
        self.assertEqual(resultado["mensaje"], "Error de WSAA")


# 🔹 Ejecutar pruebas si el archivo se ejecuta directamente
if __name__ == "__main__":
    unittest.main()
