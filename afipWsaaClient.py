import base64
import os
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xmlrpc.client import Fault

import requests
import urllib3
from requests import Session
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree
import logging
import subprocess
from zeep import Client
from zeep.transports import Transport
from dotenv import load_dotenv
load_dotenv()

class AfipWsaaClient:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @staticmethod
    def invoke_wsaa(login_ticket_request_cms, wsdl_url):
        """Llama al servicio Web de AFIP usando Zeep"""
        try:
            # 🔹 Codificar el ticket de autenticación en Base64
            # 🔹 Validar que el ticket de autenticación no sea `None`
            if login_ticket_request_cms is None:
                raise ValueError("El login_ticket_request_cms es None. No se puede procesar.")

            else:
                encoded_request = base64.b64encode(login_ticket_request_cms).decode("utf-8")
                # 🔹 Inicializar cliente Zeep con el WSDL del servicio
                session = Session()
                session.verify = False  # 🔹 Omitir verificación SSL si es necesario
                transport = Transport(session=session)
                client = Client(wsdl_url, transport=transport)

                # 🔹 Llamar al método SOAP "loginCms" con el ticket en Base64
                response = client.service.loginCms(encoded_request)

                # 🔹 Verificar si hay error en la respuesta SOAP
            if "<soapenv:Fault>" in response:
                raise Exception(f"Error en la respuesta SOAP: {response}")

            return response

        except Exception as e:
            logging.error(f"Error invocando WSAA con Zeep: {str(e)}")
            raise  # 🔹 Relanza la excepción para manejarla en otro nivel



    """
    def invoke_wsaa(login_ticket_request_cms, endpoint):
        try:
            encoded_request = base64.b64encode(login_ticket_request_cms).decode("utf-8")
            headers = {
                'Content-Type': 'application/xml',
                'SOAPAction': '"loginCms"',

            }
            # aca probar con zeep para servicios web soap
            response = requests.post(endpoint, data=encoded_request, headers=headers)

            if response.status_code == 200:
                # Procesar la respuesta del servicio
                if "<soapenv:Fault>" in response.text:
                    raise Exception(f"Error en la respuesta SOAP: {response.text}")
                return response.text
            else:
                raise Exception(f"Error en el servicio WSAA: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Error invocando WSAA: {str(e)}")
            raise  # Relanza la excepción para que sea manejada en otro nivel
    
    """

    @staticmethod
    def obtenerNuevoTokenAcceso(certificate, keyStore, wsdl_url):
        # Cargar el certificado y la clave privada
        try:
            ticket_obj = AfipWsaaClient.cargar_certificado_final(certificate, keyStore, wsdl_url)
            return ticket_obj
        except Exception as e:
            logging.error(json.dumps({"control": "ERROR", "codigo": "400", "mensaje": str(e.strerror)}))
            return json.dumps({"control": "ERROR", "codigo": "400", "mensaje": str(e.strerror)})
            raise Exception({"control": "ERROR", "codigo": "400", "mensaje": str(e.strerror)})









    def cargar_certificado_final(certificate, private_key,wsdl_url):
        print(f"Ruta del certificado: {os.path.abspath(certificate)}")
        print(f"Ruta de la clave privada: {os.path.abspath(private_key)}")

        certificate2 = r"H:\Dario\Proyectos\Python\kernel\ws-rest\facturacion-electronica\afip\certificado\homo\dQuiroga25.crt"
        private_key2 = r"H:\Dario\Proyectos\Python\kernel\ws-rest\facturacion-electronica\afip\certificado\homo\dQuiroga25.key"

        print(f"Certificado existe: {os.path.exists(certificate2)}")
        print(f"Clave privada existe: {os.path.exists(private_key2)}")

        print(f"Permisos de lectura Certificado: {os.access(certificate2, os.R_OK)}")
        print(f"Permisos de lectura Clave privada: {os.access(private_key2, os.R_OK)}")

        if not os.path.exists(certificate):
            logging.error(f"El archivo de certificado no existe: {certificate}")
            raise FileNotFoundError(f"El archivo de certificado no existe: {certificate}")
        if not os.path.exists(private_key):
            logging.error(f"El archivo de clave privada no existe: {private_key}")
            raise FileNotFoundError(f"El archivo de clave privada no existe: {private_key}")

        servicio_id = "wsfe"
        dt_now = datetime.now()

        # Crear el XML de Ticket de Acceso con ElementTree
        root = ET.Element("loginTicketRequest")
        header = ET.SubElement(root, "header")
        ET.SubElement(header, "uniqueId").text = dt_now.strftime("%y%m%d%H%M")
        ET.SubElement(header, "generationTime").text = (dt_now - timedelta(minutes=10)).isoformat()
        ET.SubElement(header, "expirationTime").text = (dt_now + timedelta(minutes=10)).isoformat()
        ET.SubElement(root, "service").text = servicio_id

        xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        # Firmar el XML con OpenSSL y obtener CMS en Base64
        try:
            signed_cms = subprocess.run([
                "openssl", "cms", "-sign",
                "-signer", certificate,
                "-inkey", private_key,
                "-nodetach",
                "-outform", "der"
            ], input=xml_str, stdout=subprocess.PIPE, check=True).stdout

            cms_b64 = base64.b64encode(signed_cms).decode("utf-8")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error al firmar CMS: {str(e)}")

        # Validar que el CMS en Base64 no esté vacío
        if not cms_b64.strip():
            raise ValueError("El CMS firmado está vacío o no se generó correctamente.")

        # Construcción del XML SOAP de forma estructurada
        soap_root = ET.Element("soapenv:Envelope", {
            "xmlns:soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
            "xmlns:ws": "http://wsaa.view.service/"
        })
        ET.SubElement(soap_root, "soapenv:Header")
        body = ET.SubElement(soap_root, "soapenv:Body")
        login_cms = ET.SubElement(body, "ws:loginCms")
        in0 = ET.SubElement(login_cms, "in0")
        in0.text = cms_b64
        # 🔹 Convertir el XML `string` en un objeto `lxml.etree.Element`



        try:
            print("-------------------------------------------------------------------")
            # 🔹 Configurar Zeep sin verificación SSL y con headers personalizados
            session = Session()
            session.verify = False  # 🔹 Evita errores de certificado en entorno de prueba
            session.headers.update({
                "Content-Type": "application/xml; charset=utf-8",
                "SOAPAction": '"loginCms"'
            })
            transport = Transport(session=session)

            # 🔹 Asegurar que la URL ya tenga `?wsdl`
            if not wsdl_url.endswith("?wsdl"):
                wsdl_url += "?wsdl"

            # 🔹 Inicializar el cliente Zeep
            client = Client(wsdl_url, transport=transport)

            # 🔹 Enviar solo el contenido CMS firmado, no un XML completo
            response = client.service.loginCms(cms_b64)

            # 🔹 Validar la respuesta
            if response is None:
                raise ValueError("Error: La respuesta del WSAA es inválida.")

            return response  # 🔹 Retorna la respuesta procesada automáticamente

        except Fault as fault:  # 🔹 Manejo de errores SOAP específicos de Zeep
            return {"control": "ERROR", "mensaje": f"WSAA devolvió un error SOAP: {fault}"}

        except Exception as e:  # 🔹 Manejo de otros errores generales
            return {"control": "ERROR", "mensaje": f"Error en WSAA con Zeep: {str(e)}"}




        """try:
            # Enviar la solicitud SOAP al WSAA
            print("::: Enviando petición SOAP al WSAA... :::")
            response = requests.post(wsdl_url, data=soap_envelope, headers=headers, timeout=30)

            logging.info(response.text)
            response.raise_for_status()  # Lanza una excepción si el código HTTP no es 200
            print(f"Respuesta de AFIP:\n{response.text}")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error en la solicitud SOAP: {str(e)}")
        return {"cms_b64": cms_b64, "response": response}
        """
        # Retornar el resultado




    def procesar_respuesta_error_soap(response_text):
        try:
            root = etree.fromstring(response_text.encode('utf-8'))
            fault = root.find(".//soapenv:Fault", namespaces={"soapenv": "http://schemas.xmlsoap.org/soap/envelope/"})
            if fault is not None:
                fault_code = fault.find(".//faultcode").text
                fault_string = fault.find(".//faultstring").text
                return {"fault_code": fault_code, "fault_string": fault_string}
            return {"error": "No se encontró Fault en la respuesta."}
        except Exception as e:
            return {"error": f"Error procesando la respuesta SOAP: {e}"}






    @staticmethod
    def cargar_pkcs12(p12_path, password):
        """Cargar archivo PKCS#12 y obtener clave privada y certificado"""
        with open(p12_path, "rb") as p12_file:
            p12_data = p12_file.read()

        # Deserializar el archivo PKCS#12
        private_key, certificate, _ = pkcs12.load_key_and_certificates(p12_data, password.encode())
        return private_key, certificate


    @staticmethod
    def create_login_ticket_request(signer_dn, dst_dn, service, ticket_time_seconds):
        """Crea el XML necesario para el LoginTicketRequest"""
        # Crear el XML estructurado
        generation_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        expiration_time = (datetime.utcnow() + timedelta(seconds=ticket_time_seconds)).strftime('%Y-%m-%dT%H:%M:%S')

        login_ticket_request = ET.Element("loginTicketRequest")
        login_ticket_request.set("version", "1.0")

        header = ET.SubElement(login_ticket_request, "header")
        unique_id = ET.SubElement(header, "uniqueId")
        unique_id.text = str(int(datetime.timestamp(datetime.utcnow())))
        generation_time_tag = ET.SubElement(header, "generationTime")
        generation_time_tag.text = generation_time
        expiration_time_tag = ET.SubElement(header, "expirationTime")
        expiration_time_tag.text = expiration_time

        service_tag = ET.SubElement(login_ticket_request, "service")
        service_tag.text = service

        return ET.tostring(login_ticket_request).decode("utf-8")






    
