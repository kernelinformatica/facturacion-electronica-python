import json
import logging
from flask import Flask
from flask_cors import CORS
from facturacion_router import facturacion_bp, dummy, consultarComprobanteEmitido, consultarPtosVentas, consultarUltimoCbteAutorizado, autorizarComprobante

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AppFacturacionElectronica():
    def __init__(self):
        super().__init__()
        self.app = Flask(__name__)
        CORS(self.app)
        self.app.register_blueprint(facturacion_bp, url_prefix='/api')

    def run(self, debug=True, host="0.0.0.0", port=5000):
        self.app.run(debug=True, host=host, port=port)

# **🚀 Ejecutar el servidor Flask**
"""
if __name__ == "__main__":
    facturacionApp = AppFacturacionElectronica()
    try:
        with facturacionApp.app.app_context():
            facturacionApp.run(debug=True, port=5050)
    except Exception as e:
        logging.error(f"Error al iniciar el servicio: {e}")
"""
if __name__ == "__main__":
    facturacionApp = AppFacturacionElectronica()

    try:
        with facturacionApp.app.test_request_context():  # 🔹 Simula un request con headers
            parametrosSybase = {
                "cbteTipo": 1,
                "cbteNro": 1,
                "cbtePtoVta": 1,
                "cbteFch": "2025-05-28",
            }


            parametros = {
                "idFactCab": 2814,
                "idFactCabRelacionado":0,
                "cbtePtoVta" : 1,
                "cbteTipo" :1,
                "cbteFch": "2025-05-28",
            }

            # Convertir el string JSON en un diccionario Python



            try:
                # = autorizarComprobante("DBA", parametrosSybase)
                #logging.info(f"result: {autorizarSybase}")

                autorizar = autorizarComprobante(63, parametros)
                #logging.info(f"result: {autorizar}")

                #consultarUltimoAutorizado = consultarUltimoCbteAutorizado(62, 2, 1)
                #logging.info(f"result: {consultarUltimoAutorizado}")
            except Exception as e:
                logging.error(f"Error general: {e}")
            #consultarUltimoAutorizado = consultarUltimoCbteAutorizado(62, 2, 1)
            #print(int(consultarUltimoAutorizado["CbteNro"])+1)
            #logging.info(f"result: {consultarUltimoAutorizado["CbteNro"]}")

            #dummy = dummy()
            #ogging.info(f"result: {dummy}")
    except Exception as e:
        logging.error(f"Error al iniciar el servicio: {e}")
