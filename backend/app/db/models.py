from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Ghost(Base):
    __tablename__ = "ghosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    anxiety_level: Mapped[int] = mapped_column(Integer, nullable=False)
    favorite_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    relocation_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    special_conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment: Mapped["Assignment | None"] = relationship(
        back_populates="ghost", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_type: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    occupied: Mapped[int] = mapped_column(Integer, default=0)
    lighting: Mapped[str] = mapped_column(String(20), nullable=False)
    noise_level: Mapped[int] = mapped_column(Integer, nullable=False)
    humidity: Mapped[str] = mapped_column(String(20), nullable=False)
    ambient_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    has_people: Mapped[bool] = mapped_column(Boolean, default=False)
    has_mirrors: Mapped[bool] = mapped_column(Boolean, default=False)
    has_attic: Mapped[bool] = mapped_column(Boolean, default=False)
    restrictions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments: Mapped[list["Assignment"]] = relationship(back_populates="location")

    @property
    def free_capacity(self) -> int:
        return self.capacity - self.occupied


class Assignment(Base):
    """Текущее распределение: одно привидение -> одно место (или ручной выбор)."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ghost_id: Mapped[int] = mapped_column(ForeignKey("ghosts.id", ondelete="CASCADE"), unique=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[list[str]] = mapped_column(JSON, default=list)
    manual: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ghost: Mapped["Ghost"] = relationship(back_populates="assignment")
    location: Mapped["Location"] = relationship(back_populates="assignments")
