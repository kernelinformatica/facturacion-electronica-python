import ssl

from requests_toolbelt import SSLAdapter
# Crear un ejemplo de datos



from zeep import Client, Transport
from requests import Session
import logging

# Configuración del cliente SOAP
wsdl = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
session = Session()
transport = Transport(session=session)
client = Client(wsdl=wsdl, transport=transport)
# Crear un contexto SSL personalizado
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False  # Deshabilitar la verificación del nombre del host
ssl_context.verify_mode = ssl.CERT_NONE  # No verificar certificados
ssl_context.set_ciphers( "DEFAULT:@SECLEVEL=1")  # Reducir el nivel de seguridad para aceptar claves DH pequeñas
# Configurar la sesión de requests
session = Session()
session.verify = False  # Evita errores de certificado en entorno de prueba
session.mount("https://", SSLAdapter(ssl_context=ssl_context))
# Configurar la sesión de requests
session.headers.update({
                    "Content-Type": "application/xml; charset=utf-8",
                    "SOAPAction": '"FECAESolicitar"'
})
# Datos de autenticación
auth = {
     "Token": 'PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9InllcyI/Pgo8c3NvIHZlcnNpb249IjIuMCI+CiAgICA8aWQgc3JjPSJDTj13c2FhaG9tbywgTz1BRklQLCBDPUFSLCBTRVJJQUxOVU1CRVI9Q1VJVCAzMzY5MzQ1MDIzOSIgZHN0PSJDTj13c2ZlLCBPPUFGSVAsIEM9QVIiIHVuaXF1ZV9pZD0iMzQ3NTY1NDYzNyIgZ2VuX3RpbWU9IjE3NDcyMjY4ODciIGV4cF90aW1lPSIxNzQ3MjcwMTQ3Ii8+CiAgICA8b3BlcmF0aW9uIHR5cGU9ImxvZ2luIiB2YWx1ZT0iZ3JhbnRlZCI+CiAgICAgICAgPGxvZ2luIGVudGl0eT0iMzM2OTM0NTAyMzkiIHNlcnZpY2U9IndzZmUiIHVpZD0iU0VSSUFMTlVNQkVSPUNVSVQgMjAyMzQ3NjIyNjYsIENOPWRhcmlvZmV0ZXN0IiBhdXRobWV0aG9kPSJjbXMiIHJlZ21ldGhvZD0iMjIiPgogICAgICAgICAgICA8cmVsYXRpb25zPgogICAgICAgICAgICAgICAgPHJlbGF0aW9uIGtleT0iMjAyMzQ3NjIyNjYiIHJlbHR5cGU9IjQiLz4KICAgICAgICAgICAgPC9yZWxhdGlvbnM+CiAgICAgICAgPC9sb2dpbj4KICAgIDwvb3BlcmF0aW9uPgo8L3Nzbz4K',
     "Sign": 'DnSDxou9QN9/GoUPUto9GxHw/yfD8OsnAgiDCyNq7YcyAA+knuuYeIBTerBkIatCuOOg8JXPLZOOvwaIpFJ00WvFaeyPiwcQew1quyKvrhpMfWgqaE6Sdk8Ry8HPyW8H7uaX2T9BaMN1bQaSCqufaL9dbYCn0TxJJAQLT+O6Bcw=',
      "Cuit": 20234762266
}


# Estructura de la solicitud
fe_cab_req = {
    "CantReg": 1,
    "PtoVta": 2,
    "CbteTipo": 8
}

fe_det_req = [
    {
        "Concepto": 2,
        "DocTipo": 96,
        "DocNro": 17280761,
        "CbteDesde": 1,
        "CbteHasta": 1,
        "CbteFch": "20250503",
        "ImpTotal": 184.05,
        "ImpTotConc": 0,
        "ImpNeto": 150,
        "ImpOpEx": 0,
        "ImpTrib": 7.8,
        "ImpIVA": 26.25,
        "FchServDesde": "20250503",
        "FchServHasta": "20250503",
        "FchVtoPago": "20250503",
        "MonId": "PES",
        "MonCotiz": 1,
        "CondicionIVAReceptorId": 4,
        "CbtesAsoc": [],
        "Tributos": {
            "Tributo": [
                {
                    "Id": 99,
                    "Desc": "Impuesto Municipal Matanza",
                    "BaseImp": 150,
                    "Alic": 5.2,
                    "Importe": 7.8
                }
            ]
        },
        "Iva": {
            "AlicIva": [
                {
                    "Id": 5,
                    "BaseImp": 100,
                    "Importe": 21
                },
                {
                    "Id": 4,
                    "BaseImp": 50,
                    "Importe": 5.25
                }
            ]
        }
    }
]

# Llamada al servicio SOAP
try:
    response = client.service.FECAESolicitar(
        Auth=auth,
        FeCAEReq={
            "FeCabReq": fe_cab_req,
            "FeDetReq": fe_det_req
        }
    )
    print("✅ Solicitud WSFE enviada con éxito.")
    print(response)
    with open("respuesta.xml", "w", encoding="utf-8") as file:
        file.write(str(response))
except Exception as e:
    print("❌ Error al enviar la solicitud WSFE.")
    print(str(e))