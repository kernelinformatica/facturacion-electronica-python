from decimal import Decimal
class Utilidades:
    def __init__(self):
        super().__init__()

        # Cargar configuración desde el archivo .env




    def convertirImportes(self, enteros, decimales, importe):
        # Construir el formato dinámicamente
        formato = f"{'9' * enteros}.{'9' * decimales}"
        return Decimal(importe).quantize(Decimal(formato))











