import time

from fastapi import FastAPI
from sqlalchemy import text

from app.core.db import Base, engine

app = FastAPI(title="RutaSegura")


@app.get("/health")
def health():
    return {"status": "ok"}


def _wait_for_db(retries: int = 10, delay: float = 1.5) -> None:
    last_error = None
    for _ in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - queremos reintentar ante cualquier fallo de conexión
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"No se pudo conectar a la base de datos tras {retries} intentos") from last_error


@app.on_event("startup")
def on_startup():
    _wait_for_db()
    Base.metadata.create_all(bind=engine)
