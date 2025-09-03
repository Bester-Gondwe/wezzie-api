# app/routes/staff/staff_schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum

from app.models.all_models import (
    UserRole, Gender, Priority, AppointmentStatus, 
    AmbulanceStatus, InquiryStatus, ResponseMethod
)

class StaffBase(BaseModel):
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    qualifications: Optional[str] = None
    years_of_experience: Optional[int] = 0
    consultation_fee: Optional[float] = None
    is_available_online: Optional[bool] = True
    working_hours: Optional[Dict[str, Any]] = None

class StaffCreate(StaffBase):
    pass

class StaffUpdate(StaffBase):
    pass

class StaffResponse(StaffBase):
    id: UUID
    user_id: UUID
    employee_id: str
    department_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class StaffUserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    role: UserRole
    profile_image: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Gender
    is_active: bool
    staff_profile: Optional[StaffResponse] = None
    
    class Config:
        from_attributes = True

class AppointmentUpdateRequest(BaseModel):
    status: Optional[AppointmentStatus] = None
    doctor_id: Optional[UUID] = None
    notes: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None

class AmbulanceBookingUpdateRequest(BaseModel):
    status: Optional[AmbulanceStatus] = None
    driver_id: Optional[UUID] = None
    ambulance_id: Optional[UUID] = None
    notes: Optional[str] = None
    estimated_cost: Optional[float] = None

class InquiryResponseRequest(BaseModel):
    message: str
    is_internal_note: Optional[bool] = False
    response_method: Optional[ResponseMethod] = None

class DepartmentBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    head_of_department_id: Optional[UUID] = None
    floor_number: Optional[int] = None
    location_description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True