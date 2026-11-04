"""Envío automático de la alerta SOS por la API oficial de WhatsApp (Meta Cloud API).

Es opcional: solo se usa si hay credenciales en el entorno. Fuera de la ventana de 24 h
de atención, WhatsApp solo permite plantillas aprobadas, por eso se admite
WHATSAPP_TEMPLATE_NAME (con dos variables: nombre de la usuaria y enlace de ubicación).
"""
import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("rutasegura.sos")

GRAPH_URL = "https://graph.facebook.com/{version}/{phone_id}/messages"


def configurado() -> bool:
    return bool(settings.WHATSAPP_TOKEN.get_secret_value() and settings.WHATSAPP_PHONE_NUMBER_ID)


def _una_linea(texto: str) -> str:
    # Los parámetros de plantilla no admiten saltos de línea ni tabulaciones
    return " ".join(texto.split())


def construir_payload(telefono: str, nombre: str, ubicacion_url: str | None, mensaje: str) -> dict:
    if settings.WHATSAPP_TEMPLATE_NAME:
        return {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "template",
            "template": {
                "name": settings.WHATSAPP_TEMPLATE_NAME,
                "language": {"code": settings.WHATSAPP_TEMPLATE_LANG},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": _una_linea(nombre) or "Una persona"},
                            {"type": "text", "text": ubicacion_url or "ubicación no disponible"},
                        ],
                    }
                ],
            },
        }
    return {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"preview_url": True, "body": mensaje},
    }


async def enviar_uno(client: httpx.AsyncClient, payload: dict) -> tuple[bool, str | None]:
    url = GRAPH_URL.format(version=settings.WHATSAPP_API_VERSION, phone_id=settings.WHATSAPP_PHONE_NUMBER_ID)
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN.get_secret_value()}"}
    try:
        resp = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError:
        logger.warning("WhatsApp: sin conexión con la API")
        return False, "No se pudo conectar con WhatsApp"
    if resp.is_success:
        return True, None
    codigo = None
    try:
        codigo = resp.json().get("error", {}).get("code")
    except ValueError:
        pass
    # No se registran teléfonos, mensajes ni coordenadas (Ley 1581)
    logger.warning("WhatsApp rechazó un mensaje: http=%s codigo=%s", resp.status_code, codigo)
    return False, f"WhatsApp rechazó el mensaje (código {codigo or resp.status_code})"


async def enviar_a_todos(
    telefonos: list[str],
    nombre: str,
    ubicacion_url: str | None,
    mensaje: str,
    client: httpx.AsyncClient | None = None,
) -> list[tuple[bool, str | None]]:
    """Envía en paralelo y devuelve (ok, detalle_del_error) por teléfono, en el mismo orden."""

    async def _enviar(c: httpx.AsyncClient):
        tareas = [enviar_uno(c, construir_payload(t, nombre, ubicacion_url, mensaje)) for t in telefonos]
        return list(await asyncio.gather(*tareas))

    if client is not None:
        return await _enviar(client)
    async with httpx.AsyncClient(timeout=6) as c:
        return await _enviar(c)
