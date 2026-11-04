from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    contacts = relationship("TrustedContact", back_populates="user", cascade="all, delete-orphan")
    guardian_sessions = relationship("GuardianSession", back_populates="user", cascade="all, delete-orphan")


class TrustedContact(Base):
    __tablename__ = "trusted_contacts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=False)

    user = relationship("User", back_populates="contacts")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_lat_lng", "lat", "lng"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String(20), nullable=False)  # poca_luz, acoso, calle_sola, zona_segura
    severity = Column(Integer, nullable=False)  # 1-5
    description = Column(String(280), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class SafePoint(Base):
    __tablename__ = "safe_points"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    kind = Column(String(20), nullable=False)  # cai, farmacia, tienda, gasolinera
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    open_24h = Column(Boolean, default=False, nullable=False)


class GuardianSession(Base):
    __tablename__ = "guardian_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    eta_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, arrived, alert
    last_lat = Column(Float, nullable=False)
    last_lng = Column(Float, nullable=False)

    user = relationship("User", back_populates="guardian_sessions")
