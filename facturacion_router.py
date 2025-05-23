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
@facturacion_bp.route('/autorizarComprobante', methods=['POST'])
def autorizarComprobante(id_usuario=0, comprobante=None):
    try:

        if id_usuario == 0:
            logging.error(f"❌ ID de usuario no proporcionado")
            return jsonify({"control": "ERROR", "mensaje": "ID de usuario no proporcionado"}), 400

        if comprobante == "" or comprobante is None:
            logging.error(f"❌ El comprobante a autorizar no pudo ser detectado")
            return jsonify({"control": "ERROR", "mensaje": "El comprobante a autorizar no pudo ser detectado"}), 400



        # Procesar la factura
        resultado = wsfe_instance.autorizarComprobante(id_usuario, comprobante)
        return resultado
    except Exception as e:
        logging.error(f"Error en autorizar el comprobante: {e}")
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
def consultarComprobanteEmitido(id_usuario=0, cbteTipo=0, cbteNro=0, cbtePtoVta=0):
    if id_usuario == 0 :
        logging.error(f"❌ ID de usuario no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "ID de usuario no proporcionado"}), 400

    if cbteTipo  == 0:
        logging.error(f"❌ Tipo de Comprobante no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "Tipo de comprobante no proporcionado"}), 400
    if cbteNro == 0:
        logging.error(f"❌ Número de Comprobante no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "Número de Comprobante no proporcionado"}), 400

    if cbtePtoVta == 0:
        logging.error(f"❌ Punto de venta no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "Punto de venta no proporcionado"}), 400
    try:
        # Consultar el comprobante emitido
        response = wsfe_instance.consultarComprobanteEmitido(id_usuario, cbteTipo, cbteNro, cbtePtoVta)
        return response
    except Exception as e:
        logging.error(f"Error en consultarComprobanteEmitido: {e}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500

@facturacion_bp.route('/consultarUltimoCbteAutorizado', methods=['post'])
def consultarUltimoCbteAutorizado(id_usuario=0,  cbtePtoVta=0, cbteTipo=0):
    if id_usuario == 0 :
        logging.error(f"❌ ID de usuario no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "ID de usuario no proporcionado"}), 400

    if cbteTipo  == 0:
        logging.error(f"❌ Tipo de Comprobante no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "Tipo de comprobante no proporcionado"}), 400

    if cbtePtoVta == 0:
        logging.error(f"❌ Punto de venta no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "Punto de venta no proporcionado"}), 400
    try:
        # Consultar el comprobante emitido
        response = wsfe_instance.ultimoComprobanteAutorizado(id_usuario,  cbtePtoVta, cbteTipo)
        return response
    except Exception as e:
        logging.error(f"Error en consultarComprobanteEmitido: {e}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500


@facturacion_bp.route('/consultarPuntosDeVenta', methods=['post'])
def consultarPtosVentas(id_usuario):
    try:
        if not id_usuario:
            return jsonify({"control": "ERROR", "mensaje": "ID de usuario no proporcionado"}), 400

        # Consultar el comprobante emitido
        response = wsfe_instance.consultarPuntosVenta(id_usuario)
        return response
    except Exception as e:
        logging.error(f"Error en consultarPtosVentas: {e}")
        return jsonify({"control": "ERROR", "mensaje": str(e)}), 500


def validarToken(id_usuario):
    try:
        # Obtener el token vigente de la base de datos
        tokenResponse = getLogin(id_usuario)

        # Si tokenResponse es una tupla, accede a sus elementos
        if isinstance(tokenResponse, tuple):
            tokenResponse, codigo = tokenResponse
        else:
            raise Exception("Respuesta inesperada de getLogin.")

        if tokenResponse.get("codigo") == 200:
            for token in tokenResponse.get("datos", []):
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

