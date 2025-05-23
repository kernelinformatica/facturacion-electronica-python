# ejemplo con parametros externos 
#param (
#    [string]$serverHost,
#    [int]$serverPort,
#    [string]$username,
#    [string]$password
#)
# ejemplo como ejecutarlo
#.\script.ps1 -serverHost "192.168.210.100" -serverPort 2638 -username "DBA" -password "SQL"


# Parámetros de línea de comandos
[CmdletBinding()]
Param(
   [Parameter(Mandatory=$False)]
   [string]$Certificado="C:\kernel\wsaa-cliente\source\kernel.crt",
    
   [Parameter(Mandatory=$False)]
   [string]$ClavePrivada="C:\kernel\wsaa-cliente\source\pk-kernel.key",
   
   [Parameter(Mandatory=$False)]
   [string]$ServicioId="wsfe",
   
   [Parameter(Mandatory=$False)]
   [string]$OutXml="LoginTicketRequest.xml",   
   
   [Parameter(Mandatory=$False)]
   [string]$OutCms="LoginTicketRequest.xml.cms",   

   [Parameter(Mandatory=$False)]
   [string]$WsaaWsdl = "https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL"    
)

$ErrorActionPreference = "Stop"
##############################################
# PASO 1: CREAR EL XML DEL TICKET DE ACCESO
##############################################
$dtNow = Get-Date 
$xmlTA = New-Object System.XML.XMLDocument
$xmlTA.LoadXml('<loginTicketRequest><header><uniqueId></uniqueId><generationTime></generationTime><expirationTime></expirationTime></header><service></service></loginTicketRequest>')
$xmlUniqueId = $xmlTA.SelectSingleNode("//uniqueId")
$xmlGenTime = $xmlTA.SelectSingleNode("//generationTime")
$xmlExpTime = $xmlTA.SelectSingleNode("//expirationTime")
$xmlService = $xmlTA.SelectSingleNode("//service")

$xmlGenTime.InnerText = $dtNow.AddMinutes(-10).ToString("s")
$xmlExpTime.InnerText = $dtNow.AddMinutes(+10).ToString("s")
$xmlUniqueId.InnerText = $dtNow.ToString("yyMMddHHMM")
$xmlService.InnerText = $ServicioId

$seqNr = Get-Date -UFormat "%Y%m%d%H%S"
$xmlTA.InnerXml | Out-File "$seqNr-$OutXml" -Encoding ASCII
#############################################################
# PASO 2: FIRMAR CMS
#############################################################
# VALIDO QUE EL OPENSSL ESTE INSTALADO
if (Get-Command openssl -ErrorAction SilentlyContinue) {
    Write-Output "OpenSSL está instalado y disponible."
} else {
    Write-Output "Error: OpenSSL no está instalado o no está en la variable PATH."
    exit 1
}
openssl cms -sign -in "$seqNr-$OutXml" -signer $Certificado -inkey $ClavePrivada -nodetach -outform der -out "$seqNr-$OutCms-DER"
############################################################
# PASO 3: ENCODEAR EL CMS EN BASE 64
############################################################
openssl base64 -in "$seqNr-$OutCms-DER" -e -out "$seqNr-$OutCms-DER-b64"
###########################################################
# PASO 4: INVOCAR AL WSAA
###########################################################
try {
   $cms = Get-Content "$seqNr-$OutCms-DER-b64" -Raw
   $wsaa = New-WebServiceProxy -Uri $WsaaWsdl -ErrorAction Stop
   $wsaaResponse = $wsaa.loginCms($cms) 
   $wsaaResponse | Out-File "$seqNr-loginTicketResponse.xml"
   Write-Output $wsaaResponse
}
catch {
   $errMsg = $_.Exception.Message
   $errMsg | Out-File "$seqNr-loginTicketResponse-ERROR.xml"
   Write-Output $errMsg
}
###########################################################
# PASO 5: EXTRACCIÓN DE CREDENCIALES
###########################################################
$loginResponse = [xml](Get-Content "$seqNr-loginTicketResponse.xml")
$token = $loginResponse.loginTicketResponse.credentials.token
$sign = $loginResponse.loginTicketResponse.credentials.sign
$cuit = "30711536813"  # Reemplaza con tu CUIT correcto
###########################################################
# PASO 6: SOLICITUD A WSFE
###########################################################
$uri = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
#################################################################
# EJEMPLO DE CONEXION A BASE DE DATOS Y LECTURA DE TABLA EMPRESAS
# Definir la cadena de conexión ODBC
$conexion = New-Object System.Data.Odbc.OdbcConnection
$conexion.ConnectionString = "DSN=caja1;UID=dba;PWD=sql"

# Abrir la conexión
$conexion.Open()

# Definir la consulta SQL
$consulta = "SELECT emp_descri, emp_cuit FROM empresas"

# Crear y ejecutar el comando SQL
$comando = $conexion.CreateCommand()
$comando.CommandText = $consulta
$lector = $comando.ExecuteReader()

# Leer los resultados
while ($lector.Read()) {
    $emp_descri = $lector.GetString(0)  # Primera columna: emp_descri
    $emp_cuit = $lector.GetString(1)    # Segunda columna: emp_cuit

    Write-Output "Empresa: $emp_descri | CUIT: $emp_cuit"
}

# Cerrar la conexión
$lector.Close()
$conexion.Close()

##################################################################
$Url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
##################################################################
# CONSULTA ULTIMO COMPROBANTE TIPO 8
##################################################################
$xmlRequest = @"
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Header/>
    <soapenv:Body>
        <ar:FECompUltimoAutorizado>
            <ar:Auth>
                <ar:Token>$token</ar:Token>
                <ar:Sign>$sign</ar:Sign>
                <ar:Cuit>$cuit</ar:Cuit>
            </ar:Auth>
            <ar:PtoVta>2</ar:PtoVta>
            <ar:CbteTipo>8</ar:CbteTipo>
        </ar:FECompUltimoAutorizado>
    </soapenv:Body>
</soapenv:Envelope>
"@

# Guardar el XML para depuración
$xmlRequest | Out-File "soap_request.xml"

# Configuración de la solicitud HTTP
$headers = @{
    "Content-Type" = "text/xml;charset=UTF-8"
    "SOAPAction"   = "http://ar.gov.afip.dif.FEV1/FECompUltimoAutorizado"
}

try {
    $response = Invoke-WebRequest -Uri $Url -Method Post -Headers $headers -Body $xmlRequest -ContentType "text/xml"
    Write-Output "✅ Solicitud WSFE enviada con éxito."
    Write-Output $response.Content
    $response.Content | Out-File "respuesta.xml" -Encoding UTF8

}
catch {
    Write-Output "❌ Error al enviar la solicitud WSFE."
    Write-Output $_.Exception.Message
}

# Cargar el XML
[xml]$xmlDoc = Get-Content "respuesta.xml"

# Crear y agregar el manejador de espacios de nombres
$namespaceMgr = New-Object System.Xml.XmlNamespaceManager($xmlDoc.NameTable)
$namespaceMgr.AddNamespace("soap", "http://schemas.xmlsoap.org/soap/envelope/")

# Navegar por la estructura XML
$body = $xmlDoc.SelectSingleNode("//soap:Body", $namespaceMgr)

# Extraer valores específicos
$ptoVta = $body.FECompUltimoAutorizadoResponse.FECompUltimoAutorizadoResult.PtoVta
$cbteTipo = $body.FECompUltimoAutorizadoResponse.FECompUltimoAutorizadoResult.CbteTipo
$cbteNro = $body.FECompUltimoAutorizadoResponse.FECompUltimoAutorizadoResult.CbteNro

# Extraer errores
$errors = $body.FECompUltimoAutorizadoResponse.FECompUltimoAutorizadoResult.Errors.Err | ForEach-Object {
    [PSCustomObject]@{
        Code = $_.Code
        Msg  = $_.Msg
    }
}

# Extraer eventos
$events = $body.FECompUltimoAutorizadoResponse.FECompUltimoAutorizadoResult.Events.Evt | ForEach-Object {
    [PSCustomObject]@{
        Code = $_.Code
        Msg  = $_.Msg
    }
}

# Mostrar resultados
Write-Output "Punto de Venta: $ptoVta"
Write-Output "Tipo de Comprobante: $cbteTipo"
Write-Output "Número de Comprobante: $cbteNro"

Write-Output "Errores:"
$errors | Format-Table -AutoSize

Write-Output "Eventos:"
$events | Format-Table -AutoSize
################################################################
# LUEGO A LA VARIABLE DE ULTIMO CBTE LE SUMA 1
$cbteNro = [int]$cbteNro + 1  # Convertimos a número y sumamos 1
##########################################################################
# AUTORIZA EL COMPROBANTE DE NOTA DE CREDITO POR EJEMPLO
#############################################################################
$xmlBody = @"
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Header/>
    <soapenv:Body>
       <ar:FECAESolicitar>
            <ar:Auth>
                <ar:Token>$token</ar:Token>
                <ar:Sign>$sign</ar:Sign>
                <ar:Cuit>$cuit</ar:Cuit>
            </ar:Auth>
            <ar:FeCAEReq>
                <ar:FeCabReq>
                    <ar:CantReg>1</ar:CantReg>
                    <ar:PtoVta>2</ar:PtoVta>
                    <ar:CbteTipo>8</ar:CbteTipo>
                </ar:FeCabReq>
                 <ar:FeDetReq>
                    <ar:FECAEDetRequest>
                        <ar:Concepto>2</ar:Concepto>
                        <ar:DocTipo>96</ar:DocTipo>
                        <ar:DocNro>17280761</ar:DocNro>
                        <ar:CbteDesde>$cbteNro</ar:CbteDesde>
                        <ar:CbteHasta>$cbteNro</ar:CbteHasta>
                        <ar:CbteFch>20250503</ar:CbteFch>
                        <ar:ImpTotal>184.05</ar:ImpTotal>
                        <ar:ImpTotConc>0</ar:ImpTotConc>
                        <ar:ImpNeto>150</ar:ImpNeto>
                        <ar:ImpOpEx>0</ar:ImpOpEx>
                        <ar:ImpTrib>7.8</ar:ImpTrib>
                        <ar:ImpIVA>26.25</ar:ImpIVA>
                        <ar:FchServDesde>20250503</ar:FchServDesde>
                        <ar:FchServHasta>20250503</ar:FchServHasta>
                        <ar:FchVtoPago>20250503</ar:FchVtoPago>
                        <ar:MonId>PES</ar:MonId>
                        <ar:MonCotiz>1</ar:MonCotiz>
                        <ar:CondicionIVAReceptorId>4</ar:CondicionIVAReceptorId>
                        <ar:CbtesAsoc>
                           <ar:CbteAsoc>
                              <ar:Tipo>6</ar:Tipo>
                              <ar:PtoVta>2</ar:PtoVta>
                              <ar:Nro>109</ar:Nro>
                              <ar:Cuit>30711536813</ar:Cuit>
                              <ar:CbteFch>20250503</ar:CbteFch>
                           </ar:CbteAsoc>
                        </ar:CbtesAsoc>
                        <ar:Tributos>
                            <ar:Tributo>
                                <ar:Id>99</ar:Id>
                                <ar:Desc>Impuesto Municipal Matanza</ar:Desc>
                                <ar:BaseImp>150</ar:BaseImp>
                                <ar:Alic>5.2</ar:Alic>
                                <ar:Importe>7.8</ar:Importe>
                            </ar:Tributo>
                        </ar:Tributos>
                        <ar:Iva>
                            <ar:AlicIva>
                                <ar:Id>5</ar:Id>
                                <ar:BaseImp>100</ar:BaseImp>
                                <ar:Importe>21</ar:Importe>
                            </ar:AlicIva>
                            <ar:AlicIva>
                                <ar:Id>4</ar:Id>
                                <ar:BaseImp>50</ar:BaseImp>
                                <ar:Importe>5.25</ar:Importe>
                            </ar:AlicIva>
                        </ar:Iva>
         </ar:FECAEDetRequest>
       </ar:FeDetReq>
     </ar:FeCAEReq>
   </ar:FECAESolicitar>
 </soapenv:Body>
</soapenv:Envelope>
"@

try {
    $response = Invoke-WebRequest -Uri $uri -Method Post -Body $xmlBody -ContentType "text/xml" -Headers @{"SOAPAction"="http://ar.gov.afip.dif.FEV1/FECAESolicitar"}
    Write-Output "✅ Solicitud WSFE enviada con éxito."
    Write-Output $response.Content
    $response.Content | Out-File "respuesta.xml" -Encoding UTF8

}
catch {
    Write-Output "❌ Error al enviar la solicitud WSFE."
    Write-Output $_.Exception.Message
}

