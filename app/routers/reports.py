from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user_optional
from app.core.limiter import limiter
from app.models import Report, User
from app.schemas import ReportCreate, ReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(
    min_lat: float = Query(..., ge=-90, le=90),
    max_lat: float = Query(..., ge=-90, le=90),
    min_lng: float = Query(..., ge=-180, le=180),
    max_lng: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    return (
        db.query(Report)
        .filter(Report.lat.between(min_lat, max_lat))
        .filter(Report.lng.between(min_lng, max_lng))
        .filter(Report.created_at >= since)
        .order_by(Report.created_at.desc())
        .limit(500)
        .all()
    )


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_report(
    request: Request,
    data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # Ubicación redondeada a 4 decimales (~11 m) por privacidad (Ley 1581)
    report = Report(
        user_id=current_user.id if current_user else None,
        type=data.type,
        severity=data.severity,
        description=data.description,
        lat=round(data.lat, 4),
        lng=round(data.lng, 4),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
