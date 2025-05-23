import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, date
import re
import ssl
from decimal import Decimal
from idlelib import history

from requests import Session
from SSLAdapter import SSLAdapter

from zeep.helpers import serialize_object
from requests.adapters import HTTPAdapter
from conectorManagerDB import ConectorManagerDB
import zeep
from zeep import Client
from zeep.transports import Transport
from tokens import Tokens as tok
import requests
from dotenv import load_dotenv
from afipWsaaClient import AfipWsaaClient as afipClient

# Crear un contexto SSL personalizado que permita claves DH pequeñas
ssl_context = ssl.create_default_context()
ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")  # Reducir el nivel de seguridad para aceptar claves DH pequeñas

# Configurar el registro de depuración
#logging.basicConfig(level=logging.DEBUG)
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
                    logging.error(f"❌ Error en la respuesta de AFIP: {response.Errors}")
                    return {"control": "ERROR", "mensaje": f"Error en respuesta de AFIP: {response.Errors}"}
                else:
                    logging.info("✅ "+str(endPonintNombre)+": Solicitud enviada correctamente.")
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
                    logging.error(f"❌ Error en la respuesta de AFIP: {response.Errors}")
                    return {"control": "ERROR", "mensaje": f"Error en respuesta de AFIP: {response.Errors}"}
                else:
                    logging.info("✅ "+str(endPonintNombre)+": Solicitud enviada correctamente.")
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
                    logging.error(f"❌ Error en la respuesta de AFIP: {response.Errors}")
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




    def autorizarComprobante(self, id_usuario, comprobante=None):

        """
        Antes que todo me fijo si la petición viene del sistema web de facturación
        o del sistema sybase de facturacion
        """
        if self.plataforma == 1:
            comprobante =self.traerComprobante(comprobante)

        elif self.plataforma == 2:
            # en comprobante va a venir el nro de comrpbaonte
            comprobante = self.traerComprobanteSybase(id_usuario, comprobante)
            if comprobante is None:
                logging.error("❌ El comprobante a autorizar no pudo ser detectado")
                self.grabarRespuestaARCA(2, id_usuario, 400, "FECAESolicitar", "El comprobante a autorizar no pudo ser detectado")
                return {"control": "ERROR", "codigo": "400", "mensaje": "El comprobante a autorizar no pudo ser detectado"}



        from facturacion_router import validarToken
        tok = validarToken(id_usuario)
        if tok["token"] is not None:
            try:
                if not tok["token"] or not tok["sign"]:
                    raise Exception("No estás autenticado. Llama al método `autenticar` primero.")
                # Busco el ultimo comprobante autorizado:
                comprobante_dict = json.loads(comprobante)
                cabecera = comprobante_dict.get("FeCabReq", {})
                detalle = comprobante_dict.get("FeDetReq", {})
                punto_venta = cabecera["PtoVta"]
                tipo_comp =  cabecera["CbteTipo"]
                cantidad = cabecera["CantReg"]



                ultimo = self.ultimoComprobanteAutorizado(id_usuario, punto_venta, tipo_comp)
                if ultimo["CbteNro"] is None:
                    if self.plataforma == 2:
                        #self, destino, id_usuario, errorCodigo, metodo,  errorMsg, params=None
                        self.grabarRespuestaARCA(2, id_usuario, ultimo["Code"], "FECompUltimoAutorizado", ultimo["Errors"], "U")
                        logging.error("Error: "+str(ultimo["Code"])+", Error: "+str(ultimo["Errors"]))
                    return {"control": "ERROR", "codigo": "400", "mensaje": f"Error no se encontró el último comprobante autorizado: {ultimo['Errors']}"}
                    raise Exception("No se encontró el último comprobante autorizado con el tipo de comprobante"+str(datos_factura["tipoComprobante"])+" y punto de venta: "+str(datos_factura["ptoVenta"])+".")
                metodo = "POST"
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
                        print("CbtesAsoc: " + str(detalle["CbtesAsoc"]))
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
                                CbtesAsoc= detalle["Tributos"],
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

                        self.autorizarComprobanteRespuesta(id_usuario, response, comprobante, nroComprobanteInterno)

                except Exception as e:
                    return self.autorizarComprobanteRespuesta(id_usuario, response, comprobante)

            except Exception as e:

                logging.error(f"Error enviando factura a "+str(self.nombre_entidad)+": "+str({e}))
                raise Exception(f"Error enviando factura a "+str(+str(self.nombre_entidad))+": "+str(e))


    def reautorizarComprobante(self, id_usuario, comprobante=None):
        print(":: REAUTORIZAR COMPROBANTE ::")

    def autorizarComprobanteRespuesta(self, id_usuario, respuesta, comprobante=None, nro_comp_interno=0):
        try:
            # Verificar si hay errores
            if respuesta["Errors"]:
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

                else:
                    return json.dumps({
                        "control": "ERROR",
                        "codigo": "400",
                        "mensaje": "Se encontraron errores en la respuesta de " + str(self.nombre_entidad) + ".",
                        "errores": [{"codigo": err["Code"], "mensaje": err["Msg"]} for err in errores]
                    }, indent=4, ensure_ascii=False)




               #logging.error(respuesta["Errors"]["Err"][0]["Msg"])
            # Verificar si el comprobante fue generado con éxito
            elif hasattr(respuesta, "FeCabResp") and respuesta.FeCabResp:
                # Verificar si el resultado es exitoso

                if hasattr(respuesta.FeCabResp, "Resultado") and respuesta.FeCabResp.Resultado == "A":
                    logging.info("✅ Comprobante autorizado con éxito !!")
                    if self.plataforma == 2:
                        self.actualizarComprobanteSybase(id_usuario, comprobante, respuesta, nro_comp_interno)
                    else:
                        self.actualizarComprobante(id_usuario, comprobante, respuesta, nro_comp_interno)

                    #self.g(id_usuario, respuesta, comprobante)

                else:
                    # Comprobante no autorizado
                    observaciones = [
                        {"Code": obs.Code, "Msg": obs.Msg} for obs in
                        respuesta.FeDetResp.FECAEDetResponse[0].Observaciones.Obs
                    ]
                    logging.error("❌ Comprobante no autorizado.")
                    if self.plataforma == 2:
                        self.borraErrorARCASybase(1, id_usuario, comprobante)
                        h=0
                        for fila in observaciones:
                            print(f"Código: {fila['Code']}, Mensaje: {fila['Msg']}")
                            msg = "Comprobante no autorizado"+": "+fila["Msg"]+" (Codigo: "+str(fila["Code"])+")"
                            self.grabarRespuestaARCA(1, id_usuario, 400, "FECAESolicitar", msg, comprobante, "E")
                            h = h+1
                            logging.info("Ver tabla afipws_fe_log: "+msg)
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
                    "mensaje": "El comprobante no fue generado con éxito.",
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





    def actualizarComprobante(self, id_usuario, comprobante_original, respuesta, nro_comp_interno=0):
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
                # print(f"Código: {observacion_code} - Mensaje: {observacion_msg}")
        else:
            print("No hay observaciones registradas.")

        # Mostrar valores extraídos
        print(f"Cuit: {cuit}, PtoVta: {pto_vta}, CbteTipo: {cbte_tipo}")
        print(f"Fecha Proceso: {fch_proceso}, CantReg: {cant_reg}, Resultado: {resultado}, Reproceso: {reproceso}")
        print(f"Concepto: {concepto}, DocTipo: {doc_tipo}, DocNro: {doc_nro}")
        print(f"CbteDesde: {cbte_desde}, CbteHasta: {cbte_hasta}, CbteFch: {cbte_fch}, Resultado: {resultado_det}")
        print(f"CAE: {cae}, CAE Fch Vto: {cae_fch_vto}")
        print(f"Observación Code: {observacion_code}, Observación Msg: {observacion_msg}")

        conn = ConectorManagerDB(1)
        cursor = conn.get_connection().conn.cursor()
        # Debo actualizar de la cabecera 'FactCab' los campos  numeroAfip, cai, caiVto"
        # SELECT numeroAfip, cai, caiVto FROM FactCab

        print("Actualiza tablas FacCab de facturacion nueva")





    def validarConexion(self):
        """Valida la conexión con el servicio de AFIP"""
        try:
            logging.info("Validando conexión con el servicio de AFIP...")
            endPointNombre = "FEDummy"
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



        nro_comprobante = comprobante["idFactCab"]
        nro_comprobante_asoc = comprobante["idFactCabRelacionado"]

        conn = ConectorManagerDB(1)
        cursor = conn.get_connection().conn.cursor()
        query = "SELECT idCteTipo, letra, codigoAfip, numero, fechaEmision, fechaVto, fechaConta, codBarra, idPadron, idProductoCanje, precioReferenciaCanje, interesCanje, idMoneda, nombre, cuit, sitIVA, codigoPostal,idListaPrecios,  cotDolar, fechaDolar, Observaciones, idSisTipoOperacion, idVendedor, idSisOperacionComprobantes,  domicilio, idDepositoDestino, idRelacionCanje, kilosCanje, idCteNumerador, pesificado, dolarizadoAlVto, interesMensualCompra canjeInsumos, tipoCambio, estadoCerealSisa, porcentajePercep2459, cerealCanje, diferidoVto, interesMensualPesificado, marcaPesificado FROM FactCab WHERE idFactCab = %s"
        cursor.execute(query, (nro_comprobante,))
        resultado = cursor.fetchone()
        if resultado:
            id_cte_tipo = resultado[0]
            letra = resultado[1]
            codigo_afip = resultado[2]
            numero = resultado[3]
            fecha_emision = resultado[4]
            fecha_vto = resultado[5]
            fecha_conta = resultado[6]
            cod_barra = resultado[7]
            id_padron = resultado[8]
            id_producto_canje = resultado[9]
            precio_referencia_canje = resultado[10]
            interes_canje = resultado[11]
            id_moneda = resultado[12]
            nombre = resultado[13]
            cuit = resultado[14]
            sit_iva = resultado[15]
            codigo_postal = resultado[16]
            id_lista_precios = resultado[17]
            cot_dolar = resultado[18]
            fecha_dolar = resultado[19]
            observaciones = resultado[20]
            id_sis_tipo_operacion = resultado[21]
            id_vendedor = resultado[22]
            id_sis_operacion_comprobantes = resultado[23]
            domicilio = resultado[24]
            id_deposito_destino = resultado[25]
            id_relacion_canje = resultado[26]
            kilos_canje = resultado[27]
            id_cte_numerador = resultado[28]
            pesificado = resultado[29]
            dolarizado_al_vto = resultado[30]
            interes_mensual_compra_canje_insumos = resultado[31]
            tipo_cambio = resultado[32]
            estado_cereal_sisa = resultado[33]
            porcentaje_percep_2459 = resultado[34]
            cereal_canje = resultado[35]
            diferido_vto = resultado[36]
            interes_mensual_pesificado = resultado[37]
            marca_pesificado = resultado[38]

            # Mostrar los datos
            print(f"Letra: {letra}, Número: {numero}, Fecha de emisión: {fecha_emision}")
            print(f"Nombre: {nombre}, CUIT: {cuit}, Código postal: {codigo_postal}")
            print(f"Observaciones: {observaciones}, Tipo de cambio: {tipo_cambio}, Pesificado: {pesificado}")
        else:
            print(f"No se encontró el comprobante con id {nro_comprobante}")



        # leo la cabecera por idFactCab

        fechaTemp = str(comprobante["cbteFch"])
        fecha = datetime.strptime(fechaTemp, "%Y-%m-%d").strftime("%Y%m%d")

        tipo_comprobante = 0
        fechaTemp = str(comprobante["cbteFch"])

        # Verificar valores nulos



        datos_cabecera = ""
        datos_detalle = ""
        """
        query = ("SELECT Concepto, DocTipo, DocNro, CbteDesde, CbteHasta, REPLACE(CbteFch, '-', '') AS CbteFch,  ImpTotal, ImpTotConc, ImpNeto, ImpOpEx, "
                "ImpTrib, ImpIVA, REPLACE(FchServDesde, '-', '') AS FchServDesde, REPLACE(FchServHasta, '-', '') AS FchServHasta, REPLACE(FchVtoPago, '-', '') AS FchVtoPago, MonId, MonCotiz, v_numero_comprobante"
                " FROM  afipws_fe_master WHERE CbteDesde = " + str(nro_comprobante) +
                " AND CbteTipo = " + str(tipo_comprobante) +
                " AND PtoVta = " + str(pto_venta) +
                "AND Resultado <> 'A' " +
                "AND REPLACE(CbteFch, '-', '') = '" + str(fecha) + "'"
        )
        # AGREGAR AL QUERY --> and Resultado <> A LUEGO
        cursor.execute(query)
        resultado = cursor.fetchall()[0]
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
        """
        json_unificado = json.dumps({
            "FeCabReq": datos_cabecera,
            "FeDetReq": datos_master
        }, indent=4, ensure_ascii=False)
        return json_unificado



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

        query = ("SELECT Concepto, DocTipo, DocNro, CbteDesde, CbteHasta, REPLACE(CbteFch, '-', '') AS CbteFch,  ImpTotal, ImpTotConc, ImpNeto, ImpOpEx, "
                "ImpTrib, ImpIVA, REPLACE(FchServDesde, '-', '') AS FchServDesde, REPLACE(FchServHasta, '-', '') AS FchServHasta, REPLACE(FchVtoPago, '-', '') AS FchVtoPago, MonId, MonCotiz, v_numero_comprobante"
                " FROM  afipws_fe_master WHERE CbteDesde = " + str(nro_comprobante) +
                " AND CbteTipo = " + str(tipo_comprobante) +
                " AND PtoVta = " + str(pto_venta) +
                "AND Resultado <> 'A' " +
                "AND REPLACE(CbteFch, '-', '') = '" + str(fecha) + "'"
        )
        # AGREGAR AL QUERY --> and Resultado <> A LUEGO
        cursor.execute(query)
        resultado = cursor.fetchall()[0]
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