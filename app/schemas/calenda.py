# app/schemas/calendar_schemas.py
from pydantic import BaseModel
from uuid import UUID
from datetime import date, time
from typing import Optional
from app.models.all_models import AppointmentStatus, Priority

class AppointmentResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: Optional[UUID]
    service_id: UUID
    department_id: UUID
    appointment_date: date
    appointment_time: time
    estimated_duration: int
    status: AppointmentStatus
    priority: Priority
    symptoms: Optional[str]
    special_requirements: Optional[str]
    notes: Optional[str]
    
    class Config:
        from_attributes = True