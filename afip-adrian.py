import requests
import datetime
import base64
import subprocess
from lxml import etree

# Parámetros de configuración

certificado = r"C:\odoo16\server\addons_ext\kernel\ws-rest\facturacion-electronica\afip\certificado\homo\dQuiroga25.crt"
clave_privada = r"C:\odoo16\server\addons_ext\kernel\ws-rest\facturacion-electronica\afip\certificado\homo\dQuiroga25.key"
#certificado = r"C:\odoo16\server\addons_ext\kernel\ws-rest\facturacion-electronica\afip\certificado\homo\coopaz\coopaz.crt"
#clave_privada = r"C:\odoo16\server\addons_ext\kernel\ws-rest\facturacion-electronica\afip\certificado\homo\coopaz\pk-mp.key"
servicio_id = "wsfe"
out_xml = "LoginTicketRequest.xml"
out_cms = "LoginTicketRequest.xml.cms"
# Usaremos el endpoint real, sin el parámetro ?WSDL, para la llamada SOAP.
wsaa_endpoint = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"

# PASO 1: ARMAR EL XML DEL TICKET DE ACCESO
dt_now = datetime.datetime.now()
# Creamos el documento XML
login_ticket = etree.Element("loginTicketRequest")
header = etree.SubElement(login_ticket, "header")
unique_id = etree.SubElement(header, "uniqueId")
generation_time = etree.SubElement(header, "generationTime")
expiration_time = etree.SubElement(header, "expirationTime")
service = etree.SubElement(login_ticket, "service")

# Configuramos los valores:
generation_time.text = (dt_now - datetime.timedelta(minutes=10)).isoformat()
expiration_time.text = (dt_now + datetime.timedelta(minutes=10)).isoformat()
unique_id.text = dt_now.strftime("%y%m%d%H%M")
service.text = servicio_id

# Utilizamos un identificador de secuencia basado en la fecha y hora
seq_nr = dt_now.strftime("%Y%m%d%H%S")
xml_filename = f"{seq_nr}-{out_xml}"

# Guardamos el XML; se guarda con declaración y en UTF-8
tree = etree.ElementTree(login_ticket)
tree.write(xml_filename, encoding="utf-8", xml_declaration=True)
print(f"XML generado y guardado en: {xml_filename}")

# PASO 2: FIRMAR CMS con OpenSSL
# Se firma el XML usando el certificado y clave privada, se usa el formato DER sin detach.
cms_der_filename = f"{seq_nr}-{out_cms}-DER"
try:
    subprocess.run([
        "openssl", "cms", "-sign",
        "-in", xml_filename,
        "-signer", certificado,
        "-inkey", clave_privada,
        "-nodetach",
        "-outform", "der",
        "-out", cms_der_filename
    ], check=True)
    print(f"Archivo firmado (DER) guardado en: {cms_der_filename}")
except subprocess.CalledProcessError as cpe:
    print("Error al firmar el XML con OpenSSL:", cpe)
    exit(1)

# PASO 3: ENCODEAR EL CMS EN BASE 64
cms_b64_filename = f"{seq_nr}-{out_cms}-DER-b64"
try:
    with open(cms_der_filename, "rb") as file_in:
        cms_der = file_in.read()
    cms_b64 = base64.b64encode(cms_der).decode("utf-8")
    with open(cms_b64_filename, "w") as file_out:
        file_out.write(cms_b64)
    print(f"Archivo CMS codificado en Base64 guardado en: {cms_b64_filename}")
except Exception as e:
    print("Error al codificar en Base64:", e)
    exit(1)

# PASO 4: INVOCAR AL WSAA CON PETICION SOAP
try:
    # Leemos el CMS (ya codificado en Base64)
    with open(cms_b64_filename, "r") as file:
        cms = file.read()

    # Armar la petición SOAP en XML, incluyendo la llamada a loginCms.
    # Se incluye el parámetro "in0" que contiene el CMS.
    soap_envelope = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://wsaa.view.service/">
  <soapenv:Header/>
  <soapenv:Body>
    <ws:loginCms>
      <in0>{cms}</in0>
    </ws:loginCms>
  </soapenv:Body>
</soapenv:Envelope>'''

    # Importante: se incluye la cabecera SOAPAction ya que el servidor lo requiere.
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": '"loginCms"'
    }

    print("Enviando petición SOAP al WSAA...")
    response = requests.post(wsaa_endpoint, data=soap_envelope, headers=headers, timeout=30)

    # Guardamos la respuesta en un archivo
    response_filename = f"{seq_nr}-loginTicketResponse.xml"
    with open(response_filename, "w", encoding="utf-8") as file_out:
        file_out.write(response.text)

    print(f"Respuesta recibida. Guardada en: {response_filename}")
    print("Respuesta del WSAA:")
    print(response.text)

except Exception as e:
    error_filename = f"{seq_nr}-loginTicketResponse-ERROR.xml"
    with open(error_filename, "w", encoding="utf-8") as file_out:
        file_out.write(str(e))
    print("Se ha producido un error al invocar el WSAA. Detalle:")
    print(e)