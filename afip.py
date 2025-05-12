import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re

from conectorManagerDB import ConectorManagerDB
import zeep
from tokens import Tokens as tok
import requests
from dotenv import load_dotenv
from afipWsaaClient import AfipWsaaClient as afipClient
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Afip():
    def __init__(self):
        # Api

        # Cargar configuración desde el archivo .env
        super().__init__()
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
        self.service = os.getenv("SERVICE")
        self.signer_alias = os.getenv("SIGNER_ALIAS")
        self.dst_dn = os.getenv("DST_DN")
        self.ticket_time_seconds = int(os.getenv("TICKET_TIME_SECONDS", 3600))
        self.p12_file = os.getenv("P12_FILE")
        self.p12_password = os.getenv("P12_PASSWORD")
        self.sign = None
        self.id_usuario = 0

        # Estas dos variables definien si es homologacion o produccion y a que base se conecta
        self.plataforma = int(os.getenv("PLATAFORMA", 1))
        self.testSn = os.getenv("WS_TEST", "True")

        #
    def login(self, id_usuario):
        logging.info("----------> :: app: login() Autentica con AFIP utilizando los certificados :: <----------")

        try:
            # 🔹 Crear el NUEVO TA
            cms = afipClient.obtenerNuevoTokenAcceso(self.trust_store, self.keystore, self.endpoint_login)
            root = ET.fromstring(cms)
            if not cms:
                if "control" in cms and "mensaje" in cms:
                    return cms["mensaje"]
            else:
                # Header #
                source = root.find(".//source").text if root.find(".//source") is not None else "N/A"
                destination = root.find(".//destination").text if root.find(".//destination") is not None else "N/A"
                uniqueId = root.find(".//uniqueId").text if root.find(".//uniqueId") is not None else "N/A"
                generationTime = root.find(".//generationTime").text if root.find(
                    ".//generationTime") is not None else "N/A"
                expirationTime = root.find(".//expirationTime").text if root.find(
                    ".//expirationTime") is not None else "N/A"

                # Credenciales #
                token = root.find(".//token").text if root.find(".//token") is not None else "N/A"
                sign = root.find(".//sign").text if root.find(".//sign") is not None else "N/A"
                tok.grabarToken(self, id_usuario, source, destination, uniqueId, generationTime, expirationTime, token, sign)

        except Exception as e:
            logging.error(f"❌ Error autenticando con {self.nombre_entidad}: {str(e)}")
            return {"control": "ERROR", "mensaje": f"Error autenticando con {self.nombre_entidad}: {str(e)}"}


    def consultarComprobanteEmitido(self, id_usuario):
        # Primero consulta si el token esta activo
        logging.info(":: consultarComprobanteEmitido("+str(id_usuario)+")"+"::")
        # Valida token y genera nuevo si es necesario: con importacion diferida,
        # ver este punto con cuidado porque todos los metodos deberia implemntarlo de la misma manera
        from facturacion_router import facturacion_bp, validarToken
        tok = validarToken(id_usuario)
        # Fin importacion diferida
        if tok["token"] is not None:
            #return tok
            metodo = "FECompConsultar"
            cuit_patron = r"CUIT (\d+)"
            source = tok["source"]
            cui = re.search(cuit_patron, source)
            cuit = cui.group(1) if cui else 0
            payload = {
                "FECompConsultar": {
                    "Auth": {
                        "Token": tok["token"],
                        "Sign":tok["sign"],
                        "Cuit": cuit
                    },
                    "FeCompConsReq": [
                        {
                            "CbteTipo": 1,
                            "CbteNro": 5927,
                            "PtoVta":2

                        }
                    ]
                }
            }
            # 🔹 Imprimir con formato JSON
            print(json.dumps(payload, indent=4))
            """
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            # Enviar datos a AFIP (simulado con endpoint de prueba)
            response = requests.post(self.endpoint_fe, json=payload, headers=headers)
            if response.status_code == 200:
                logging.info("Factura enviada exitosamente a AFIP.")
                return response.json()
            else:
                raise Exception(f"Error en respuesta de AFIP: {response.status_code} - {response.text}")"""












    def enviarFactura(self, datos_factura):
        """Enviar datos de una factura a AFIP"""
        try:
            if not self.token or not self.sign:
                raise Exception("No estás autenticado. Llama al método `autenticar` primero.")

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }

            # Ejemplo de carga útil
            payload = {
                "FeCAEReq": {
                    "FeCabReq": {
                        "CantReg": 1,
                        "PtoVta": datos_factura["ptoVenta"],
                        "CbteTipo": datos_factura["tipoComprobante"]
                    },
                    "FeDetReq": [
                        {
                            "Concepto": datos_factura["concepto"],
                            "DocTipo": 80,
                            "DocNro": datos_factura["cuitEmisor"],
                            "CbteDesde": datos_factura["numeroComprobante"],
                            "CbteHasta": datos_factura["numeroComprobante"],
                            "CbteFch": datos_factura["fechaComprobante"],
                            "ImpTotal": datos_factura["importe"],
                            "MonId": datos_factura["moneda"],
                            "MonCotiz": 1.0
                        }
                    ]
                }
            }

            # Enviar datos a AFIP (simulado con endpoint de prueba)
            response = requests.post(self.endpoint_fe, json=payload, headers=headers)
            if response.status_code == 200:
                logging.info("Factura enviada exitosamente a AFIP.")
                return response.json()
            else:
                raise Exception(f"Error en respuesta de AFIP: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Error enviando factura a AFIP: {e}")
            raise Exception(f"Error enviando factura a AFIP: {e}")

    def validarConexion(self):
        """Valida la conexión con el servicio de AFIP"""
        try:
            logging.info("Validando conexión con el servicio de AFIP...")
            # Realiza una solicitud HEAD para verificar si el endpoint está accesible
            #response = requests.get(self.endpoint_dummy, timeout=5)
            client = zeep.Client(wsdl=self.endpoint_fe)
            response = client.service.FEDummy()
            if response.AppServer == "OK" and response.DbServer == "OK" and response.AuthServer == "OK" :
                msg = f"La conexión con {self.nombre_entidad} se realizó exitosamente."
                codigo = 200
                control = "OK"
            else:
                msg = f"Problema en la conexión con {self.nombre_entidad}. Servidores: {response}"
                logging.warning(msg)
                codigo = 500
                control = "ERROR"

            resp_json = {
                "control": control,
                "codigo": codigo,
                "mensaje": msg,
                "servidores": {
                    "AppServer": response.AppServer,
                    "DbServer": response.DbServer,
                    "AuthServer": response.AuthServer
                }
            }
            logging.info(json.dumps(resp_json, ensure_ascii=False,indent=4))
            return resp_json

        except requests.exceptions.RequestException as e:
            logging.error(f"Error al conectar con AFIP: {e}")
            return {"control": "ERROR", "mensaje": f"Error al conectar con AFIP: {str(e)}"}


"""if __name__ == "__main__":
    afipClient = Afip()
    resultado = afipClient.login()
    print(resultado)"""