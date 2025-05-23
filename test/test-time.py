import datetime
import pytz

# Obtener hora del servidor en UTC
hora_servidor = datetime.datetime.now(pytz.utc)
print("⏳ Hora del servidor UTC:", hora_servidor)

# Opcional: compara con la hora oficial de Argentina
tz_ar = pytz.timezone("America/Argentina/Buenos_Aires")
hora_local = datetime.datetime.now(tz_ar)
print("🇦🇷 Hora en Argentina:", hora_local)
