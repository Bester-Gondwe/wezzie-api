# app//calendar/route.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime, date, time, timedelta
import uuid

from app.database import get_db
from app.models.all_models import (
    Appointment, User, Department, Service, StaffProfile, 
    PatientProfile, AppointmentStatus, Priority, UserRole
)
from app.utils import require_admin,get_current_user
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse,
    AppointmentCalendarEvent
)


router = APIRouter()

@router.get("/", response_model=List[AppointmentResponse])
async def get_appointments(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    department_id: Optional[uuid.UUID] = None,
    doctor_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get appointments with optional filters for calendar view
    """
    try:
        # Build query with filters
        query = db.query(Appointment)
        
        # Date range filter
        if start_date and end_date:
            query = query.filter(
                and_(
                    Appointment.appointment_date >= start_date,
                    Appointment.appointment_date <= end_date
                )
            )
        elif start_date:
            query = query.filter(Appointment.appointment_date >= start_date)
        elif end_date:
            query = query.filter(Appointment.appointment_date <= end_date)
        
        # Additional filters
        if department_id:
            query = query.filter(Appointment.department_id == department_id)
        
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        
        if status:
            # Convert string status to enum
            status_enum = AppointmentStatus(status)
            query = query.filter(Appointment.status == status_enum)
        
        # Order by date and time
        appointments = query.order_by(
            Appointment.appointment_date,
            Appointment.appointment_time
        ).all()
        
        return appointments
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status value: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving appointments: {str(e)}"
        )

@router.get("/calendar-events", response_model=List[AppointmentCalendarEvent])
async def get_calendar_events(
    start: date,
    end: date,
    department_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get appointments formatted as calendar events for FullCalendar
    """
    try:
        query = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date >= start,
                Appointment.appointment_date <= end
            )
        )
        
        if department_id:
            query = query.filter(Appointment.department_id == department_id)
        
        appointments = query.all()
        
        calendar_events = []
        for appointment in appointments:
            # Get patient and doctor details
            patient = db.query(User).filter(User.id == appointment.patient_id).first()
            doctor = db.query(User).filter(User.id == appointment.doctor_id).first() if appointment.doctor_id else None
            department = db.query(Department).filter(Department.id == appointment.department_id).first()
            service = db.query(Service).filter(Service.id == appointment.service_id).first()
            
            # Format event title
            patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown Patient"
            doctor_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Unassigned"
            title = f"{patient_name} - {doctor_name}"
            
            # Create datetime objects for start and end
            start_datetime = datetime.combine(appointment.appointment_date, appointment.appointment_time)
            end_datetime = start_datetime + timedelta(minutes=appointment.estimated_duration or 30)
            
            calendar_events.append(AppointmentCalendarEvent(
                id=appointment.id,
                title=title,
                start=start_datetime.isoformat(),
                end=end_datetime.isoformat(),
                patient_id=appointment.patient_id,
                patient_name=patient_name,
                doctor_id=appointment.doctor_id,
                doctor_name=doctor_name,
                department_id=appointment.department_id,
                department_name=department.name if department else "Unknown",
                service_id=appointment.service_id,
                service_name=service.name if service else "Unknown",
                status=appointment.status,
                priority=appointment.priority,
                symptoms=appointment.symptoms,
                notes=appointment.notes
            ))
        
        return calendar_events
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving calendar events: {str(e)}"
        )

@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new appointment
    """
    try:
        # Check if patient exists
        patient = db.query(User).filter(User.id == appointment_data.patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Check if doctor exists (if provided)
        if appointment_data.doctor_id:
            doctor = db.query(User).filter(User.id == appointment_data.doctor_id).first()
            if not doctor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Doctor not found"
                )
            # Check if user is actually a doctor/nurse
            if doctor.role not in [UserRole.DOCTOR, UserRole.NURSE]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specified user is not a medical professional"
                )
        
        # Check if department exists
        department = db.query(Department).filter(Department.id == appointment_data.department_id).first()
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Check if service exists
        service = db.query(Service).filter(Service.id == appointment_data.service_id).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
        
        # Check for scheduling conflicts (only if doctor is assigned)
        if appointment_data.doctor_id:
            existing_appointment = db.query(Appointment).filter(
                and_(
                    Appointment.doctor_id == appointment_data.doctor_id,
                    Appointment.appointment_date == appointment_data.appointment_date,
                    Appointment.appointment_time == appointment_data.appointment_time,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
                )
            ).first()
            
            if existing_appointment:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Doctor already has an appointment at this time"
                )
        
        # Create new appointment
        db_appointment = Appointment(
            **appointment_data.dict(),
            created_by=current_user.id
        )
        
        db.add(db_appointment)
        db.commit()
        db.refresh(db_appointment)
        
        return db_appointment
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )

@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: uuid.UUID,
    appointment_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update an existing appointment
    """
    try:
        # Find the appointment
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Check for scheduling conflicts if time or doctor is being changed
        update_data = appointment_data.dict(exclude_unset=True)
        doctor_id = update_data.get('doctor_id', appointment.doctor_id)
        check_date = update_data.get('appointment_date', appointment.appointment_date)
        check_time = update_data.get('appointment_time', appointment.appointment_time)
        
        if doctor_id and (update_data.get('appointment_date') or update_data.get('appointment_time')):
            existing_appointment = db.query(Appointment).filter(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date == check_date,
                    Appointment.appointment_time == check_time,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                    Appointment.id != appointment_id
                )
            ).first()
            
            if existing_appointment:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Doctor already has an appointment at this time"
                )
        
        # Update appointment fields
        for field, value in update_data.items():
            setattr(appointment, field, value)
        
        appointment.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(appointment)
        
        return appointment
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating appointment: {str(e)}"
        )

@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete an appointment
    """
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        db.delete(appointment)
        db.commit()
        
        return {"message": "Appointment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting appointment: {str(e)}"
        )

@router.get("/departments")
async def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get all departments for dropdown selection
    """
    try:
        departments = db.query(Department).filter(Department.is_active == True).all()
        return departments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving departments: {str(e)}"
        )

@router.get("/doctors")
async def get_doctors(
    department_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get doctors for dropdown selection, optionally filtered by department
    """
    try:
        query = db.query(User).join(StaffProfile).filter(
            User.role.in_([UserRole.DOCTOR, UserRole.NURSE]),
            User.is_active == True
        )
        
        if department_id:
            query = query.filter(StaffProfile.department_id == department_id)
        
        doctors = query.all()
        return doctors
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving doctors: {str(e)}"
        )

@router.get("/services")
async def get_services(
    department_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get services for dropdown selection, optionally filtered by department
    """
    try:
        query = db.query(Service).filter(Service.is_active == True)
        
        if department_id:
            query = query.filter(Service.department_id == department_id)
        
        services = query.all()
        return services
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving services: {str(e)}"
        )