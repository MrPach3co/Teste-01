from slowapi import Limiter
from slowapi.util import get_remote_address

# Instância única compartilhada pelo app e por todos os routers.
limiter = Limiter(key_func=get_remote_address)
