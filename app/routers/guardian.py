from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.models import GuardianSession, TrustedContact, User
from app.schemas import (
    MAX_CONTACTOS,
    ContactCreate,
    ContactOut,
    GuardianCheckin,
    GuardianOut,
    GuardianStart,
    SOSContacto,
    SOSOut,
    SOSRequest,
    normalizar_celular,
)
from app.services import whatsapp

router = APIRouter(prefix="/api", tags=["guardian"])


def _get_session_or_404(session_id: int, user: User, db: Session) -> GuardianSession:
    session = db.get(GuardianSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
    return session


def _maybe_mark_alert(session: GuardianSession) -> GuardianSession:
    # Evaluación perezosa del vencimiento del ETA, sin workers en segundo plano
    if session.status == "active" and datetime.now(timezone.utc) > session.eta_at:
        session.status = "alert"
    return session


@router.post("/guardian/start", response_model=GuardianOut, status_code=status.HTTP_201_CREATED)
def start_guardian(
    data: GuardianStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    session = GuardianSession(
        user_id=current_user.id,
        started_at=now,
        eta_at=now + timedelta(minutes=data.minutes),
        status="active",
        last_lat=data.lat,
        last_lng=data.lng,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/guardian/{session_id}/checkin", response_model=GuardianOut)
def checkin_guardian(
    session_id: int,
    data: GuardianCheckin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user, db)
    if session.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La sesión ya finalizó")
    session.last_lat = data.lat
    session.last_lng = data.lng
    if data.extend_minutes:
        session.eta_at = datetime.now(timezone.utc) + timedelta(minutes=data.extend_minutes)
    db.commit()
    db.refresh(session)
    return _maybe_mark_alert(session)


@router.post("/guardian/{session_id}/arrived", response_model=GuardianOut)
def arrived_guardian(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user, db)
    session.status = "arrived"
    db.commit()
    db.refresh(session)
    return session


@router.get("/guardian/{session_id}", response_model=GuardianOut)
def get_guardian(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user, db)
    _maybe_mark_alert(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/sos", response_model=SOSOut)
@limiter.limit("6/minute")
async def sos(
    request: Request,
    data: SOSRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # La ubicación solo viaja en el mensaje; no se guarda ni se registra en logs (Ley 1581)
    data = data or SOSRequest()
    contactos = (
        db.query(TrustedContact).filter(TrustedContact.user_id == current_user.id).order_by(TrustedContact.id).all()
    )
    ubicacion_url = None
    if data.lat is not None and data.lng is not None:
        ubicacion_url = f"https://maps.google.com/?q={data.lat:.5f},{data.lng:.5f}"
    mensaje = f"EMERGENCIA: {current_user.name} necesita ayuda."
    if ubicacion_url:
        mensaje += f" Mi ubicación: {ubicacion_url}"
    mensaje += " Si no respondo, llama al 123. (Enviado desde RutaSegura)"
    texto = quote(mensaje)

    automatico = whatsapp.configurado() and bool(contactos)
    if automatico:
        resultados = await whatsapp.enviar_a_todos([c.phone for c in contactos], current_user.name, ubicacion_url, mensaje)
    else:
        resultados = [(False, None)] * len(contactos)

    salida = []
    for c, (ok, detalle) in zip(contactos, resultados):
        estado = "enviado" if ok else ("fallido" if automatico else "manual")
        salida.append(
            SOSContacto(
                name=c.name,
                phone=c.phone,
                estado=estado,
                detalle=detalle,
                whatsapp_url=f"https://wa.me/{normalizar_celular(c.phone)}?text={texto}",
            )
        )
    return SOSOut(
        mensaje=mensaje,
        automatico=automatico,
        contactos=salida,
        whatsapp_compartir=f"https://wa.me/?text={texto}",
    )


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(TrustedContact).filter(TrustedContact.user_id == current_user.id).all()


@router.post("/contacts", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existentes = db.query(TrustedContact).filter(TrustedContact.user_id == current_user.id).all()
    if len(existentes) >= MAX_CONTACTOS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Puedes tener hasta {MAX_CONTACTOS} contactos de emergencia",
        )
    if any(c.phone == data.phone for c in existentes):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese número ya está en tus contactos")
    contact = TrustedContact(user_id=current_user.id, name=data.name, phone=data.phone)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.get(TrustedContact, contact_id)
    if contact is None or contact.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")
    db.delete(contact)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
