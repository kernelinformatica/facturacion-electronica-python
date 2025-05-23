import ssl
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
class SSLAdapter(HTTPAdapter):
    """Adaptador personalizado para configurar un contexto SSL."""

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)
