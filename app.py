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
                "cbteFch": "2025-05-23",
            }
            parametros = {
                "idFactCab": 2814,
                "idFactCabRelacionado":0,
                "id_usuario": 63,

            }

            comprobante = {
            "FeCabReq": {
                "CantReg": 1,
                "PtoVta": 1,
                "CbteTipo": 6
            },
            "FeDetReq": {
                "Concepto": 1,
                "DocTipo": 96,
                "DocNro": 12345678,
                "CbteDesde": 1,
                "CbteHasta": 1,
                "CbteFch": "20250519",
                "ImpTotal": 121.0,
                "ImpTotConc": 0.0,
                "ImpNeto": 100.0,
                "ImpOpEx": 0.0,
                "ImpTrib": 7.8,
                "ImpIVA": 21.0,
                "MonId": "PES",
                "MonCotiz": 1.0,
                "CanMisMonExt": "",
                "FchServDesde": "",
                "FchServHasta": "",
                "CondicionIVAReceptorId": 4,
                "FchVtoPago": "20250610",
                "Tributos": [
                    {
                        "Id": 99,
                        "Desc": "Impuesto Municipal",
                        "BaseImp": 150.0,
                        "Alic": 5.2,
                        "Importe": 7.8
                    }
                ],
                "Iva": [
                    {
                        "Id": 5,
                        "BaseImp": 100.0,
                        "Importe": 21.0
                    }
                ],
                "CbtesAsoc": None,
                "Opcionales": None,
                "Compradores": None,
                "PeriodoAsoc": None,
                "Actividades": None
            }
        }



            try:
                # = autorizarComprobante("DBA", parametrosSybase)
                #logging.info(f"result: {autorizarSybase}")
                id_usu =parametros["id_usuario"]
                autorizar = autorizarComprobante(id_usu, parametros)
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
