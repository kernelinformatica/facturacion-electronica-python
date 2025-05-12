import logging
from flask import Flask
from flask_cors import CORS
from facturacion_router import facturacion_bp, consultarComprobanteEmitido

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
            consultarComprobante = consultarComprobanteEmitido(62)
            logging.info(f"result: {consultarComprobante}")
    except Exception as e:
        logging.error(f"Error al iniciar el servicio: {e}")
