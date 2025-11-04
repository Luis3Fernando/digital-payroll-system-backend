import time
from datetime import datetime

class APIResponse:
    """
    Crea respuestas uniformes para toda la API.
    """
    @staticmethod
    def success(data=None, message="Operación exitosa", code=200, meta=None):
        start = time.time()
        return {
            "code": code,
            "status": "success",
            "messages": [message],
            "data": data,
            "meta": {
                "durationMs": int((time.time() - start) * 1000),
                "version": "v1.0.0",
                "cacheHit": False,
                "pagination": meta.get("pagination") if meta else None,
                "warnings": meta.get("warnings") if meta else [],
            }
        }

    @staticmethod
    def error(message="Ocurrió un error", code=400, errors=None):
        return {
            "code": code,
            "status": "error",
            "messages": [message],
            "data": None,
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "version": "v1.0.0",
                "errors": errors or [],
            }
        }
