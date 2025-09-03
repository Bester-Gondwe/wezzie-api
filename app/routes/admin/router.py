from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import date
from uuid import UUID
from sqlalchemy import func
from app.database import get_db
from app.models.all_models import (
    BLANTYRE_TZ, User, Appointment, Ambulance, Notification, AppointmentStatus, AmbulanceStatus, UserRole, NotificationType
)
from app.utils.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

# Pydantic models for response schemas
class DashboardMetric(BaseModel):
    title: str
    value: str
    icon: str
    color: str

class AppointmentResponse(BaseModel):
    id: UUID
    patient: str
    date: date
    time: str
    status: AppointmentStatus

    class Config:
        orm_mode = True

class AmbulanceResponse(BaseModel):
    id: str
    status: AmbulanceStatus
    location: str

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: UUID
    name: str
    role: UserRole
    status: str

    class Config:
        orm_mode = True

class NotificationResponse(BaseModel):
    message: str
    time: str
    type: str

    class Config:
        orm_mode = True

# Dashboard Metrics Endpoint
@router.get("/admin/dashboard/metrics", response_model=List[DashboardMetric])
async def get_dashboard_metrics(db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    total_users = db.query(func.count(User.id)).scalar()
    today = date.today()
    appointments_today = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_date == today,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.IN_PROGRESS])
    ).scalar()
    ambulances_available = db.query(func.count(Ambulance.id)).filter(
        Ambulance.is_operational == True
    ).scalar()
    resources_in_use = db.query(func.count(Appointment.id)).filter(
        Appointment.status == AppointmentStatus.IN_PROGRESS
    ).scalar()
    pending_notifications = db.query(func.count(Notification.id)).filter(
        Notification.is_read == False
    ).scalar()

    metrics = [
        {"title": "Total Users", "value": str(total_users), "icon": "Users", "color": "text-blue-600"},
        {"title": "Appointments Today", "value": str(appointments_today), "icon": "Calendar", "color": "text-green-600"},
        {"title": "Ambulances Available", "value": str(ambulances_available), "icon": "Ambulance", "color": "text-red-600"},
        {"title": "Resources In Use", "value": str(resources_in_use), "icon": "Clipboard", "color": "text-purple-600"},
        {"title": "Pending Notifications", "value": str(pending_notifications), "icon": "Bell", "color": "text-yellow-600"},
    ]
    return metrics

# Recent Appointments Endpoint
@router.get("/admin/dashboard/appointments", response_model=List[AppointmentResponse])
async def get_recent_appointments(patient: str = "all", db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    query = db.query(Appointment).join(User, Appointment.patient_id == User.id)
    
    if patient != "all":
        patient_name = patient.replace("-", " ").title()
        query = query.filter(User.first_name + " " + User.last_name == patient_name)
    
    appointments = query.order_by(Appointment.created_at.desc()).limit(10).all()
    
    return [
        {
            "id": appointment.id,
            "patient": f"{appointment.patient.first_name} {appointment.patient.last_name}",
            "date": appointment.appointment_date,
            "time": appointment.appointment_time.strftime("%I:%M %p"),
            "status": appointment.status
        } for appointment in appointments
    ]

# Ambulances Endpoint
@router.get("/admin/dashboard/ambulances", response_model=List[AmbulanceResponse])
async def get_ambulances(db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    ambulances = db.query(Ambulance).order_by(Ambulance.created_at.desc()).limit(10).all()
    
    return [
        {
            "id": ambulance.registration_number,
            "status": AmbulanceStatus.REQUESTED if ambulance.bookings else AmbulanceStatus.COMPLETED,
            "location": ambulance.current_location or "Unknown"
        } for ambulance in ambulances
    ]

# Recent Users Endpoint
@router.get("/admin/dashboard/users", response_model=List[UserResponse])
async def get_recent_users(db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    
    return [
        {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "role": user.role,
            "status": "Active" if user.is_active else "Inactive"
        } for user in users
    ]

# Recent Notifications Endpoint
@router.get("/admin/dashboard/notifications", response_model=List[NotificationResponse])
async def get_recent_notifications(db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    from datetime import datetime
    notifications = db.query(Notification).order_by(Notification.created_at.desc()).limit(10).all()
    
    return [
        {
            "message": notification.message,
            "time": f"{(datetime.now(BLANTYRE_TZ) - notification.created_at).seconds // 60} minutes ago",
            "type": notification.type.value
        } for notification in notifications
    ]