# app/schemas/appointment.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time, datetime
from uuid import UUID
from app.models.all_models import AppointmentStatus, Priority

class AppointmentBase(BaseModel):
    patient_id: UUID
    doctor_id: Optional[UUID] = None
    service_id: UUID
    department_id: UUID
    appointment_date: date
    appointment_time: time
    estimated_duration: Optional[int] = 30
    status: Optional[AppointmentStatus] = AppointmentStatus.SCHEDULED
    priority: Optional[Priority] = Priority.MEDIUM
    symptoms: Optional[str] = None
    special_requirements: Optional[str] = None
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    doctor_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    estimated_duration: Optional[int] = None
    status: Optional[AppointmentStatus] = None
    priority: Optional[Priority] = None
    symptoms: Optional[str] = None
    special_requirements: Optional[str] = None
    notes: Optional[str] = None

class AppointmentResponse(AppointmentBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AppointmentCalendarEvent(BaseModel):
    id: UUID
    title: str
    start: str  # ISO format datetime
    end: str    # ISO format datetime
    patient_id: UUID
    patient_name: str
    doctor_id: Optional[UUID] = None
    doctor_name: Optional[str] = None
    department_id: UUID
    department_name: str
    service_id: UUID
    service_name: str
    status: AppointmentStatus
    priority: Priority
    symptoms: Optional[str] = None
    notes: Optional[str] = None