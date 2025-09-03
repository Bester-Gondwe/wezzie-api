# app/routes/calendar/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.database import get_db
from app.models.all_models import User, Appointment, AppointmentStatus
from app.schemas.calenda import AppointmentResponse

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("/appointments", response_model=List[AppointmentResponse])
def get_calendar_appointments(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    doctor_id: Optional[UUID] = None,
    status: Optional[AppointmentStatus] = None,
    db: Session = Depends(get_db)
):
    """Get appointments for calendar view with filtering options"""
    query = db.query(Appointment)
    
    if start_date:
        query = query.filter(Appointment.appointment_date >= start_date)
    if end_date:
        query = query.filter(Appointment.appointment_date <= end_date)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if status:
        query = query.filter(Appointment.status == status)
    
    appointments = query.order_by(
        Appointment.appointment_date,
        Appointment.appointment_time
    ).all()
    
    return appointments


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def get_appointment_details(appointment_id: UUID, db: Session = Depends(get_db)):
    """Get detailed information for a specific appointment"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )
    
    return appointment


@router.get("/availability/{doctor_id}")
def get_doctor_availability(
    doctor_id: UUID,
    date: str,
    db: Session = Depends(get_db)
):
    """Get available time slots for a doctor on a specific date"""
    # Get existing appointments for the doctor on the given date
    existing_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == date,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
    ).all()
    
    # Generate available time slots (simplified example)
    # In a real implementation, you'd consider doctor's working hours, breaks, etc.
    booked_times = [appt.appointment_time for appt in existing_appointments]
    
    # Sample available time slots (9 AM to 5 PM in 30-minute intervals)
    available_slots = []
    for hour in range(9, 17):
        for minute in [0, 30]:
            time_slot = f"{hour:02d}:{minute:02d}:00"
            if time_slot not in booked_times:
                available_slots.append(time_slot)
    
    return {
        "doctor_id": doctor_id,
        "date": date,
        "available_slots": available_slots,
        "booked_slots": booked_times
    }