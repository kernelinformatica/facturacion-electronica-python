class ConnectionManager:
    def __init__(self, plataforma):
        self.plataforma = plataforma
        self.connection = None

    def get_connection(self):
        """🔹 Devuelve la conexión adecuada según el valor de plataforma."""
        if self.plataforma == 1:
            from conn.FacturacionConnection import DBConnection
            self.connection = DBConnection()  # Conexión a MySQL
        elif self.plataforma == 2:
            from conn.OtherDBConnection import OtherDBConnection
            self.connection = OtherDBConnection()  # Conexión a la otra base de datos
        else:
            raise ValueError("Plataforma no soportada")
        return self.connection