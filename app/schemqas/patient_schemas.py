# app/schemas/patient_schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, time, datetime
from enum import Enum

from app.models.all_models import (
    Gender, Priority, CaseSeverity, AmbulancePriority
)

# Patient Schemas
class PatientBase(BaseModel):
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district_id: Optional[UUID] = None
    area_id: Optional[UUID] = None
    postal_code: Optional[str] = None
    national_id: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: UUID
    user_id: UUID
    patient_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Appointment Schemas
class AppointmentBase(BaseModel):
    service_id: UUID
    department_id: UUID
    appointment_date: date
    appointment_time: time
    symptoms: Optional[str] = None
    special_requirements: Optional[str] = None
    notes: Optional[str] = None
    priority: Priority = Priority.MEDIUM

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    symptoms: Optional[str] = None
    special_requirements: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[Priority] = None

class AppointmentResponse(AppointmentBase):
    id: UUID
    patient_id: UUID
    doctor_id: Optional[UUID] = None
    status: str
    estimated_duration: int
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Ambulance Booking Schemas
class AmbulanceBookingBase(BaseModel):
    case_severity: CaseSeverity
    priority: AmbulancePriority
    pickup_location: str
    pickup_district_id: Optional[UUID] = None
    pickup_area_id: Optional[UUID] = None
    pickup_coordinates: Optional[str] = None
    destination: str
    destination_district_id: Optional[UUID] = None
    destination_area_id: Optional[UUID] = None
    destination_coordinates: Optional[str] = None
    requested_datetime: datetime
    patient_condition: Optional[str] = None
    special_equipment_needed: Optional[str] = None
    vital_signs: Optional[Dict[str, Any]] = None
    medical_history: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    insurance_coverage: bool = False
    notes: Optional[str] = None

class AmbulanceBookingCreate(AmbulanceBookingBase):
    pass

class AmbulanceBookingUpdate(BaseModel):
    patient_condition: Optional[str] = None
    special_equipment_needed: Optional[str] = None
    vital_signs: Optional[Dict[str, Any]] = None
    medical_history: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    notes: Optional[str] = None

class AmbulanceBookingResponse(AmbulanceBookingBase):
    id: UUID
    patient_id: UUID
    driver_id: Optional[UUID] = None
    ambulance_id: Optional[UUID] = None
    status: str
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    distance_km: Optional[float] = None
    assigned_at: Optional[datetime] = None
    en_route_pickup_at: Optional[datetime] = None
    arrived_pickup_at: Optional[datetime] = None
    transporting_at: Optional[datetime] = None
    en_route_hospital_at: Optional[datetime] = None
    arrived_hospital_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True