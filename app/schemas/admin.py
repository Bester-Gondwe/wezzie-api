from pydantic import BaseModel, EmailStr
from datetime import datetime, date, time
from typing import Optional, List
from enum import Enum
from uuid import UUID

# Enums matching the SQLAlchemy models
class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class AmbulanceStatus(str, Enum):
    AVAILABLE = "Available"
    IN_USE = "In Use"
    MAINTENANCE = "Maintenance"

class UserStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"

# Response models
class DashboardMetric(BaseModel):
    title: str
    value: str
    icon: str
    color: str

    class Config:
        orm_mode = True

class AppointmentResponse(BaseModel):
    id: UUID
    patient: str
    date: date
    time: str
    status: AppointmentStatus

    class Config:
        orm_mode = True

class AmbulanceResponse(BaseModel):
    id: UUID
    registration_number: str
    status: AmbulanceStatus
    location: str

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: UUID
    name: str
    role: str
    status: UserStatus

    class Config:
        orm_mode = True

class NotificationResponse(BaseModel):
    message: str
    time: str
    type: str

    class Config:
        orm_mode = True

# Request models
class AdminStatsResponse(BaseModel):
    total_users: int
    appointments_today: int
    ambulances_available: int
    resources_in_use: int
    pending_notifications: int

    class Config:
        orm_mode = True