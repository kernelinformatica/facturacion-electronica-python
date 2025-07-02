import json

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
@facturacion_bp.route('/solicitarCae', methods=['POST'])
def autorizarComprobante():


    # Leer JSON del body
    parametros = request.get_json()
    id_usuario = parametros.get("id_usuario", 0)  # O ajusta según tu payload
    idFactCab = parametros.get("idFactCab", 0)
    idTipoCbte = parametros.get("cbteTipo", 0)
    idPtoVta = parametros.get("cbtePtoVta", 0)
    idFactCabRelacionado = parametros.get("idFactCabRelacionado", 0)

    if id_usuario == 0:
        logging.error("❌ ID de usuario no proporcionado")
        return jsonify({"control": "ERROR", "mensaje": "ID de usuario no proporcionado"}), 400

    if not idFactCab:
        logging.error("❌ El comprobante a autorizar no pudo ser detectado")
        return jsonify({"control": "ERROR", "mensaje": "El comprobante a autorizar no pudo ser detectado"}), 400

    try:
        parametros = {
            "idFactCab": idFactCab,
            "idFactCabRelacionado": idFactCabRelacionado,
            "cbtePtoVta": idPtoVta,
            "cbteTipo": idTipoCbte,
            "cbteFch": "2025-06-18",

        }

        # Procesar la factura
        resultado = wsfe_instance.autorizarComprobante(id_usuario, parametros)
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
        # Validar el ID de usuario
        if not id_usuario:
            return jsonify({"control": "ERROR", "mensaje": "Usuario no proporcionado"}), 400

        # Buscar token vigente
        tok = Tokens()
        tokenResponse = tok.buscarTokenVigente(id_usuario)

        if tokenResponse["codigo"] == 200:
            logging.info(":: Token vigente encontrado ::")
            return tokenResponse, 200

        logging.info(":: Token no vigente, generando nuevo token... ::")

        # Intentar generar nuevo token
        resp = conexion_afip.login(id_usuario)

        # Asegurar que la respuesta sea un diccionario JSON válido
        if isinstance(resp, str):
            resp = json.loads(resp)

        # Determinar el código de respuesta basado en la autenticación
        codigo = 200 if resp.get("control") == "OK" else 404

        # Registrar log de éxito o error
        if codigo == 200:
            logging.info(":: Autenticación exitosa con ARCA. ::")
        else:
            logging.info(f":: Algo salió mal al autenticar con ARCA: {resp} ::")

        # Retornar la respuesta en formato JSON compatible con APIs Flask
        return jsonify(resp), codigo

    except Exception as e:
         logging.error(f"❌ Error autenticando con ARCA: {str(e.strerror)}")
         return jsonify({"control": "ERROR", "mensaje": f"Error autenticando con ARCA: {str(e)}"}), 500


@facturacion_bp.route('/consultarCoprobanteEmitido', methods=['post'])
def consultarComprobanteEmitido(id_usuario=0, parametros=None):
    try:
        # Consultar el comprobante emitido
        response = wsfe_instance.consultarComprobanteEmitido(id_usuario, parametros["CbteTipo"], parametros["CbteNro"], parametros["PtoVta"])
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

        # Si `tokenResponse` es una tupla, desempacarla correctamente
        if isinstance(tokenResponse, tuple):
            tokenResponse, codigo = tokenResponse
        else:
            logging.error("❌ Respuesta inesperada de getLogin.")
            return None

        # Verificar si el token es válido
        if tokenResponse.get("codigo") == 200:
            token_datos = tokenResponse.get("datos", [])
            if token_datos:
                return token_datos[0]  # Retorna solo el primer token encontrado
            else:
                logging.error("❌ No se encontraron tokens en los datos.")
                return None

        logging.info(":: No se encontró un token vigente, generando nuevo token... ::")
        return None

    except Exception as e:
        logging.error(f"❌ Error al obtener el token: {str(e)}")
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

