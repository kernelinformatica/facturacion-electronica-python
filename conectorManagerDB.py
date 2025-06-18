class ConectorManagerDB:
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


"""
 conn = ConectorManagerDB(1)
cursor = conn.get_connection().conn.cursor()
sql_libro =  SELECT valor from Parametros where  Parametros.grupo = 'contable' and Parametros.nombreParametro = 'codigo_libro_sybase';  
print(sql_libro)
cursor.execute(sql_libro,)
lib = cursor.fetchone()
if lib:
    print(f"Valor del libro: {lib[0]}")
 """




