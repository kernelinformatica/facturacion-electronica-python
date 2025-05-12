import datetime
from decimal import Decimal


class RequerimientoCAE:
    def __init__(self, producto_facade, fact_cab_facade, fact_cab_relacionados_facade):
        self.producto_facade = producto_facade
        self.fact_cab_facade = fact_cab_facade
        self.fact_cab_relacionados_facade = fact_cab_relacionados_facade
        # Variables usadas en la clase
        self.nro_punto_venta = 0
        self.concepto = 0
        self.imp_total = Decimal(0)
        self.imp_tot_conc = Decimal(0)
        self.imp_neto = Decimal(0)
        self.imp_op_ex = Decimal(0)
        self.imp_iva = Decimal(0)
        self.imp_trib = Decimal(0)

    def get_fecae_req(self, fact_cab):
        try:
            # Crear las estructuras de datos necesarias
            requerimiento_facturacion = {
                "FeCabReq": {},
                "FeDetReq": []
            }

            # Seteo de valores en la cabecera
            item_cab_actual = {
                "CantReg": 1,
                "CbteTipo": fact_cab["codigo_afip"]
            }
            # Parseo del número de punto de venta
            numero = str(fact_cab["numero_afip"]).zfill(12)
            pto_venta = numero[:-8]
            self.nro_punto_venta = int(pto_venta)
            item_cab_actual["PtoVta"] = self.nro_punto_venta

            # Preparación del detalle
            item_det_actual = {}
            contador_prod = 0
            contador_serv = 0
            for detalle in fact_cab["fact_detalle_collection"]:
                if detalle["id_producto"] != 0:
                    producto = self.producto_facade.find(detalle["id_producto"])
                    if producto:
                        if producto.get("stock"):
                            contador_prod += 1
                        else:
                            contador_serv += 1
                else:
                    self.concepto = 2

            # Determinación de concepto
            if contador_prod > 0 and contador_serv == 0:
                self.concepto = 1
            elif contador_prod == 0 and contador_serv > 0:
                self.concepto = 2
            elif contador_prod > 0 and contador_serv > 0:
                self.concepto = 3
            else:
                self.concepto = 2

            item_det_actual["Concepto"] = self.concepto
            item_det_actual["DocTipo"] = 80
            item_det_actual["DocNro"] = int(fact_cab["cuit"])

            # Formateo de comprobante
            numero_venta_format = str(fact_cab["numero_afip"]).zfill(8)
            item_det_actual["CbteDesde"] = int(numero_venta_format)
            item_det_actual["CbteHasta"] = int(numero_venta_format)
            item_det_actual["CbteFch"] = fact_cab["fecha_emision"].strftime("%Y%m%d")

            # Cálculo de importes
            if fact_cab["letra"] == "C":
                self.imp_neto = sum([
                    d["importe"] for d in fact_cab["fact_detalle_collection"]
                    if d["iva_porc"] != Decimal(0)
                ])
            else:
                self.imp_neto = Decimal(0)

            for pie in fact_cab["fact_pie_collection"]:
                self.imp_total += pie["importe"]
                if fact_cab["letra"] != "C":
                    if pie["id_sis_tipo_modelo"] == 2:
                        self.imp_iva += pie["importe"]
                    else:
                        self.imp_trib += pie["importe"]
                else:
                    self.imp_iva = Decimal(0)

            if fact_cab["letra"] == "C":
                self.imp_tot_conc = Decimal(0)
            else:
                self.imp_tot_conc = sum([
                    d["importe"] for d in fact_cab["fact_detalle_collection"]
                    if d["iva_porc"] == Decimal(0)
                ])

            item_det_actual["ImpTotal"] = float(self.imp_total)
            item_det_actual["ImpTotConc"] = float(self.imp_tot_conc)
            item_det_actual["ImpNeto"] = float(self.imp_neto)
            item_det_actual["ImpOpEx"] = float(self.imp_op_ex)
            item_det_actual["ImpIVA"] = float(self.imp_iva)
            item_det_actual["ImpTrib"] = float(self.imp_trib)

            # Validación de servicios
            if item_det_actual["Concepto"] in [2, 3]:
                fecha_emision = fact_cab["fecha_emision"].strftime("%Y%m%d")
                item_det_actual["FchServDesde"] = fecha_emision
                item_det_actual["FchServHasta"] = fecha_emision
                item_det_actual["FchVtoPago"] = fecha_emision

            # Asociar comprobantes si aplica
            if fact_cab["id_cte_tipo"]["c_tipo_operacion"] in [3, 8, 6, 2]:
                if fact_cab["id_cte_tipo"]["curso_legal"]:
                    relacionado = self.fact_cab_relacionados_facade.get_by_id_fact_cab(fact_cab)
                    if relacionado:
                        cte_asoc = {
                            "Nro": relacionado["c_nro_asoc"],
                            "PtoVta": relacionado["p_vta_asoc"],
                            "Tipo": relacionado["c_tipo_asoc"]
                        }
                        item_det_actual["CbtesAsoc"] = [cte_asoc]

            item_det_actual["MonId"] = fact_cab["idmoneda"]["id_moneda_afip"]
            item_det_actual["MonCotiz"] = float(fact_cab["idmoneda"]["cotizacion_afip"])
            requerimiento_facturacion["FeCabReq"] = item_cab_actual
            requerimiento_facturacion["FeDetReq"].append(item_det_actual)

            return requerimiento_facturacion

        except Exception as e:
            raise Exception(f"Error generando el requerimiento de CAE: {e}")
