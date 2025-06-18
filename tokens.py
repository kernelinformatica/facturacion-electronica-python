import os
from datetime import datetime

from flask import jsonify

from dotenv import load_dotenv
import logging
from conectorManagerDB import ConectorManagerDB
load_dotenv()
class Tokens():
    def __init__(self):
        super().__init__()  # 🔹 Inicializa la conexión a la base de datos correctamente

        # Cargar configuración desde el archivo .env
        self.nombre_entidad = os.getenv("NOMBRE_ENTIDAD_CONTROLADORA")
        self.endpoint_login = os.getenv("END_POINT_LOGIN")
        self.endpoint_dummy = os.getenv("END_POINT_DUMMY")
        self.endpoint_fe = os.getenv("END_POINT_FE")
        self.keystore = os.getenv("KEYSTORE")
        self.trust_store = os.getenv("TRUST_STORE")
        self.trust_store_password = os.getenv("TRUST_STORE_PASSWORD")
        self.keystore_password = os.getenv("KEYSTORE_PASSWORD")
        self.service = os.getenv("SERVICE")
        self.cuit = os.getenv("CUIT")
        self.signer_alias = os.getenv("SIGNER_ALIAS")
        self.dst_dn = os.getenv("DST_DN")
        self.ticket_time_seconds = int(os.getenv("TICKET_TIME_SECONDS", 3600))
        self.p12_file = os.getenv("P12_FILE")
        self.p12_password = os.getenv("P12_PASSWORD")
        self.token = None
        self.sign = None
        self.plataforma = int(os.getenv("PLATAFORMA", 1))
        self.testSn = os.getenv("WS_TEST", "True")


    import logging

    def buscarTokenVigente(self, id_usuario):
        logging.info("----------> :: Buscar Token Vigente :: <----------")
        try:
            # 🔹 Ejecutar la consulta con un `with` para cerrar el cursor automáticamente
            manager = ConectorManagerDB(self.plataforma)
            db = manager.get_connection()
            if self.testSn == "True":
                homo = 'S'
            else:
                homo = 'N'
            if self.plataforma == 1:

                with db.conn.cursor() as cursor:
                    query = """SELECT uid, token, sign, source, destination, testSN  
                               FROM AfipWsaaTa WHERE idUsuario = %s  and TestSN = %s AND activo = 'S'
                               AND expTime >= NOW()"""  # 🔹
                    cursor.execute(query, (id_usuario, homo))
                    rows = cursor.fetchone()
            elif self.plataforma == 2:
                with db.conn.cursor() as cursor:
                    query = "SELECT uid, token, sign, source, destination, testSN FROM afipws_fe_wsaa_TA WHERE operador_codigo = '"+str(id_usuario)+"' AND  TestSN = '"+str(homo)+"' and activo = 'S' AND expTime >= NOW()"
                    cursor.execute(query)
                    rows = cursor.fetchone()
            else:
                return {
                    "control": "ERROR",
                    "codigo": 404,
                    "mensaje": "Plataforma "+str(self.plataforma)+", no soportada",
                    "datos": []
                }




            # 🔹 Verificar si hay datos en la respuesta
            if rows is None:
                return {
                    "control": "ERROR",
                    "codigo": 404,
                    "mensaje": "Token no encontrado",
                    "datos": []
                }
            else:

                # 🔹 Estructurar la respuesta JSON con los datos obtenidos
                return {
                    "control": "OK",
                    "codigo": 200,
                    "mensaje": "Token encontrado",
                    "datos": [
                        {
                            "uid": rows[0],
                            "token": rows[1],
                            "sign": rows[2],
                            "source": rows[3],
                            "destination": rows[4],
                            "testSN": rows[5] if rows[5] is not None else "N/A"  # 🔹 Evita `None`
                        }
                    ]
                }

        except Exception as e:
            logging.error(f"Error al buscar el token vigente: {str(e)}")
            return {
                "control": "ERROR",
                "codigo": 500,
                "mensaje": f"Error interno al consultar el token: {str(e)}"
            }

    def grabarToken(self, id_usuario, source, destination, uniqueId, generationTime, expirationTime, token, sign):
        """🔹 Graba el token y sign en la tabla AfipWsaaTa."""
        logging.info("::: Graba el token y sign en la tabla AfipWsaaTa. :::")
        try:
            # Crear una instancia de la conexión a la base de datos
            plataforma = self.plataforma
            manager = ConectorManagerDB(plataforma)
            db_connection = manager.get_connection()
            testSn = self.testSn
            if testSn == "True":
                homo = "S"
            else:
                homo = "N"
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
                query_check = "SELECT COUNT(*) FROM AfipWsaaTa WHERE uid = %s and testSn = %s "
                cursor.execute(query_check, (uniqueId, homo))
                resultado = cursor.fetchone()  # Leer el resultado de la consulta
                existe = resultado[0] if resultado else 0

                # 🔹 Si el registro existe, eliminarlo antes de insertar
                if existe > 0:
                    cursor.execute("DELETE FROM AfipWsaaTa WHERE uid = %s and testSn = %s", (uniqueId, homo))
                    logging.warning(f"⚠ Token existente con UID {uniqueId}, eliminado antes de insertar.")

                # 🔹 Formatear fechas correctamente para MySQL
                genTime_f = datetime.strptime(generationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                expTime_f = datetime.strptime(expirationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

                # 🔹 Insertar nuevo token
                query_insert = """
                INSERT INTO AfipWsaaTa (uid, genTime, expTime, token, sign, source, destination, idUsuario, activo, testSN, ultActualizacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                values = (uniqueId, genTime_f, expTime_f, token, sign, source, destination, id_usuario, activo, homo)
                cursor.execute(query_insert, values)

                # Confirmar los cambios
                db_connection.conn.commit()
                logging.info("✅ Token y sign grabados en la tabla AfipWsaaTa correctamente.")
                logging.info(f"Token: {token}, Sign: {sign}")
            elif plataforma == 2:
                # Sybase
                logging.info(":: Conexión a Sybase ::")

                # Verificar si el token ya existe
                query_check = "SELECT COUNT(*) FROM afipws_fe_wsaa_TA WHERE uid = " + uniqueId + " and TestSN = '"+str(homo)+"'"
                cursor.execute(query_check)
                resultado = cursor.fetchone()  # Leer el resultado de la consulta
                existe = resultado[0] if resultado else 0

                # Si el registro existe, eliminarlo antes de insertar
                if existe > 0:
                    cursor.execute("DELETE FROM afipws_fe_wsaa_TA WHERE uid = " + uniqueId + " and TestSN = "+str(homo)+" ")
                    logging.warning(f"⚠ Token existente con UID {uniqueId}, eliminado antes de insertar.")

                genTime_f = datetime.strptime(generationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                expTime_f = datetime.strptime(expirationTime[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

                query_insert = "INSERT INTO afipws_fe_wsaa_TA (uid, genTime, expTime, token, sign, source, destination, operador_codigo, activo, testSN, ultActualizacion) VALUES (" + uniqueId + ", '" + str(
                    genTime_f) + "', '" + str(expTime_f) + "', '" + str(token) + "', '" + str(sign) + "', '" + str(
                    source) + "', '" + str(destination) + "', '" + str(id_usuario) + "', '" + str(
                    activo) + "', '" + str(homo) + "', NOW())"

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









