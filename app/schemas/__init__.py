import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

ReportType = Literal["poca_luz", "acoso", "calle_sola", "zona_segura"]
SafePointKind = Literal["cai", "farmacia", "tienda", "gasolinera"]
GuardianStatus = Literal["active", "arrived", "alert"]


MAX_CONTACTOS = 5


def normalizar_celular(phone: str) -> str:
    """WhatsApp (wa.me) exige el número internacional solo con dígitos; 57 = Colombia."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10 and digits.startswith("3"):
        digits = "57" + digits
    return digits


# ---------- Contacts ----------
class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=30)

    @field_validator("phone")
    @classmethod
    def validar_celular(cls, v: str) -> str:
        digits = normalizar_celular(v)
        if not 11 <= len(digits) <= 15:
            raise ValueError("Escribe un celular de 10 dígitos, por ejemplo 300 123 4567")
        return digits


class ContactOut(BaseModel):
    id: int
    name: str
    phone: str

    model_config = {"from_attributes": True}


# ---------- Auth ----------
class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    contacts: list[ContactCreate] = Field(default_factory=list, max_length=MAX_CONTACTOS)

    @field_validator("contacts")
    @classmethod
    def sin_repetidos(cls, v: list[ContactCreate]) -> list[ContactCreate]:
        if len({c.phone for c in v}) != len(v):
            raise ValueError("No repitas el mismo número de celular")
        return v


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Reports ----------
class ReportCreate(BaseModel):
    type: ReportType
    severity: int = Field(ge=1, le=5)
    description: str | None = Field(default=None, max_length=280)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ReportOut(BaseModel):
    id: int
    type: ReportType
    severity: int
    description: str | None
    lat: float
    lng: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Safe points ----------
class SafePointOut(BaseModel):
    id: int
    name: str
    kind: SafePointKind
    lat: float
    lng: float
    open_24h: bool

    model_config = {"from_attributes": True}


# ---------- Routes / ISN ----------
class ISNBreakdown(BaseModel):
    riesgo_reportes: float
    penal_luz: float
    refugio_m: float
    zona_segura: int
    isn: float
    explicacion: str


class RouteOut(BaseModel):
    geometry: list[list[float]]  # [[lat, lng], ...]
    distance_m: float
    duration_s: float
    isn: float
    breakdown: ISNBreakdown
    es_mas_segura: bool


class RoutesResponse(BaseModel):
    origin: list[float]
    destination: list[float]
    rutas: list[RouteOut]


# ---------- Guardian ----------
class GuardianStart(BaseModel):
    minutes: int = Field(ge=1, le=240)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class GuardianCheckin(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    extend_minutes: int | None = Field(default=None, ge=1, le=240)


class GuardianOut(BaseModel):
    id: int
    started_at: datetime
    eta_at: datetime
    status: GuardianStatus
    last_lat: float
    last_lng: float

    model_config = {"from_attributes": True}


# ---------- SOS ----------
class SOSRequest(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class SOSContacto(BaseModel):
    name: str
    phone: str
    # enviado: salió automáticamente · fallido: el envío automático falló · manual: requiere un toque de la usuaria
    estado: Literal["enviado", "fallido", "manual"]
    detalle: str | None = None
    whatsapp_url: str


class SOSOut(BaseModel):
    mensaje: str
    automatico: bool
    contactos: list[SOSContacto]
    whatsapp_compartir: str
