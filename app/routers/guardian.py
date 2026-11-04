from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import GuardianSession, TrustedContact, User
from app.schemas import (
    ContactCreate,
    ContactOut,
    GuardianCheckin,
    GuardianOut,
    GuardianStart,
    SOSOut,
)

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
def sos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    contactos = db.query(TrustedContact).filter(TrustedContact.user_id == current_user.id).all()
    mensaje = (
        f"Alerta SOS de {current_user.name}: necesito ayuda, por favor contáctame o llama a la línea de emergencia (123)."
    )
    return SOSOut(mensaje=mensaje, contactos_notificados=[c.phone for c in contactos])


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(TrustedContact).filter(TrustedContact.user_id == current_user.id).all()


@router.post("/contacts", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = TrustedContact(user_id=current_user.id, name=data.name, phone=data.phone)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
