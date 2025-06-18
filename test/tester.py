import json


class Tester:
    def __init__(self, plataforma):
        self.plataforma = plataforma
        self.connection = None

    def get_connection(self):
        """🔹 Devuelve la conexión adecuada según el valor de plataforma."""
        if self.plataforma == 1:
            from conn.FacturacionConnection import DBConnection
            self.connection = DBConnection()  # Conexión a MySQL
        elif self.plataforma == 2:
            from conn.FacturacionConnectionSybase import DBConnectionSybase
            self.connection = DBConnectionSybase()
        else:
            raise ValueError("Plataforma no soportada")
        return self.connection



conn = Tester(1)
cursor = conn.get_connection().conn.cursor()
cbtes_asoc = []
idFactCabAsoc = 59
sql_cab = """SELECT ABS(RIGHT(numeroAfip, 8)) AS  CNroAsoc, CAST(LEFT(numeroAfip, 4) AS UNSIGNED) AS PVtaAsoc, codigoAfip AS CbteTipoAsoc, cuit AS CuitAsoc FROM FactCab WHERE idFactCab = %s"""
cursor.execute(sql_cab, (idFactCabAsoc,))
resuCab = cursor.fetchall()

for item in resuCab:
    cbte_item = {
        "CNroAsoc": int(item[0]),  # Número comprobante asociado
        "PVtaAsoc": int(item[1] // 1000),  # Punto de venta asociado
        "CTipoAsoc": int(item[2]),  # Tipo de comprobante asociado
        "CuitAsoc": int(item[3])  # Número de comprobante
    }
    cbtes_asoc.append(cbte_item)
    json_formateado = json.dumps(cbtes_asoc, indent=4, ensure_ascii=False)

    print(json_formateado)





