import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, date, time
import re
import ssl
from decimal import Decimal
from idlelib import history
from lxml import etree
from requests import Session
from SSLAdapter import SSLAdapter
from utilidades import Utilidades as utils
from zeep.helpers import serialize_object
from requests.adapters import HTTPAdapter
from conectorManagerDB import ConectorManagerDB
import zeep
from zeep import Client
from zeep.transports import Transport
from tokens import Tokens as tok
import requests
import requests
from dotenv import load_dotenv
import time
from afipWsaaClient import AfipWsaaClient as afipClient

# Crear un contexto SSL personalizado que permita claves DH pequeñas
ssl_context = ssl.create_default_context()
ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")  # Reducir el nivel de seguridad para aceptar claves DH pequeñas

# Configurar el registro de depuración
logging.basicConfig(level=logging.DEBUG)
#logging.getLogger("zeep").setLevel(logging.DEBUG)


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
        self.intentos = int(os.getenv("CANTIDAD_REINTENTOS", 5))

        # Estas dos variables definien si es homologacion o produccion y a que base se conecta
        self.plataforma = int(os.getenv("PLATAFORMA", 1))
        self.testSn = os.getenv("WS_TEST", "True")

        #

    import json

    def login(self, id_usuario=0):
        logging.info("----------> :: app: login("+str(id_usuario)+") Autentica con AFIP utilizando los certificados :: <----------")
        intentos = self.intentos

        for intento in range(1, intentos + 1):
            try:
                # 🔹 Obtener el nuevo Token de Acceso
                cms = afipClient.obtenerNuevoTokenAcceso(self.trust_store, self.keystore, self.endpoint_login)

                try:
                    # 🔹 Si la respuesta es un diccionario, devolverlo en formato JSON
                    if isinstance(cms, dict):
                        logging.info(cms)
                        return json.dumps(cms)  # Convertir el diccionario a JSON

                    elif isinstance(cms, requests.Response):
                        cms = cms.text  # Si es una respuesta HTTP, extraer el contenido de texto

                    if not isinstance(cms, str):
                        logging.error({"control": "ERROR", "codigo" : "400", "mensaje": "Respuesta inesperada del servidor"})
                        return json.dumps({"control": "ERROR", "codigo" : "400", "mensaje": "Respuesta inesperada del servidor"})

                    # 🔹 Parsear el XML si es válido
                    root = ET.fromstring(cms)

                    # 🔹 Extraer datos del XML
                    data = {
                        "control": "OK",
                        "source": root.find(".//source").text if root.find(".//source") is not None else "N/A",
                        "destination": root.find(".//destination").text if root.find(
                            ".//destination") is not None else "N/A",
                        "uniqueId": root.find(".//uniqueId").text if root.find(".//uniqueId") is not None else "N/A",
                        "generationTime": root.find(".//generationTime").text if root.find(
                            ".//generationTime") is not None else "N/A",
                        "expirationTime": root.find(".//expirationTime").text if root.find(
                            ".//expirationTime") is not None else "N/A",
                        "token": root.find(".//token").text if root.find(".//token") is not None else "N/A",
                        "sign": root.find(".//sign").text if root.find(".//sign") is not None else "N/A",
                    }

                    # 🔹 Guardar el token y devolver la respuesta en JSON
                    tok.grabarToken(self, id_usuario, data["source"], data["destination"], data["uniqueId"],
                                    data["generationTime"], data["expirationTime"], data["token"], data["sign"])
                    logging.info(data)
                    return json.dumps(data)  # Convertir el diccionario a JSON
                except ET.ParseError as e:
                    logging.error("login(): "+str(e))


            except Exception as e:
                return json.dumps({"control": "ERROR", "mensaje": f"Error autenticando con {self.nombre_entidad}: {str(e)}"})

    def consultarComprobanteEmitido(self, id_usuario=0, cbteTipo=0, cbteNro=0, cbtePtoVta=0):
        logging.info(f":: consultarComprobanteEmitido({id_usuario}) ::")
        if not id_usuario or not cbteTipo or not cbteNro or not cbtePtoVta:
            return {"control": "ERROR", "mensaje": "❌ Error: Todos los parámetros deben tener un valor válido (no pueden ser vacíos, nulos o 0)"}
            raise ValueError("❌ Error: Todos los parámetros deben tener un valor válido (no pueden ser vacíos, nulos o 0)")

            # Si pasa la validación, continuar con la lógica
        print("✅ Parámetros válidos. Procediendo con la consulta...")
        # Aquí iría el código para hacer la consulta
        from facturacion_router import validarToken
        tok = validarToken(id_usuario)
        if tok["token"] is not None:
            intentos = self.intentos
            #for intento in range(1, intentos + 1):
            try:
                    metodo = "POST"
                    endPonintNombre = "FECompConsultar"
                    cuit_patron = r"CUIT (\d+)"
                    source = tok["source"]
                    cui = re.search(cuit_patron, source)
                    cuitCertificado = cui.group(1) if cui else 0

                    # Crear un contexto SSL personalizado
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")  # Reducir el nivel de seguridad para aceptar claves DH pequeñas
                    # Configurar la sesión de requests
                    session = Session()
                    session.verify = False  # Evita errores de certificado en entorno de prueba
                    session.mount("https://", SSLAdapter(ssl_context=ssl_context))
                    session.headers.update({
                        "Content-Type": "application/xml; charset=utf-8",
                        "SOAPAction": '"FECompConsultar"'
                    })

                    # Crear el transporte con la sesión configurada
                    transport = Transport(session=session)
                    # Datos de autenticación
                    auth = {
                        "Token": tok["token"],
                        "Sign": tok["sign"],
                        "Cuit": self.cuit
                    }
                    # Datos del comprobante a consultar 1, 5927, 2
                    fe_comp_cons_req = {
                        "CbteTipo": cbteTipo,
                        "CbteNro": cbteNro,
                        "PtoVta": cbtePtoVta
                    }

                    # Crear cliente SOAP
                    client = Client(self.endpoint_fe + "?wsdl", transport=transport)

                    # Enviar datos a AFIP
                    response = client.service.FECompConsultar(Auth=auth, FeCompConsReq=fe_comp_cons_req)
                    # Manejar la respuesta

                    if hasattr(response, "Errors") and response.Errors:
                        #grabar en sybaase el error en "afipws_fe_errores_log" solo en
                        if self.plataforma == 2:
                            self.grabarRespuestaARCA(2, id_usuario, response.Code, endPonintNombre, response.Errors, "E")
                        logging.error(f"❌ consultarComprobanteEmitido: Error en la respuesta de AFIP: {response.Errors}")
                        return {"control": "ERROR", "mensaje": f"Error en respuesta de AFIP: {response.Errors}"}
                    else:
                        logging.info(response)
                        return response
            except Exception as e:
               logging.error(f"❌ Error al consultar comprobante emitido: {str(e)}")
               return {"control": "ERROR", "mensaje": f"Error al consultar comprobante emitido: {str(e)}"}
        else:
            logging.error("❌ Token no válido o no disponible.")
            return {"control": "ERROR", "mensaje": "Token no válido o no disponible."}









    def ultimoComprobanteAutorizado(self, id_usuario, ptoVta=0, cbteTipo=0):
        logging.info(f":: FECompUltimoAutorizado({id_usuario}) ::")

        from facturacion_router import validarToken
        tok = validarToken(id_usuario)
        intentos = self.intentos
        #for intento in range(1, intentos + 1):
        if tok["token"] is not None:
                try:
                    metodo = "POST"
                    endPonintNombre = "FECompUltimoAutorizado"
                    cuit_patron = r"CUIT (\d+)"
                    source = tok["source"]
                    cui = re.search(cuit_patron, source)
                    cuitCertificado = cui.group(1) if cui else 0

                    # Crear un contexto SSL personalizado
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False  # Deshabilitar la verificación del nombre del host
                    ssl_context.verify_mode = ssl.CERT_NONE  # No verificar certificados
                    ssl_context.set_ciphers(
                        "DEFAULT:@SECLEVEL=1")  # Reducir el nivel de seguridad para aceptar claves DH pequeñas
                    # Configurar la sesión de requests
                    session = Session()
                    session.verify = False  # Evita errores de certificado en entorno de prueba
                    session.mount("https://", SSLAdapter(ssl_context=ssl_context))
                    session.headers.update({
                        "Content-Type": "application/xml; charset=utf-8",
                        "SOAPAction": '"FECompUltimoAutorizado"'
                    })

                    # Crear el transporte con la sesión configurada
                    transport = Transport(session=session)
                    # Datos de autenticación
                    auth = {
                        "Token": tok["token"],
                        "Sign": tok["sign"],
                        "Cuit": self.cuit
                    }
                    ptoVta =  ptoVta
                    cbteTipo =cbteTipo

                    # Datos del comprobante a consultar
                    # Crear cliente SOAP
                    client = Client(self.endpoint_fe + "?wsdl", transport=transport)

                    # Enviar datos a AFIP
                    response = client.service.FECompUltimoAutorizado(Auth=auth, PtoVta=ptoVta, CbteTipo=cbteTipo)

                    # Manejar la respuesta
                    if hasattr(response, "Errors") and response.Errors:
                        logging.error(f"❌  ultimoComprobanteAutorizado: Error en la respuesta de AFIP : {response.Errors}")
                        return {"control": "ERROR", "mensaje": f"Error en respuesta de AFIP: {response.Errors}"}
                    else:
                        logging.info("✅ ultimoComprobanteAutorizado: Solicitud enviada correctamente.")
                        return response

                except Exception as e:
                    logging.error(f"❌ "+str(endPonintNombre)+": Error al consultar último autorizado: {str(e)}")
                    return {"control": "ERROR", "mensaje": f""+str(endPonintNombre)+": Error al consultar último autorizado: {str(e)}"}
        else:
            logging.error("❌ Token no válido o no disponible.")
            return {"control": "ERROR", "mensaje": "Token no válido o no disponible."}







    def consultarPuntosVenta(self, id_usuario):
        logging.info(f":: ConsultarPurntosDeVenta({id_usuario}) ::")

        from facturacion_router import validarToken
        tok = validarToken(id_usuario)

        if tok["token"] is not None:
            intentos = self.intentos
            #for intento in range(1, intentos + 1):
            try:
                    metodo = "POST"
                    endPointNombre = "FEParamGetPtosVenta"
                    cuit_patron = r"CUIT (\d+)"
                    source = tok["source"]
                    cui = re.search(cuit_patron, source)
                    cuitCertificado = cui.group(1) if cui else 0

                    # Crear un contexto SSL personalizado
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False  # Deshabilitar la verificación del nombre del host
                    ssl_context.verify_mode = ssl.CERT_NONE  # No verificar certificados
                    ssl_context.set_ciphers(
                        "DEFAULT:@SECLEVEL=1")  # Reducir el nivel de seguridad para aceptar claves DH pequeñas
                    # Configurar la sesión de requests
                    session = Session()
                    session.verify = False  # Evita errores de certificado en entorno de prueba
                    session.mount("https://", SSLAdapter(ssl_context=ssl_context))
                    session.headers.update({
                        "Content-Type": "application/xml; charset=utf-8",
                        "SOAPAction": '"FEParamGetPtosVenta"'
                    })

                    # Crear el transporte con la sesión configurada
                    transport = Transport(session=session)
                    # Datos de autenticación
                    auth = {
                        "Token": tok["token"],
                        "Sign": tok["sign"],
                        "Cuit": self.cuit
                    }
                    # Datos del comprobante a consultar
                    # Crear cliente SOAP
                    client = Client(self.endpoint_fe + "?wsdl", transport=transport)

                    # Enviar datos a AFIP
                    response = client.service.FEParamGetPtosVenta(Auth=auth)

                    # Manejar la respuesta
                    if hasattr(response, "Errors") and response.Errors:
                        logging.error(f"❌ consultarPuntosventa: Error en la respuesta de AFIP: {response.Errors}")
                        return {"control": "ERROR", "codigo": "400","mensaje": f"Error en respuesta de AFIP: {response.Errors}"}
                    else:
                        logging.info("✅ "+str(endPointNombre)+": Solicitud enviada correctamente.")
                        return response
            except Exception as e:
                    logging.error(f"❌ "+str(endPointNombre)+": Error al consultar los puntos de venta habilitados, puede que no tenga dados de alta puntos de venta, verifique...: {str(e)}")
                    return {"control": "ERROR", "codigo": "400", "mensaje": f""+str(endPointNombre)+": Error al consultar los puntos de venta habilitados, puede que no tenga dados de alta puntos de venta, verifiqueo: {str(e)}"}

        else:
            logging.error("❌ Token no válido o no disponible.")
            return {"control": "ERROR", "codigo": "400", "mensaje": "Token no válido o no disponible."}




    def autorizarComprobante(self, id_usuario, parametros=None):

        if self.plataforma == 1:
            idFactCab = parametros["idFactCab"]
            comprobante =self.traerComprobante(id_usuario, parametros)
            if comprobante is None:
                json_resp = json.dumps({
                        "control": "ERROR",
                        "codigo": "400",
                        "mensaje": "Error: no se encuentra el comprobante "+str(idFactCab)+" que intenta autorizar, consulte con el administrador del sistema."
                }, indent=4, ensure_ascii=False)
                logging.error(json_resp)
                return json_resp




        elif self.plataforma == 2:
            # en comprobante va a venir el nro de comrpbaonte
            comprobante = self.traerComprobanteSybase(id_usuario, parametros)

            if comprobante is None:
                logging.error("❌ El comprobante a autorizar no pudo ser detectado")
                self.grabarRespuestaARCA(2, id_usuario, 400, "FECAESolicitar", "El comprobante a autorizar no pudo ser detectado")
                return {"control": "ERROR", "codigo": "400", "mensaje": "El comprobante a autorizar no pudo ser detectado"}



        from facturacion_router import validarToken
        tok = validarToken(id_usuario)
        if tok["token"] is not None:
            try:
                if not tok["token"] or not tok["sign"]:
                    self.login(id_usuario)

                # Busco el ultimo comprobante autorizado:
                comprobante_dict = json.loads(comprobante)
                cabecera = comprobante_dict.get("FeCabReq", {})
                detalle = comprobante_dict.get("FeDetReq", {})
                punto_venta = cabecera["PtoVta"]
                tipo_comp =  cabecera["CbteTipo"]
                cantidad = cabecera["CantReg"]
                ultimo = self.ultimoComprobanteAutorizado(id_usuario, punto_venta, tipo_comp)
                if hasattr(ultimo, "control") and ultimo.control == "ERROR":
                    if self.plataforma == 2:
                        #self, destino, id_usuario, errorCodigo, metodo,  errorMsg, params=None
                        self.grabarRespuestaARCA(2, id_usuario, ultimo["Code"], "FECompUltimoAutorizado", ultimo["Errors"], "U")
                        logging.error("Error: "+str(ultimo["Code"])+", Error: "+str(ultimo["Errors"]))
                    return ultimo
                endPointNombre = "FECAESolicitar"
                cuit_patron = r"CUIT (\d+)"
                source = tok["source"]
                cui = re.search(cuit_patron, source)
                cuitCertificado = cui.group(1) if cui else 0

                # Crear un contexto SSL personalizado
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False  # Deshabilitar la verificación del nombre del host
                ssl_context.verify_mode = ssl.CERT_NONE  # No verificar certificados
                ssl_context.set_ciphers(
                    "DEFAULT:@SECLEVEL=1")  # Reducir el nivel de seguridad para aceptar claves DH pequeñas
                # Configurar la sesión de requests
                session = Session()
                session.verify = False  # Evita errores de certificado en entorno de prueba
                session.mount("https://", SSLAdapter(ssl_context=ssl_context))
                # Configurar la sesión de requests
                session.headers.update({
                    "Content-Type": "application/xml; charset=utf-8",
                    "SOAPAction": '"FECAESolicitar"'
                })

                nroComprobanteInterno  = detalle["CbteDesde"]
                nuevoNroComprobante = int(ultimo["CbteNro"])+1

                # Crear el transporte con la sesión configurada

                intentos = self.intentos
                #for intento in range(1, intentos + 1):
                transport = Transport(session=session)
                client = zeep.Client(wsdl=self.endpoint_fe + "?wsdl", transport=transport)

                try:
                        # Configurar autenticación
                        #if comprobante is not None:

                            FECAEDetRequestType = client.get_type("ns0:FECAEDetRequest")
                            FECAECabRequestType = client.get_type("ns0:FECAECabRequest")

                            auth = {
                                "Token": tok["token"],
                                "Sign": tok["sign"],
                                "Cuit": self.cuit
                            }

                            # Crear la cabecera del comprobante

                            fe_cab_req = [
                                FECAECabRequestType(
                                    CantReg = cantidad,
                                    PtoVta= 1,#punto_venta,
                                    CbteTipo = tipo_comp
                                )
                            ]
                            # Crear el detalle del comprobante



                            print(":: DETALLE DEL COMPROBANTE ::")
                            print("Concepto: "+str(detalle["Concepto"]))
                            print("DocTipo: " + str(detalle["DocTipo"]))
                            print("DocNro: " + str(detalle["DocNro"]))
                            print("CbteDesde: " + str(detalle["CbteDesde"]))
                            print("CbteHasta: " + str(detalle["CbteHasta"]))
                            print("CbteFch: " + str(detalle["CbteFch"]))
                            print("ImpTotal: " + str(detalle["ImpTotal"]))
                            print("ImpTotConc: " + str(detalle["ImpTotConc"]))
                            print("ImpNeto: " + str(detalle["ImpNeto"]))
                            print("ImpOpEx: " + str(detalle["ImpOpEx"]))
                            print("ImpTrib: " + str(detalle["ImpTrib"]))
                            print("ImpIVA: " + str(detalle["ImpIVA"]))
                            print("MonId: " + str(detalle["MonId"]))
                            print("MonCotiz: " + str(detalle["MonCotiz"]))
                            print("FchServDesde: " + str(detalle["FchServDesde"]))
                            print("FchServHasta: " + str(detalle["FchServHasta"]))

                            print("CondicionIVAReceptorId: " + str(detalle["CondicionIVAReceptorId"]))
                            print("FchVtoPago: " + str(detalle["FchVtoPago"]))
                            print("NumeroComprobanteArca: "+ str(detalle["NumeroComprobanteArca"]))
                            print("Iva: " + str(detalle["Iva"]))
                            print("Tributos: " + str(detalle["Tributos"]))
                            print("Opcionales: " + str(detalle["Opcionales"]))
                            print("PeriodoAsoc: " + str(detalle["PeriodoAsoc"]))

                            if detalle["Tributos"] is not None:
                                print("Tributos: " + str(detalle["Tributos"]))
                            if detalle["CbtesAsoc"] is not None:
                                print("CbtesAsoc: " + str(detalle["CbtesAsoc"]))
                            if detalle["Opcionales"] is not None:
                                print("Opcionales: " + str(detalle["Opcionales"]))
                            print("::::::::::::::::::::::::::::::::::::::::::::::::::::")




                            fe_det_req = [
                                FECAEDetRequestType(
                                    Concepto=detalle["Concepto"],  # Concepto: 1-Productos, 2-Servicios, 3-Productos y Servicios
                                    DocTipo=detalle["DocTipo"],  # Tipo de documento: 96-DNI
                                    DocNro=detalle["DocNro"],  # Número de documento
                                    CbteDesde=nuevoNroComprobante,  # Número de comprobante desde
                                    CbteHasta=nuevoNroComprobante,  # Número de comprobante hasta
                                    CbteFch=detalle["CbteFch"],  # Fecha del comprobante (YYYYMMDD)
                                    ImpTotal=detalle["ImpTotal"],  # Importe total
                                    ImpTotConc=detalle["ImpTotConc"],  # Importe no gravado
                                    ImpNeto=detalle["ImpNeto"],  # Importe neto gravado
                                    ImpOpEx=detalle["ImpOpEx"],  # Importe exento
                                    ImpTrib=detalle["ImpTrib"],  # Importe de tributos
                                    ImpIVA=detalle["ImpIVA"],  # Importe de IVA
                                    MonId=detalle["MonId"],  # Moneda (PES para pesos argentinos)
                                    MonCotiz=detalle["MonCotiz"],
                                    #CanMisMonExt = detalle["CanMisMonExt"],
                                    FchServDesde= detalle["FchServDesde"],
                                    FchServHasta= detalle["FchServHasta"],
                                    CondicionIVAReceptorId=detalle["CondicionIVAReceptorId"],
                                    FchVtoPago=detalle["FchVtoPago"],
                                    Tributos=detalle["Tributos"],
                                    Iva=detalle["Iva"],
                                    CbtesAsoc= detalle["CbtesAsoc"],
                                    Opcionales =  detalle["Opcionales"],
                                    Compradores = None,
                                    PeriodoAsoc = detalle["PeriodoAsoc"],
                                    Actividades = None
                                )
                            ]


                            # Construir la solicitud
                            fe_cae_req = {
                                "FeCabReq": fe_cab_req[0],
                                "FeDetReq": {"FECAEDetRequest": fe_det_req}
                            }

                            # Enviar la solicitud

                            response = client.service.FECAESolicitar(Auth=auth, FeCAEReq=fe_cae_req)

                            if self.plataforma == 1:
                                print(":: RESPUESTA DE AUTORIZACION DE COMPROBANTE EXITOSO ::")
                                resp = self.autorizarComprobanteRespuesta(id_usuario, response, comprobante, idFactCab)
                                return resp
                            else:
                                return self.autorizarComprobanteRespuesta(id_usuario, response, comprobante, nroComprobanteInterno)

                except Exception as e:
                    return self.autorizarComprobanteRespuesta(id_usuario, response, comprobante)

            except Exception as e:
                jsonResp = {
                    "control": "ERROR",
                    "codigo": "400",
                    "errorMsg" : {ultimo},
                    "mensaje": f"Error enviando factura a {self.nombre_entidad}: {str(e)}"
                }

                logging.error(f"Error enviando factura a "+str(self.nombre_entidad)+": "+str({e}))
                raise Exception(f"Error enviando factura a "+str(+str(self.nombre_entidad))+": "+str(e))


    def reautorizarComprobante(self, id_usuario, comprobante=None):
        intentos = self.intentos
        #for intento in range(1, intentos + 1):
        print(":: REAUTORIZAR COMPROBANTE ::")

    def autorizarComprobanteRespuesta(self, id_usuario, respuesta, comprobante=None, nro_comp_interno=0):
        print("=======================================================")
        print(":: RESPUESTA DE AUTORIZACION DE COMPROBANTE ::")
        print(":: "+str(respuesta)+" ::")
        print("=======================================================")

        try:
            # Verificar si hay errores
            if respuesta["Errors"] :
                errores = respuesta["Errors"]["Err"]
                if self.plataforma == 2:
                  self.borraErrorARCASybase(1, id_usuario, comprobante)
                  if self.grabarRespuestaARCA(1, id_usuario, respuesta["Errors"]["Err"][0]["Code"], "FECAESolicitar", respuesta["Errors"]["Err"][0]["Msg"], comprobante, "E") == True :
                      return json.dumps({
                          "control": "ERROR",
                          "codigo": "400",
                          "mensaje": "Se encontraron errores en la respuesta de " + str(self.nombre_entidad) + ".",
                          "errores": [{"codigo": err["Code"], "mensaje": err["Msg"]} for err in errores]
                      }, indent=4, ensure_ascii=False)
                  else:
                        #self.borraErrorARCASybase(1, id_usuario, comprobante)
                        logging.error("❌ Error al grabar en la base de datos: "+str(respuesta["Errors"]["Err"][0]["Msg"]))
                        return json.dumps({
                            "control": "ERROR",
                            "codigo": "400",
                            "mensaje": "Se encontraron errores en la respuesta de " + str(self.nombre_entidad) + ".",
                            "errores": [{"codigo": err["Code"], "mensaje": err["Msg"]} for err in errores]
                        }, indent=4, ensure_ascii=False)
                        logging.error([{"codigo": err["Code"], "mensaje": err["Msg"]} for err in errores])

                else:
                    logging.error([{"codigo": err["Code"], "mensaje": err["Msg"]} for err in errores])
                    return json.dumps({
                        "control": "ERROR",
                        "codigo": "400",
                        "mensaje": "Se encontraron errores en la respuesta de " + str(self.nombre_entidad) + ".",
                        "errores": [{"codigo": err["Code"], "mensaje": err["Msg"]} for err in errores]
                    }, indent=4, ensure_ascii=False)







            elif hasattr(respuesta, "FeCabResp") and respuesta.FeCabResp:
                # Verificar si el resultado es exitoso

                if hasattr(respuesta.FeCabResp, "Resultado") and respuesta.FeCabResp.Resultado == "A":

                    if self.plataforma == 2:
                        resp = self.actualizarComprobanteSybase(id_usuario, comprobante, respuesta, nro_comp_interno)
                        return resp
                    else:
                        resp = self.actualizarComprobante(id_usuario, comprobante, respuesta, nro_comp_interno)
                        return resp



                else:
                    # Comprobante no autorizado
                    observaciones = [
                        {"Code": obs.Code, "Msg": obs.Msg} for obs in
                        respuesta.FeDetResp.FECAEDetResponse[0].Observaciones.Obs
                    ]

                    if self.plataforma == 2:
                        self.borraErrorARCASybase(1, id_usuario, comprobante)
                        h=0
                        for fila in observaciones:
                            print(f"Código: {fila['Code']}, Mensaje: {fila['Msg']}")
                            msg = "Comprobante no autorizado"+": "+fila["Msg"]+" (Codigo: "+str(fila["Code"])+")"
                            self.grabarRespuestaARCA(1, id_usuario, 400, "FECAESolicitar", msg, comprobante, "E")
                            h = h+1
                            logging.info("Ver tabla afipws_fe_log: "+msg)

                    logging.error("ERROR: " + ": "+ str(observaciones))
                    return json.dumps({
                        "control": "ERROR",
                        "codigo": "400",
                        "mensaje": "Comprobante no autorizado.",
                        "respuesta": respuesta.FeCabResp.__dict__,
                        "observaciones": observaciones
                    }, indent=4, ensure_ascii=False)
                    # aca debo ver laplataformay grabar en sybase la repuesta para que se analice

                # Obtener el resultado del comprobante
                fe_cab_resp = respuesta.FeCabResp




                # Si el resultado no es exitoso
                return json.dumps({
                    "control": "ERROR",
                    "mensaje": "El comprobante no fue generado.",
                    "datos": fe_cab_resp
                }, indent=4, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "control": "ERROR",
                "control": "400",
                "mensaje": f"Error procesando la respuesta: {str(e)}"
            }, indent=4, ensure_ascii=False)















    def actualizarComprobanteSybase(self, id_usuario, cbte_original, respuesta, nro_comp_interno):
        conn = ConectorManagerDB(2)
        cursor = conn.get_connection().conn.cursor()
        # Extraer valores de FeCabResp
        logging.info("::::: ACTUALIZAR COMPROBANTE SYBASE:::::")
        cuit = respuesta['FeCabResp']['Cuit']
        pto_vta = respuesta['FeCabResp']['PtoVta']
        cbte_tipo = respuesta['FeCabResp']['CbteTipo']
        fch_proceso = respuesta['FeCabResp']['FchProceso']
        fch_proceso_conv =datetime.strptime(fch_proceso, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        cant_reg = respuesta['FeCabResp']['CantReg']
        resultado = respuesta['FeCabResp']['Resultado']
        reproceso = respuesta['FeCabResp']['Reproceso']

        # Extraer valores de FeDetResp
        detalles = respuesta['FeDetResp']['FECAEDetResponse'][0]
        concepto = detalles['Concepto']
        doc_tipo = detalles['DocTipo']
        doc_nro = detalles['DocNro']
        cbte_desde = detalles['CbteDesde']
        cbte_hasta = detalles['CbteHasta']
        cbte_numero_interno = nro_comp_interno
        cbte_fch = detalles['CbteFch']
        cbte_fch_conv = datetime.strptime(cbte_fch, "%Y%m%d").strftime("%Y-%m-%d")
        resultado_det = detalles['Resultado']
        cae = detalles['CAE']
        cae_fch_vto = detalles['CAEFchVto']
        cae_fch_vto_conv = datetime.strptime(cae_fch_vto, "%Y%m%d").strftime("%Y-%m-%d")

        observaciones = detalles["Observaciones"]["Obs"]
        if observaciones:  # Verificamos si hay observaciones
            for obs in observaciones:
                observacion_code = obs["Code"]
                observacion_msg = obs["Msg"]
                #print(f"Código: {observacion_code} - Mensaje: {observacion_msg}")
        else:
            print("No hay observaciones registradas.")

        # Mostrar valores extraídos
        print(f"Cuit: {cuit}, PtoVta: {pto_vta}, CbteTipo: {cbte_tipo}")
        print(f"Fecha Proceso: {fch_proceso}, CantReg: {cant_reg}, Resultado: {resultado}, Reproceso: {reproceso}")
        print(f"Concepto: {concepto}, DocTipo: {doc_tipo}, DocNro: {doc_nro}")
        print(f"CbteDesde: {cbte_desde}, CbteHasta: {cbte_hasta}, CbteFch: {cbte_fch}, Resultado: {resultado_det}")
        print(f"CAE: {cae}, CAE Fch Vto: {cae_fch_vto}")
        print(f"Observación Code: {observacion_code}, Observación Msg: {observacion_msg}")



        logging.info("::::: Afip_fe_master :::::")
        try:
            sql = """UPDATE afipws_fe_master
                     SET "Resultado" = ?, 
                         "CAE" = ?, 
                         "CAEFchVto" = ?, 
                         "pto_emision" = ?, 
                         "v_numero_comprobante" = ?, 
                         "FchProceso" = ?
                     WHERE CbteDesde = ? AND CbteFch = ? AND PtoVta = ?"""

            # Ejecutar la consulta con parámetros dentro de un bloque de manejo de errores
            cursor.execute(sql, (resultado, cae, cae_fch_vto_conv, pto_vta, cbte_desde, fch_proceso_conv, cbte_numero_interno, cbte_fch_conv,
                pto_vta))

            cursor.commit()  # Asegurar que los cambios se guarden
        except Exception as e:
            print(f"Ocurrió un error al ejecutar la consulta SQL: 'afipws_fe_master' {e}")

        logging.info("::::: Actualizando afip_fe_detalle :::::")

        try:
            sql = """UPDATE afipws_fe_detalle
                            SET "v_numero_comprobante" = ? , "pto_emision" = ?
                            WHERE CbteDesde = ? AND CbteTipo = ? AND PtoVta = ?"""

            cursor.execute(sql, (cbte_desde, pto_vta, nro_comp_interno, cbte_tipo, pto_vta))
            cursor.commit()  # Asegurar que los cambios se guarden
        except Exception as e:
            print(f"Ocurrió un error al ejecutar la consulta SQL: 'afip_fe_detalle' {e}")

        logging.info("::::: actualizando fac_ventas :::::")

        try:
            sql = """UPDATE fac_ventas
                     SET "autorizado_sn" = ?, 
                         "tipo_autorizado" = ?, 
                         "pto_autorizado" = ?, 
                         "nro_autorizado" = ?, 
                         "fe_autorizado" = ?,
                         "CAE" =? 
                     WHERE autorizado_sn = ? AND v_fecha_operacion = ? and v_numero_comprobante = ? and pto_numero = ? and v_tipo_comprobante = ?  and v_numero_cuit = ? """

            cursor.execute(sql, ("S", cbte_tipo, pto_vta, cbte_desde, cbte_fch_conv, cae, "N", cbte_fch_conv,  cbte_numero_interno, pto_vta, cbte_tipo, doc_nro))
            cursor.commit()
        except Exception as e:
            print(f"Ocurrió un error al ejecutar la consulta SQL 'fac_ventas': {e}")

        msg = "Comprobante autorizado con éxito: " + str(observacion_msg)
        self.grabarRespuestaARCA(1, id_usuario, 200, "FECAESolicitar", msg, cbte_original, "A",cbte_desde )





    def actualizarComprobante(self, id_usuario, comprobante_original, respuesta, idFactCab=0):
        logging.info("::::: ACTUALIZAR COMPROBANTE :::::")
        cuit = respuesta['FeCabResp']['Cuit']
        pto_vta = respuesta['FeCabResp']['PtoVta']
        cbte_tipo = respuesta['FeCabResp']['CbteTipo']
        fch_proceso = respuesta['FeCabResp']['FchProceso']
        fch_proceso_conv = datetime.strptime(fch_proceso, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        cant_reg = respuesta['FeCabResp']['CantReg']
        resultado = respuesta['FeCabResp']['Resultado']
        reproceso = respuesta['FeCabResp']['Reproceso']
        detalles = respuesta['FeDetResp']['FECAEDetResponse'][0]
        concepto = detalles['Concepto']
        doc_tipo = detalles['DocTipo']
        doc_nro = detalles['DocNro']
        cbte_desde = detalles['CbteDesde']
        cbte_hasta = detalles['CbteHasta']
        nro_comp_full = self.generar_numero_comprobante(pto_vta, cbte_desde)
        cbte_fch = detalles['CbteFch']
        cbte_fch_conv = datetime.strptime(cbte_fch, "%Y%m%d").strftime("%Y-%m-%d")
        resultado_det = detalles['Resultado']
        cae = detalles['CAE']
        cae_fch_vto = detalles['CAEFchVto']
        cae_fch_vto_conv = datetime.strptime(cae_fch_vto, "%Y%m%d").strftime("%Y-%m-%d")

        observaciones = detalles["Observaciones"]["Obs"]
        if observaciones:  # Verificamos si hay observaciones
            for obs in observaciones:
                observacion_code = obs["Code"]
                observacion_msg = obs["Msg"]
                # print(f"Código: {observacion_code} - Mensaje: {observacion_msg}")
        else:
            print("No hay observaciones registradas.")

        """aca debo de verificar si esxiste la cabecera antes de atualizar"""


        #primero verifico que la cabecera auno este autorizado

        # Mostrar valores extraídos
        conn = ConectorManagerDB(1)
        cursor = conn.get_connection().conn.cursor()
        sql_sel_fc = """SELECT COUNT(*) FROM FactCab WHERE idFactCab = %s AND cai = '' AND (numeroAfip IS NULL OR numeroAfip = 0);"""
        cursor.execute(sql_sel_fc, (idFactCab, ))
        row = cursor.fetchone()
        cursor.close()

        if row and row[0] > 0:

            try:
                conn = ConectorManagerDB(1)
                cursor = conn.get_connection().conn.cursor()
                sql_update = """UPDATE FactCab SET  numeroAfip = %s, cai = %s, caiVto = %s WHERE idFactCab = %s AND (cai = '' or cai IS NULL) AND (numeroAfip IS NULL OR numeroAfip = 0);"""
                cursor.execute(sql_update, (nro_comp_full, cae, cae_fch_vto_conv, idFactCab,))


                try:

                    cursor.execute("COMMIT")
                    cursor.close()
                    conn.get_connection().conn.close()
                    logging.info("✅ Commit realizado con éxito. " + str(conn.get_connection().conn))

                    fac_cab_resp = {
                        "codigo": "200",
                        "control": "OK",
                        "mensaje": "Actualización de la Cabecera exitosa, 1 registro(s) modificado(s), CAE otorgado: " + str(
                            cae) + ", Nro comprobante electrónico: " + str(
                            nro_comp_full) + ", Fecha de vencimiento del CAE: " + str(cae_fch_vto_conv)
                    }

                    logging.info(":: Actualizo la cabecera del comprobante, ahora debe hacer el pasaje a fac_ventas en sybase ::")
                    logging.info(":: Contabilizacion a Master Sybase ::")
                    actualizarAsientoMaster = self.actualizaMasterSybase(id_usuario, comprobante_original, respuesta, idFactCab)
                    if actualizarAsientoMaster == False:
                        respActualizaMaster = {
                            "codigo": "400",
                            "control": "ERROR",
                            "mensaje": "Se produjo un error inesperador al actalizar la contabilidad, verifique. Numero de comprobante = "+str(comprobante_original["CbteDesde"]),
                        }
                    else:
                        respActualizaMaster = {
                            "codigo": "200",
                            "control": "OK",
                            "mensaje": "Contabilización a Master Sybase se realizo exitosamente, Nro comprobante electrónico: " + str(nro_comp_full) + ", CAE: " + str(cae) + ", Fecha de vencimiento del CAE: " + str(cae_fch_vto_conv)
                        }
                        grabarFacVentas = self.grabarFacVentasSybase(id_usuario, comprobante_original, respuesta,
                                                                     idFactCab)
                        if grabarFacVentas == False:
                            respFacVentas = {
                                "codigo": "400",
                                "control": "ERROR",
                                "mensaje": "Se produjo un error inesperador al hacer el pasaje a fac_ventas sybase.",
                            }
                        else:
                            respFacVentas = {
                                "codigo": "200",
                                "control": "OK",
                                "mensaje": "Pasaje a fac_ventas se realizo exitosamente, Nro comprobante electrónico: " + str(
                                    nro_comp_full) + ", CAE: " + str(cae) + ", Fecha de vencimiento del CAE: " + str(
                                    cae_fch_vto_conv)
                            }


                    resp = {
                        "control": "OK",
                        "mensaje": "Comprobante autorizado con éxito",
                        "datos": {
                            "Cuit": str(cuit),
                            "PtoVta": str(pto_vta),
                            "CbteTipo": cbte_tipo,
                            "FechaProceso": str(fch_proceso),
                            "CantReg": 1,
                            "Resultado": resultado,
                            "Reproceso": reproceso,
                            "ResultadoDetalle": resultado_det,
                            "Concepto": concepto,
                            "DocTipo": doc_tipo,
                            "DocNro": doc_nro,
                            "CbteDesde": cbte_desde,
                            "CbteHasta": cbte_desde,
                            "CbteFch": "" + str(cbte_fch_conv),
                            "CAE": cae,
                            "CAEFchVto": str(cae_fch_vto),
                            "Observaciones": {
                                "Code": observacion_code,
                                "Msg": observacion_msg
                            }
                        },
                        "FactCab": fac_cab_resp,
                        "FactVentas": respFacVentas,
                        "Master": respActualizaMaster
                    }

                    logging.info(json.dumps(resp, indent=4, ensure_ascii=False))
                    return json.dumps(resp, indent=4, ensure_ascii=False)
                except Exception as e:
                    logging.error(f"❌ Error al realizar el commit: {str(e)}")
                # Verificar si se afectaron filas



            except Exception as e:
                logging.error(f"❌ Error al realizar la actualización de la cabecera: {str(e)}")
                return json.dumps(f"❌ Error al realizar la actualización de la cabecera: {str(e)}", indent=4, ensure_ascii=False)



        else:
            logging.info(":: Actualiza tabla FactCab () ::")
            logging.error("⚠️ :: Comprobante autorizado (Cae: "+str(cae)+",Nro comprobante Arca: "+str(nro_comp_full)+"), pero no se encontró la cabecera del comprobante en la base de datos, seguramente ya posee un CAE válido. Verifique !!! ::")
            return json.dumps({
                "control": "ERROR",
                "codigo": "400",
                "mensaje": "Comprobante autorizado (Cae: "+str(cae)+",Nro comprobante Arca: "+str(nro_comp_full)+"), pero no se encontró la cabecera del comprobante en la base de datos, seguramente ya posee un CAE. Verifique !!!"
            }, indent=4, ensure_ascii=False)

















    """
    Pasajes a Sybase
    
    """

    def grabarFacVentasSybase(self, id_usuario, cbte_original, cbte_autorizado, idFactCab=0):
        logging.info("--------------> grabarFacVentasSybase("+str(idFactCab)+") <----------------------")
        try:
            # 🔹 Extraer datos del comprobante antes de autorizar
            fe_original_data = json.loads(cbte_original)
            fe_cab_original = fe_original_data["FeCabReq"]
            fe_det_original = fe_original_data["FeDetReq"]

            # 🔹 Extraer datos del comprobante autorizado
            fe_cab_resp = cbte_autorizado.FeCabResp
            fe_det_resp = cbte_autorizado.FeDetResp.FECAEDetResponse[0]  # Tomamos el primer comprobante

            # 🔹 Extraer datos principales
            fechaProcesoObj = datetime.strptime(fe_cab_resp.FchProceso, "%Y%m%d%H%M%S")
            fchProceso = fechaProcesoObj.strftime("%Y-%m-%d")
            fechaProcesoHora = fechaProcesoObj.strftime("%H:%M:%S")

            fechaCaeObj = datetime.strptime(fe_det_resp.CAEFchVto, "%Y%m%d")
            fechaCae = fechaCaeObj.strftime("%Y-%m-%d")


            fechVenceObj = datetime.strptime(fe_det_resp.CAEFchVto, "%Y%m%d")
            fechaVence = fechVenceObj.strftime("%Y-%m-%d")





            # 🔹 Sentencia SQL para insertar datos
            try:
                conn = ConectorManagerDB(1)
                with conn.get_connection().conn.cursor() as cursor:
                    # Consulta principal
                    sql_fp = """SELECT codigoSYsbase
                                        FROM FactFormaPago ffp
                                        INNER JOIN FormaPago fp ON fp.idFormaPago = ffp.idFormaPago
                                        WHERE ffp.idFactCab = %s;
                                    """
                    cursor.execute(sql_fp, (idFactCab,))
                    resu = cursor.fetchone()
                    if resu[0] is None:
                        formaPago = 0
                    else:
                        formaPago = resu[0]

                with conn.get_connection().conn.cursor() as cursor:
                    sql_pad = """SELECT apellido, nombre from PadronGral  WHERE idPadronGral = %s"""
                    cursor.execute(sql_pad, (fe_det_original["IdPadron"],))
                    resu = cursor.fetchone()
                    if resu[0] is None:
                        nombreApellido = ""
                    else:
                        nombreApellido = resu[0]+" "+resu[1]

                iva_21 = 0
                iva_105 =0
                iva_27 =0
                iva_extento = 0
                # me fijo que iva es
                for iva in fe_det_original["Iva"]["AlicIva"]:
                    if iva["Id"] == 5:
                        iva_21 = iva["Importe"]
                        #print(f"Alícuota 21% encontrada - Base: {iva['BaseImp']}, Importe: {iva['Importe']}")
                    elif iva["Id"] == 4:
                        iva_105 = iva["Importe"]
                        #print(f"Alícuota 10% encontrada - Base: {iva['BaseImp']}, Importe: {iva['Importe']}")
                    elif iva["Id"] == 6:
                        iva_27 = iva["Importe"]

                    else:
                        print(f"⚠️ Alícuota desconocida - ID: {iva['Id']}")


                # traigo el detalle FactCabDetalle
                fac_detalle = []
                idDeposito = 1

                with conn.get_connection().conn.cursor() as cursor:
                    sql_fd = """SELECT Depositos.codigoDep FROM FactDetalle, Depositos WHERE FactDetalle.idFactCab = %s  AND FactDetalle.idDepositos = Depositos.idDepositos GROUP BY FactDetalle.idDepositos"""
                    cursor.execute(sql_fd, (idFactCab,))
                    resu = cursor.fetchone()
                    if resu[0] is None:
                        idDeposito = 1
                    else:
                        idDeposito = resu[0]




                pto_venta_original = fe_det_original["CbteDesde"][:4]
                nro_comprobante_original = fe_det_original["CbteDesde"][4:]


                # Aca evaluar para la reautorizacion de hacer un uptdate de fac_ventas si el registro existe
                # si no existe lo inserto y si existe lo actualizo



                conn = ConectorManagerDB(2)
                with conn.get_connection().conn.cursor() as cursor:
                    # movimiento de cierre
                    datosCierre = {
                        "v_codigo": "CIERRE",
                        "v_tipo_operacion": fe_cab_original["CbteTipo"],
                        "v_fecha_operacion": str(fchProceso),
                        "v_tipo_comprobante": fe_cab_original["CbteTipo"],
                        "v_numero_comprobante": int(nro_comprobante_original),
                        "v_numero_ctacte": fe_det_original["IdPadron"],
                        "v_numero_mov": 0,
                        "v_forma_pago": formaPago,
                        "v_nombre": nombreApellido,
                        "v_numero_cuit": int(fe_det_original["DocNro"]),
                        "v_cantidad": 1,
                        "v_descripcion": "FE: " + nombreApellido,
                        "v_precio_unitario": float(fe_det_original["ImpNeto"]),
                        "v_retencion1": float(0.00),
                        "v_retencion2": float(0.00),
                        "v_percepcion1": float(fe_det_original["ImpTrib"]),
                        "v_percepcion2": float(0.00),
                        "v_impuesto_interno": float(0.00),
                        "v_otro_impuesto": float(0.00),
                        "v_iva_ri": float(iva_21),
                        "v_iva_rni": float(iva_105),
                        "v_descuento": float(0.00),
                        "v_bonificacion": float(fe_det_original["ImpTotal"]),
                        "v_codigo_relacion": 1,
                        "v_fecha_vencimiento": fechaVence,
                        "v_facturado_sn": "S",
                        "v_codigo_operador": 'DBA',
                        "v_hora": fechaProcesoHora,
                        "v_condicion_iva": fe_det_original["CondicionIVAReceptorId"],
                        "pto_numero": fe_cab_original["PtoVta"],
                        "v_tipo_comprobante_asoc": 0,  # supongo que es cuando anulamos ???
                        "v_numero_comprobante_asoc": 0,  # supongo que es cuando anulaos ???,
                        "v_deposito": idDeposito,
                        "v_contabil": "S",
                        "v_cuotas": int(0),
                        "v_cuotas_interes": float(0),
                        "canje_sn": "N",
                        "canje_nro_cto": "0",
                        "li_nro_comp": 0,
                        "li_preimp": 0,
                        "v_perce2459_1": float(0),
                        "v_perce2459_105": float(0),
                        "cod_actividad": 0,
                        "autorizado_sn": "S",
                        "pto_autorizado": fe_cab_resp["PtoVta"],
                        "tipo_autorizado": fe_cab_resp["CbteTipo"],
                        "nro_autorizado": fe_det_resp["CbteDesde"],
                        "fe_autorizado": fchProceso,
                        "CAE": int(fe_det_resp["CAE"]),
                        "fe_Vto": fechaCae,  # Conversión de fecha
                    }
                    sql_insert = """INSERT INTO fac_ventas(v_codigo, v_tipo_operacion, v_fecha_operacion, v_tipo_comprobante, v_numero_comprobante, v_numero_ctacte, 
                                   v_numero_mov, v_forma_pago, v_nombre, v_numero_cuit, v_cantidad, v_descripcion, v_precio_unitario, v_retencion1, 
                                   v_retencion2, v_percepcion1, v_percepcion2, v_impuesto_interno, v_otro_impuesto, v_iva_ri, v_iva_rni, v_descuento, 
                                   v_bonificacion, v_codigo_relacion, v_fecha_vencimiento, v_facturado_sn, v_codigo_operador, v_hora, v_condicion_iva, 
                                   pto_numero, v_tipo_comprobante_asoc, v_numero_comprobante_asoc, v_deposito, v_contabil, v_cuotas, v_cuotas_interes, 
                                    canje_sn, canje_nro_cto, li_nro_comp, li_preimp, v_perce2459_1, v_perce2459_105, cod_actividad, autorizado_sn, pto_autorizado,
                                   tipo_autorizado, nro_autorizado, fe_autorizado, CAE, fe_Vto) 
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,  ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                    try:
                        cursor.execute(sql_insert, tuple(datosCierre.values()))
                        conn.get_connection().conn.commit()  # Confirmar la transacción
                        logging.error("✅ Registro insertado correctamente en fac_ventas")
                        return True
                    except Exception as e:
                        logging.error(":: Error al insertar en FactVentasSybase: " + str(e))
            except Exception as e:
                #logging.error("Error General al insertar en FactVentasSybase: " + str(e))
                return False
            finally:
                conn.get_connection().conn.close()
            # 🔹 Si todo sale bien, retornar True
            return True

        except Exception as e:
            #logging.error("Error al grabar en FactVentasSybase: "+str(e))
            return False





    def actualizaMasterSybase(self, id_usuario, cbte_original, cbte_autorizado, idFactCab=0):
        logging.info("--------------> actualizaMasterSybase("+str(idFactCab)+"), actualiza por nro_comp, fecha_emision y libro 50 <----------------------")
        try:
            conn = ConectorManagerDB(1)
            cursor = conn.get_connection().conn.cursor()
            sql_libro = """ SELECT valor from Parametros where  Parametros.grupo = 'contable' and Parametros.nombreParametro = 'codigo_libro_sybase';  """
            cursor.execute(sql_libro, )
            lib = cursor.fetchone()
            if lib:
                codigo_libro = lib[0]
            else:
                codigo_libro = 50  # Valor por defecto si no se encuentra el libro
            # SELECT * FROM Master WHERE nro_comp = '1500012174' AND m_ingreso = '2025-06-12' AND codigo_libro = 50 and padron_codigo = 6028

            # 🔹 Extraer datos del comprobante antes de autorizar
            fe_original_data = json.loads(cbte_original)
            fe_cab_original = fe_original_data["FeCabReq"]
            fe_det_original = fe_original_data["FeDetReq"]

            # 🔹 Extraer datos del comprobante autorizado
            fe_cab_resp = cbte_autorizado.FeCabResp
            fe_det_resp = cbte_autorizado.FeDetResp.FECAEDetResponse[0]  # Tomamos el primer comprobante

            # 🔹 Extraer datos principales
            fechaProcesoObj = datetime.strptime(fe_cab_resp.FchProceso, "%Y%m%d%H%M%S")
            fchProceso = fechaProcesoObj.strftime("%Y-%m-%d")
            fechaProcesoHora = fechaProcesoObj.strftime("%H:%M:%S")

            fechaCaeObj = datetime.strptime(fe_det_resp.CAEFchVto, "%Y%m%d")
            fechaCae = fechaCaeObj.strftime("%Y-%m-%d")

            fechVenceObj = datetime.strptime(fe_det_resp.CAEFchVto, "%Y%m%d")
            fechaVence = fechVenceObj.strftime("%Y-%m-%d")
            # armo el preimpreso del comprobante

            pto_vta = fe_cab_original["PtoVta"]
            nro_comprobante = fe_det_resp['CbteDesde']
            pto_vta_formateado = f"{pto_vta:0<4}"
            nro_comprobante_formateado = f"{nro_comprobante:06d}"
            nro_comp_preimp = f"{pto_vta_formateado}{nro_comprobante_formateado}"
            print(nro_comp_preimp)  # Salida esperada: 3500013816

            # 🔹 Sentencia SQL para actualizar datos en master
            conn = ConectorManagerDB(2)
            cursor = conn.get_connection().conn.cursor()
            sql_upt_master = """UPDATE master
                                SET nro_comp_asoc = ?,
                                 nro_comp_preimp = ?,
                                 autoriza_codigo = ?
                                WHERE "nro_comp" = ? and 
                                    "m_ingreso" = ? and 
                                    "codigo_libro" = ? and  
                                    "padron_codigo" = ? """
            params={
                "nro_comp_asoc": nro_comp_preimp,
                "nro_comp_preimp": nro_comp_preimp,
                "autoriza_codigo": fe_cab_original["PtoVta"],
                "nro_comp  ": fe_det_original["CbteDesde"],
                "m_ingreso": fchProceso,
                "codigo_libro": codigo_libro,
                "padron_codigo": fe_det_original["IdPadron"]
            }

            cursor.execute(sql_upt_master, tuple(params.values()))
            conn.get_connection().conn.commit()
            logging.info("✅ Registro actualizado correctamente en master")
            return True
            # 🔹 Extraer datos del comprobante antes de autorizar
        except Exception as e:
            return False
        finally:
            conn.get_connection().conn.close()














    def generar_numero_comprobante(self, pto_vta, nro_comprobante):
        nro =  f"{int(pto_vta):04d}{int(nro_comprobante):08d}"
        return str(nro)

    def validarConexion(self):
        """Valida la conexión con el servicio de AFIP y muestra el XML puro"""
        intentos = self.intentos
        for intento in range(1, intentos + 1):
            try:
                logging.info("Validando conexión con el servicio de AFIP...")
                plugin = self.get_zeep_logging_plugin()
                client = zeep.Client(wsdl=self.endpoint_fe + "?wsdl", plugins=[plugin])
                response = client.service.FEDummy()
                if response.AppServer == "OK" and response.DbServer == "OK" and response.AuthServer == "OK":
                    msg = f"La conexión con {self.nombre_entidad} se realizó exitosamente tras intentar "+str(intento)+" vez de "+str(self.intentos)+" intentos."
                    codigo = 200
                    control = "OK"
                else:
                    msg = f"Problema en la conexión con {self.nombre_entidad}. Servidores: {response} "+", intento: " + str(intento)
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
                logging.info(json.dumps(resp_json, ensure_ascii=False, indent=4))
                return resp_json

            except requests.exceptions.RequestException as e:
                logging.error(f"Error al conectar con AFIP (intento {intento}): {e}")
                if intento < intentos:
                    time.sleep(2)  # Espera 2 segundos antes de reintentar
                else:
                    return {"control": "ERROR",
                            "mensaje": f"Error al conectar con AFIP tras {intentos} intentos: {str(e)}"}




    def get_zeep_logging_plugin(self):
        from zeep import Plugin
        class LoggingPlugin(Plugin):
            def egress(self, envelope, http_headers, operation, binding_options):
                #print("===== REQUEST XML =====")
                #print(etree.tostring(envelope, pretty_print=True, encoding="unicode"))
                return envelope, http_headers

            def ingress(self, envelope, http_headers, operation):
                #print("===== RESPONSE XML =====")
                #print(etree.tostring(envelope, pretty_print=True, encoding="unicode"))
                return envelope, http_headers

        return LoggingPlugin()



    def borraErrorARCASybase(self, destino, id_usuario, cbte=None):
        # destino = 1 BORRA en afipws_fe_errores_log (errores generales de apliacion)
        # destino = 2 BORRA en afipws_fe_log (errores generados al autorizar comprobantes)
        # destino = 3 por ahora nada, se puede implementar distintas tablas
        try:
            # Conectar a la base de datos
            conn = ConectorManagerDB(2)
            cursor = conn.get_connection().conn.cursor()
            comp_dic = json.loads(cbte)
            fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Sentencia SQL de inserción
            if destino == 1:
                cabecera = comp_dic.get("FeCabReq", {})
                detalle = comp_dic.get("FeDetReq", {})
                # Valores a insertar
                cbteTipo = cabecera["CbteTipo"]
                ptoVenta = cabecera["PtoVta"]
                cbteDesde = detalle["CbteDesde"]
                nroComp = detalle["CbteDesde"]
                sql_delete = """
                DELETE FROM afipws_fe_log 
                WHERE CbteTipo = ? AND PtoVta = ? AND CbteDesde = ? AND tipo_comp = ? AND v_numero_comprobante = ?
                AND resultado <> 'A'"""
                # Ejecutar la sentencia
                cursor.execute(sql_delete, (cbteTipo, ptoVenta, cbteDesde, cbteTipo, nroComp))
                conn.get_connection().conn.commit()
                cursor.close()
            elif destino == 2:
                sql_delete = """
                DELETE FROM afipws_fe_errores_log 
                WHERE  operador = ?"""

                # Ejecutar la sentencia
                cursor.execute(sql_delete, ( id_usuario))
                conn.get_connection().conn.commit()
                cursor.close()


            return True
        except Exception as e:
            logging.error(f"Error al insertar en afipws_fe_errores_log: {e}")
            return False





        sqldel = """ delete  afipws_fe_log where  CbteTipo = % s and PtoVta = % s and v_numero_comprobante = % s and tipo_comp = %s"""
        cursor.execute(sqldel,cbteTipo, ptoVenta, nroComp, cbteTipo)
        conn.get_connection().conn.commit()

    def grabarRespuestaARCA(self, destino, id_usuario, errorCodigo, metodo,  errorMsg, cbte=None, resultado="E", comp_afip=0):
        # destino = 1 graba en afipws_fe_errores_log (errores generales de apliacion)
        # destino = 2 graba en afipws_fe_log (errores generados al autorizar comprobantes)
        # destino = 3 por ahora nada, se puede implementar distintas tablas
        if self.plataforma == 2 :
            try:

                conn = ConectorManagerDB(2)
                cursor = conn.get_connection().conn.cursor()

                fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                comp_dic =  json.loads(cbte)
                cabecera = comp_dic.get("FeCabReq", {})
                detalle = comp_dic.get("FeDetReq", {})
                if destino == 1 :

                    cbteTipo = cabecera["CbteTipo"]
                    ptoVenta = cabecera["PtoVta"]
                    mensaje = errorMsg
                    cbteDesde = detalle["CbteDesde"]
                    cbteHasta =  detalle["CbteHasta"]
                    nroComp =  detalle["CbteDesde"]

                    if comp_afip > 0 :
                        nro = comp_afip
                    else:
                        nro =   cbteDesde
                    sql = """INSERT INTO afipws_fe_log ("CbteTipo", "PtoVta", "CbteDesde", "FechaYHora", "mensaje", "CbteHasta", "tipo_comp", "pto_autorizado", "v_numero_comprobante", resultado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                    cursor.execute(sql, (cbteTipo, ptoVenta, nro, fecha_hora, mensaje, cbteHasta, cbteTipo, ptoVenta, nroComp, resultado))
                    conn.get_connection().conn.commit()
                    logging.info("Registro insertado correctamente en Sybase: afipws_fe_log.")
                elif destino == 2:

                    fecha_hora = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    err = errorMsg.strip('"')
                    errorDet = err.replace("str", "")

                    sql = "INSERT INTO afipws_fe_errores_log  (FechayHora, mensaje, codigoError, metodoAfip, operador) VALUES ('"+str(fecha_hora)+"',  '"+errorDet+"', '"+str(errorCodigo)+"', '"+str(metodo)+"', '"+str(id_usuario)+"') "
                    cursor.execute(sql )
                    conn.get_connection().conn.commit()
                    logging.info("Registro  insertado correctamente en Sybase: afipws_fe_errores_log.")




                return True
            except Exception as e:
                logging.error(f"Error al insertar en afipws_fe_errores_log: {e}")
                return False

        else:
            logging.info(":: ATENCION !! No se graba en la base de datos de facturación nueva ::")

    def traerComprobante(self, id_usuario, comprobante=None):
        fechaTemp = str(comprobante["cbteFch"])
        fecha = datetime.strptime(fechaTemp, "%Y-%m-%d").strftime("%Y%m%d")
        nro_comprobante = comprobante["idFactCab"]
        nro_fac_cab_asoc = comprobante["idFactCabRelacionado"]
        #debo buscar el punto de venta por el idFactCab y el tipo de comprobante
        pto_venta = comprobante["cbtePtoVta"]
        tipo_comprobante = comprobante["cbteTipo"]


        if not all([nro_comprobante, id_usuario]):
            logging.error("Error: Uno o más campos requeridos no tienen un valor válido.")
            return None

        logging.info(":: TRAER COMPROBANTE ::")

        try:
            conn = ConectorManagerDB(1)
            if conn.get_connection().conn is None:
                print("❌ No se pudo establecer conexión con la base de datos.")
            else:
                print("✅ Conexión establecida correctamente.")
            with conn.get_connection().conn.cursor() as cursor:
                # Consulta principal
                query = """SELECT IdPadron, Concepto, DocTipo, DocNro, CbteDesde, CbteHasta, CbteFch, ImpOpEx, 
                           ImpTotal, ImpTotConc, ImpNeto, ImpTrib, ImpIVA, FchServDesde, FchServHasta, 
                           FchVtoPago, MonId, MonCotiz, NumeroComprobanteArca
                           FROM v_afipws_fe_master WHERE idFactCab = %s"""
                cursor.execute(query, (nro_comprobante,))
                resu = cursor.fetchone()

                if not resu:
                    logging.error("No se encontró el comprobante.")
                    return None

                columnasDet = ["IdPadron","Concepto", "DocTipo", "DocNro", "CbteDesde", "CbteHasta", "CbteFch", "ImpOpEx",
                               "ImpTotal", "ImpTotConc", "ImpNeto", "ImpTrib", "ImpIVA", "FchServDesde", "FchServHasta",
                               "FchVtoPago", "MonId", "MonCotiz", "NumeroComprobanteArca"]
                resultado = dict(zip(columnasDet, resu))
                campos_importe = ["ImpTotal", "ImpTotConc", "ImpNeto", "ImpTrib", "ImpIVA"]
                for campo in campos_importe:
                    if campo in resultado and resultado[
                        campo] is not None:  # Verificar que el campo existe y no es None
                        resultado[campo] = Decimal(resultado[campo]).quantize(Decimal('0.00'))

                print(resultado)

            tieneIva = "S" if resultado["ImpIVA"] > 0 else "N"
            tieneTributos = "S" if resultado["ImpTrib"] > 0 else "N"

            # Buscar tipo de documento en el padrón si es necesario
            padronCodigo = resultado["IdPadron"]
            if resultado["DocTipo"] == 0:
                with conn.get_connection().conn.cursor() as cursor:

                    query = """SELECT cuit, CASE WHEN LENGTH(cuit) = 11 THEN 80 ELSE 96 END AS codigo_documento FROM PadronGral WHERE idPadronGral = %s"""
                    cursor.execute(query, (padronCodigo,))
                    resu_tipodoc = cursor.fetchone()
                    if resu_tipodoc:
                        resultado["DocTipo"] = resu_tipodoc[1]
                    else:
                        logging.warning("No se encontró el tipo de documento para el CUIT proporcionado.")






            # Obtener datos de IVA
            iva = []
            if tieneIva == "S":
                with conn.get_connection().conn.cursor() as cursor:
                    queryIva = """SELECT detalle, porcentaje, importe, baseImponible, AfipWsTiposIva.idTiposIva AS afipId 
                                  FROM FactPie, AfipWsTiposIva 
                                  WHERE FactPie.idFactCab = %s AND FactPie.idSisTipoModelo = 2 
                                  AND AfipWsTiposIva.alicuota = FactPie.porcentaje"""
                    cursor.execute(queryIva, (nro_comprobante,))

                    resultadoIva = cursor.fetchall()
                    for item in resultadoIva:
                        iva.append({
                            "Id": int(item[4]) if item[4] is not None else 0,
                            "BaseImp": float(item[3]) if item[3] is not None else 0.0,
                            "Importe": float(item[2]) if item[2] is not None else 0.0
                        })

            # Obtener datos de tributos
            tributos_items = []
            if tieneTributos == "S":
                with conn.get_connection().conn.cursor() as cursor:
                    queryTributos = """SELECT detalle, porcentaje, importe, baseImponible, AfipWsTiposIva.idTiposIva AS afipId 
                                       FROM FactPie, AfipWsTiposIva 
                                       WHERE idFactCab = %s AND idSisTipoModelo <> 2 
                                       AND AfipWsTiposIva.alicuota = FactPie.porcentaje"""
                    cursor.execute(queryTributos, (nro_comprobante,))
                    resultadoTributos = cursor.fetchall()
                    for item in resultadoTributos:
                        tributos_items.append({
                            "Id": int(item[4]) if item[4] is not None else 0,
                            "Desc": str(item[0]),
                            "BaseImp": float(item[3]) if item[3] is not None else 0.0,
                            "Alic": float(item[1]) if item[1] is not None else 0.0,
                            "Importe": float(item[2]) if item[2] is not None else 0.0
                        })


            # CBTES ASOCIADOS
            cbtes_asoc = []
            if nro_fac_cab_asoc is not None and nro_fac_cab_asoc > 0:
                    # Traer datos de la cabecera del comprobante asociado
                conn = ConectorManagerDB(1)
                with conn.get_connection().conn.cursor() as cursor:
                    sql_cab = """SELECT ABS(RIGHT(numeroAfip, 8)) AS  CNroAsoc, CAST(LEFT(numeroAfip, 4) AS UNSIGNED) AS PVtaAsoc, codigoAfip AS CbteTipoAsoc, cuit AS CuitAsoc FROM FactCab WHERE idFactCab = %s"""

                    cursor.execute(sql_cab, (nro_fac_cab_asoc,))
                    resuCab = cursor.fetchall()

                    for item in resuCab:
                        cbte_item = {
                            "Nro": int(item[0]),  # Número comprobante asociado
                            "PtoVta": int(item[1] // 1000),  # Punto de venta asociado
                            "Tipo": int(item[2]),  # Tipo de comprobante asociado
                            "Cuit": int(item[3])  # Número de comprobante
                        }
                        cbtes_asoc.append(cbte_item)

            periodo_asoc = []
            opcionales =[]
            # Construir datos finales
            datos_cabecera = {
                "PtoVta": pto_venta,
                "CbteTipo": tipo_comprobante,
                "CantReg": 1,
            }
            """datos_master = {
                columnasDet: (str(valor) if isinstance(valor, (Decimal, date)) else valor)
                for columnasDet, valor in zip(columnasDet, resultado)
            }"""






            datos_master = {
                columnasDet[i]: (str(valor) if isinstance(valor, (Decimal, date)) else valor)
                for i, valor in enumerate(resultado.values())
            }

            if iva:
                datos_master["Iva"] = {"AlicIva": iva}
            else:
                datos_master["Iva"] = None
            if cbtes_asoc:
                datos_master["CbtesAsoc"] = {"CbteAsoc": cbtes_asoc}
            else:
                datos_master["CbtesAsoc"] = None
            if opcionales:
                datos_master["Opcionales"] = {"Opcional": opcionales}
            else:
                datos_master["Opcionales"] = None

            if periodo_asoc:
                datos_master["PeriodoAsoc"] = periodo_asoc
            else:
                datos_master["PeriodoAsoc"] = None
            if tributos_items:
                datos_master["Tributos"] = {"Tributo": tributos_items}
            else:
                datos_master["Tributos"] = None

            if resultado["DocTipo"] == 80:
                conn = ConectorManagerDB(1)
                with conn.get_connection().conn.cursor() as cursor:
                    # Consulta principal
                    query = """SELECT idSisSitIVA FROM v_afipws_fe_master WHERE idFactCab = %s"""
                    cursor.execute(query, (nro_comprobante,))
                    resu = cursor.fetchone()
                    if resu is None:
                        condicionIVAReceptorId = 4
                    else:
                        condicionIVAReceptorId = resu[0]

            else:
                condicionIVAReceptorId = 4

            datos_master["CondicionIVAReceptorId"] = int(condicionIVAReceptorId)
            json_unificado = json.dumps({
                "FeCabReq": datos_cabecera,
                "FeDetReq": datos_master
            }, indent=4, ensure_ascii=False)

            return json_unificado

        except Exception as e:
            logging.error(f"Error en traerComprobante: {e}")
            return None



    def traerComprobanteSybase(self, id_usuario, comprobante=None):
        nro_comprobante = comprobante["cbteNro"]
        pto_venta = comprobante["cbtePtoVta"]
        tipo_comprobante = comprobante["cbteTipo"]
        fechaTemp = str(comprobante["cbteFch"])
        fecha = datetime.strptime(fechaTemp, "%Y-%m-%d").strftime("%Y%m%d")

        conn = ConectorManagerDB(2)
        cursor = conn.get_connection().conn.cursor()

        # Verificar valores nulos
        if nro_comprobante is None:
            logging.error("Error: 'Número de Comprobante' no tiene un valor válido.")
        if pto_venta is None:
            logging.error("Error: 'Punto de Venta' no tiene un valor válido.")
        if tipo_comprobante is None:
            logging.error("Error: 'Tipo de Comprobante' no tiene un valor válido.")
        if fecha is None:
            logging.error("Error: 'Fecha del Comprobante' no tiene un valor válido.")

        try:
            query = ("SELECT Concepto, DocTipo, DocNro, CbteDesde, CbteHasta, "
                     "REPLACE(CAST(CbteFch AS VARCHAR), '-', '') AS CbteFch, "
                     "ImpTotal, ImpTotConc, ImpNeto, ImpOpEx, ImpTrib, ImpIVA, "
                     "REPLACE(CAST(FchServDesde AS VARCHAR), '-', '') AS FchServDesde, "
                     "REPLACE(CAST(FchServHasta AS VARCHAR), '-', '') AS FchServHasta, "
                     "REPLACE(CAST(FchVtoPago AS VARCHAR), '-', '') AS FchVtoPago, "
                     "MonId, MonCotiz, v_numero_comprobante "
                     "FROM afipws_fe_master  WHERE  CbteDesde = %s AND CbteTipo = %s AND PtoVta = %s AND  "
                     "REPLACE(CAST(CbteFch AS VARCHAR), '-', '') = %s AND Resultado <> 'A'")


            cursor.execute(query, (nro_comprobante, tipo_comprobante, pto_venta, fecha))
            resultado = cursor.fetchall()

            if not resultado:
                print("⚠ No se encontraron resultados para la consulta.")
                self.grabarRespuestaARCA(2, id_usuario, 500, "TraerComprobanteSybase","No se encontraron el comprobante "+str(nro_comprobante)+" en afipws_fe_master para la consulta.", nro_comprobante)

            else:
                for row in resultado:
                    print(row)

        except Exception as e:
            self.grabarRespuestaARCA(2, id_usuario, 500, "TraerComprobanteSybase","e produjo un error al ejecutar la consulta sql en afipws_fe_master", comprobante)
            print(f"❌ Se produjo un error al ejecutar la consulta sql: {str(e)}")

        tieneIva = "N"
        tieneTributos ="N"
        iva = []
        tributos_items = []
        if resultado[11] > 0:
            tieneIva = "S"
        if resultado[10] > 0:
            tieneTributos = "S"


        columnasDet = [
            "Concepto", "DocTipo", "DocNro", "CbteDesde", "CbteHasta", "CbteFch", "ImpTotal", "ImpTotConc", "ImpNeto",
            "ImpOpEx", "ImpTrib", "ImpIVA", "FchServDesde", "FchServHasta", "FchVtoPago", "MonId", "MonCotiz",
            "NumeroComprobanteArca"
        ]

        # IVA
        if tieneIva == "S":
            queryIva = (
                    "SELECT TipoDetalle, Pase, Id, AsocPtoVta, AsocNroCbte, Valor, BaseImp, Alic, importe, descriTributo "
                    "FROM afipws_fe_detalle WHERE CbteDesde = " + str(nro_comprobante) +
                    " AND CbteTipo = " + str(tipo_comprobante) +
                    " AND PtoVta = " + str(pto_venta) +
                    " AND id > 1"
            )
            cursor.execute(queryIva)
            resultadoIva = cursor.fetchall()

            for item in resultadoIva:
                iva_item = {
                    "Id": int(item[2]),  # Convertir Id a entero
                    "BaseImp": float(item[6]),  # Convertir BaseImponible a flotante
                    "Importe": float(item[8])  # Convertir Importe a flotante
                }
                iva.append(iva_item)


        if tieneTributos == "S":
            queryTributos = (
                    "SELECT TipoDetalle, Pase, Id, AsocPtoVta, AsocNroCbte, Valor, BaseImp, Alic, importe, descriTributo "
                    "FROM afipws_fe_detalle WHERE CbteDesde = " + str(nro_comprobante) +
                    " AND CbteTipo = " + str(tipo_comprobante) +
                    " AND PtoVta = " + str(pto_venta) +
                    " AND id = 1"
            )
            cursor.execute(queryTributos)
            resultadoTributos = cursor.fetchall()

            for item in resultadoTributos:
                tributo_item = {
                    "Id": int(item[2]),
                    "Desc": str(item[9]),
                    "BaseImp": float(item[6]),
                    "Alic": float(item[7]),
                    "Importe": float(item[8]),
                }
                tributos_items.append(tributo_item)




        # CBTES ASOCIADOS
        if  resultado[17] == None:
            numeroComprobanteArca = 0
        else:
            numeroComprobanteArca = resultado[17]
        queryAsoc = (
                "SELECT * FROM afipws_fe_CbtesAsociados WHERE CTipoAsoc = " + str(tipo_comprobante) +
                " AND PVtaAsoc = " + str(pto_venta) +
                " AND CNroAsoc = " + str(numeroComprobanteArca) +
                " AND CbteNro = " + str(nro_comprobante)
        )
        cursor.execute(queryAsoc)
        resultadoAsoc = cursor.fetchall()

        # Construcción del JSON de comprobantes asociados
        cbtes_asoc = []
        for item in resultadoAsoc:
            cbte_item = {
                "CTipoAsoc": int(item[0]),  # Tipo de comprobante asociado
                "PVtaAsoc": int(item[1]),  # Punto de venta asociado
                "CNroAsoc": int(item[2]),  # Número comprobante asociado
                "CbteNro": int(item[3])  # Número de comprobante
            }
            cbtes_asoc.append(cbte_item)

        # Opcionales
        queryOpcionales = (
                "SELECT Id, Valor FROM afipws_fe_Opcionales WHERE CbteNro = " + str(nro_comprobante) +
                " AND PtoVta = " + str(pto_venta)
        )
        cursor.execute(queryOpcionales)
        resultadoOpcionales = cursor.fetchall()
        opcionales = []
        for item in resultadoOpcionales:
            opcional_item = {
                "Id": str(item[0]),  # ID del opcional (convertido a string)
                "Valor": str(item[1])  # Valor asociado al opcional
            }
            opcionales.append(opcional_item)

        # Periodos asociados
        queryPeriodoAsoc = (
                "SELECT REPLACE(fechadesde,'-', ''), REPLACE(fechahasta, '-', '') FROM afipws_fe_CbtesAsociados_periodo WHERE CbteNro = " + str(
            nro_comprobante) +
                " AND CbteTipo = " + str(tipo_comprobante) +
                " AND PtoVta = " + str(pto_venta)
        )
        cursor.execute(queryPeriodoAsoc)
        resultadoPeriodoAsoc = cursor.fetchall()

        # Construcción del JSON de PeriodoAsoc
        periodo_asoc = []
        for item in resultadoPeriodoAsoc:
            periodo_item = {
                "FchDesde": str(item[0]),
                "FchHasta": str(item[1])
            }
            periodo_asoc.append(periodo_item)

        # Convertir los datos en un diccionario
        datos_cabecera = {
            "PtoVta": pto_venta,
            "CbteTipo": tipo_comprobante,
            "CantReg": 1,
        }

        datos_master = {
            columnasDet: (str(valor) if isinstance(valor, (Decimal, date)) else valor)
            for columnasDet, valor in zip(columnasDet, resultado)
        }
        if datos_master["DocTipo"] == str(80):
            cuit =  datos_master["DocNro"]
            query_iva_con = ("SELECT v_condicion_iva FROM fac_ventas where v_numero_comprobante = "+str(nro_comprobante)+" and "
             "pto_numero = "+str(pto_venta)+" and v_tipo_comprobante = "+str(tipo_comprobante)+" and REPLACE(v_fecha_operacion, '-', '') = '"+str(fecha)+"' and v_codigo = 'CIERRE'")
            print(query_iva_con)
            cursor.execute(query_iva_con)
            conIvaRecept = cursor.fetchone()
            if conIvaRecept is None:
                condicionIVAReceptorId = 4
            else:
                condicionIVAReceptorId = str(conIvaRecept[0])
        else:
            condicionIVAReceptorId = 4

        if iva:
            datos_master["Iva"] = {"AlicIva": iva}
        else:
            datos_master["Iva"] = None
        if cbtes_asoc:
            datos_master["CbtesAsoc"] = {"CbteAsoc": cbtes_asoc}
        else:
            datos_master["CbtesAsoc"] = None
        if opcionales:
            datos_master["Opcionales"] = {"Opcional": opcionales}
        else:
            datos_master["Opcionales"] = None

        if periodo_asoc:
            datos_master["PeriodoAsoc"] = periodo_asoc
        else:
            datos_master["PeriodoAsoc"] = None
        if tributos_items:
            datos_master["Tributos"] = {"Tributo": tributos_items}
        else:
            datos_master["Tributos"] = None

        datos_master["CondicionIVAReceptorId"] = int(condicionIVAReceptorId)
        json_unificado = json.dumps({
            "FeCabReq": datos_cabecera,
            "FeDetReq": datos_master
        }, indent=4, ensure_ascii=False)
        return json_unificado















"""if __name__ == "__main__":
    afipClient = Afip()
    resultado = afipClient.login()
    print(resultado)"""