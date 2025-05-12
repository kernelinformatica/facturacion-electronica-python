from flask import Blueprint, request, jsonify
import logging
from tokens import Tokens as Tokens
import config
from afip import Afip as wsfe
facturacion_bp = Blueprint('facturacion', __name__)
from afip import Afip as ConexionAFIP
conexion_afip = ConexionAFIP()
wsfe_instance = wsfe()

# **🔹 Autorizar factura electrónica**
@facturacion_bp.route('/autorizarFactura', methods=['POST'])
def autorizarFactura():
    try:
        token = request.headers.get("token")
        json_body = request.get_json()

        if not token:
            return jsonify({"control": "ERROR", "mensaje": "Token vacío"}), 400
        if not json_body:
            return jsonify({"control": "ERROR", "mensaje": "Cuerpo de la solicitud vacío"}), 400

        id_factura = json_body.get("idFactura")
        if not id_factura:
            return jsonify({"control": "ERROR", "mensaje": "ID de factura no proporcionado"}), 400

        # Autenticación con AFIP
        conexion_afip.autenticar()

        # Procesar la factura
        resultado = wsfe_instance.procesarFactura(id_factura)
        if not resultado:
            return jsonify({"control": "ERROR", "mensaje": f"Factura con ID {id_factura} no encontrada"}), 404

        # Enviar datos a AFIP
        resultado = conexion_afip.enviarFactura(resultado)
        return jsonify({"control": "OK", "resultado": resultado}), 200
    except Exception as e:
        logging.error(f"Error en autorizarFactura: {e}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500

# **🔹 Validar conexión con AFIP**
@facturacion_bp.route('/validarConexion', methods=['GET'])
def validarConexionConArca():
    try:
        print("Validando conexión con AFIP...")
        response = conexion_afip.validarConexion()
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error en validarConexionEndpoint: {e}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500



# **🔹 Obtener autenticación con AFIP**
@facturacion_bp.route('/obtenerAutenticacion', methods=['post'])
def getLogin(id_usuario):

    try:

        # Parametros por post

        """logging.info("Iniciando validación de conexión con AFIP...")
        if not request.is_json:
            return jsonify({"control": "ERROR", "mensaje": "El request no contiene JSON válido"}), 400
      
        data = request.get_json()
        if not data:
            return jsonify({"control": "ERROR", "mensaje": "El cuerpo de la solicitud está vacío"}), 400
"""

        if not id_usuario:
            return jsonify({"control": "ERROR", "mensaje": "Usuario no proporcionado"}), 400


        # BUSCO SI TIENE UN TOKEN VALIDO O VIGENTE
        tok = Tokens()
        tokenResponse = tok.buscarTokenVigente(id_usuario)
        if tokenResponse["codigo"] == 200:
            for item in tokenResponse["datos"]:
             return  tokenResponse, tokenResponse["codigo"]
        else:
            logging.info(":: Token no vigente, generando nuevo token...")
            # Generar un nuevo token
            resp = conexion_afip.login(id_usuario)
            if resp["codigo"] == 200:
                return resp, resp["codigo"]
                logging.info(":: Autenticación exitosa con AFIP. ::")
            else:
                return jsonify(resp), 404
                logging.info(":: Algo salio mál:  " +str(resp)+"::")


    except Exception as e:
        # Manejo de errores
        logging.error(f"Error en obtenerAutenticacion: {str(e)}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500





@facturacion_bp.route('/consultarCoprobanteEmitido', methods=['post'])
def consultarComprobanteEmitido(id_usuario):
    try:
        if not id_usuario:
            return jsonify({"control": "ERROR", "mensaje": "ID de usuario no proporcionado"}), 400

        # Consultar el comprobante emitido
        response = wsfe_instance.consultarComprobanteEmitido(id_usuario)
        return response
    except Exception as e:
        logging.error(f"Error en consultarComprobanteEmitido: {e}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500








# metodos sin router
def validarToken(id_usuario):
    try:
        # Obtener el token vigente de la base de datos
        tokenResponse = getLogin(id_usuario)
        if tokenResponse[0]["codigo"] == 200:
            for token in tokenResponse[0]["datos"]:
                return token
        else:
           raise Exception("No se encontró un token vigente.")
           return None

    except Exception as e:
        logging.error(f"Error al obtener el token: {str(e)}")
        return None

# **🔹 Test de conexión con AFIP**
@facturacion_bp.route('/dummy', methods=['GET'])
def dummy():
    try:
        print("Validando conexión con AFIP...")
        response = conexion_afip.validarConexion()
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error en validarConexionEndpoint: {e}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500

