from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import pytz
import re

from app.database import get_db
from app.models.all_models import (
    User, PatientProfile, Appointment, AmbulanceBooking, 
    District, Area, Service, Department, UserRole,
    AppointmentStatus, CaseSeverity, AmbulancePriority, AmbulanceStatus
)
from app.routes.patients.patient_schemas import (
    PatientCreate, PatientUpdate,
    AppointmentCreate, AppointmentUpdate,
    AmbulanceBookingCreate, AmbulanceBookingUpdate
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/patients", tags=["patients"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def require_patient(current_user: User = Depends(get_current_user)) -> User:
    """Require patient role."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user

def sanitize_input(value: str) -> str:
    """Sanitize input strings to prevent injection attacks."""
    if not isinstance(value, str):
        return value
    # Remove potentially dangerous characters and excessive whitespace
    value = re.sub(r'[<>;]', '', value.strip())
    value = re.sub(r'\s+', ' ', value)
    return value

@router.get("/profile")
async def get_patient_profile(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient profile not found"
            )
        
        return patient_profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving patient profile: {str(e)}"
        )

@router.put("/profile")
async def update_patient_profile(
    profile_update: PatientUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.user_id == current_user.id
        ).first()
        
        if not patient_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient profile not found"
            )
        
        update_data = profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if isinstance(value, str):
                    value = sanitize_input(value)
                setattr(patient_profile, field, value)
        
        patient_profile.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
        
        db.commit()
        db.refresh(patient_profile)
        
        return patient_profile
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating patient profile: {str(e)}"
        )

@router.get("/appointments")
async def get_patient_appointments(
    status: Optional[AppointmentStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Appointment).filter(
            Appointment.patient_id == current_user.id
        )
        
        if status:
            query = query.filter(Appointment.status == status)
        
        appointments = query.order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc()
        ).offset(skip).limit(limit).all()
        
        return appointments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving appointments: {str(e)}"
        )

@router.post("/appointments", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        # Validate service
        service = db.query(Service).filter(
            Service.id == appointment_data.service_id,
            Service.is_active == True
        ).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found or inactive"
            )
        
        # Validate department
        department = db.query(Department).filter(
            Department.id == appointment_data.department_id,
            Department.is_active == True
        ).first()
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found or inactive"
            )
        
        # Validate appointment date is not in the past
        current_time = datetime.now(pytz.timezone('Africa/Blantyre'))
        appointment_datetime = datetime.combine(
            appointment_data.appointment_date,
            appointment_data.appointment_time
        )
        if appointment_datetime < current_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule appointments in the past"
            )
        
        # Sanitize string inputs
        appointment_dict = appointment_data.dict()
        for field in ['symptoms', 'special_requirements', 'notes']:
            if appointment_dict.get(field):
                appointment_dict[field] = sanitize_input(appointment_dict[field])
        
        appointment = Appointment(
            **appointment_dict,
            patient_id=current_user.id,
            created_by=current_user.id,
            created_at=current_time,
            updated_at=current_time
        )
        
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        return appointment
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )

@router.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: UUID,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_user.id
        ).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        return appointment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving appointment: {str(e)}"
        )

@router.put("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: UUID,
    appointment_update: AppointmentUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_user.id
        ).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify completed or cancelled appointments"
            )
        
        update_data = appointment_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if isinstance(value, str):
                    value = sanitize_input(value)
                setattr(appointment, field, value)
        
        appointment.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
        
        db.commit()
        db.refresh(appointment)
        
        return appointment
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating appointment: {str(e)}"
        )

@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(
    appointment_id: UUID,
    cancellation_reason: str = Query(..., min_length=5, max_length=500),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_user.id
        ).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        if appointment.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment is already cancelled"
            )
        
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = sanitize_input(cancellation_reason)
        appointment.cancelled_at = datetime.now(pytz.timezone('Africa/Blantyre'))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling appointment: {str(e)}"
        )

@router.get("/ambulance-bookings")
async def get_patient_ambulance_bookings(
    status: Optional[AmbulanceStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(AmbulanceBooking).filter(
            AmbulanceBooking.patient_id == current_user.id
        )
        
        if status:
            query = query.filter(AmbulanceBooking.status == status)
        
        bookings = query.order_by(
            AmbulanceBooking.requested_datetime.desc()
        ).offset(skip).limit(limit).all()
        
        return bookings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving ambulance bookings: {str(e)}"
        )

@router.post("/ambulance-bookings", status_code=status.HTTP_201_CREATED)
async def create_ambulance_booking(
    booking_data: AmbulanceBookingCreate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        # Validate districts and areas
        if booking_data.pickup_district_id:
            pickup_district = db.query(District).filter(
                District.id == booking_data.pickup_district_id,
                District.is_active == True
            ).first()
            if not pickup_district:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pickup district not found or inactive"
                )
        
        if booking_data.pickup_area_id:
            pickup_area = db.query(Area).filter(
                Area.id == booking_data.pickup_area_id,
                Area.is_serviced == True
            ).first()
            if not pickup_area:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pickup area not found or not serviced"
                )
        
        if booking_data.destination_district_id:
            dest_district = db.query(District).filter(
                District.id == booking_data.destination_district_id,
                District.is_active == True
            ).first()
            if not dest_district:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Destination district not found or inactive"
                )
        
        if booking_data.destination_area_id:
            dest_area = db.query(Area).filter(
                Area.id == booking_data.destination_area_id,
                Area.is_serviced == True
            ).first()
            if not dest_area:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Destination area not found or not serviced"
                )
        
        # Validate requested datetime
        current_time = datetime.now(pytz.timezone('Africa/Blantyre'))
        if booking_data.requested_datetime < current_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule bookings in the past"
            )
        
        # Sanitize string inputs
        booking_dict = booking_data.dict()
        for field in ['pickup_location', 'destination', 'patient_condition', 
                     'special_equipment_needed', 'medical_history', 
                     'contact_person_name', 'contact_person_phone', 'notes']:
            if booking_dict.get(field):
                booking_dict[field] = sanitize_input(booking_dict[field])
        
        booking = AmbulanceBooking(
            **booking_dict,
            patient_id=current_user.id,
            created_at=current_time,
            updated_at=current_time
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        return booking
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating ambulance booking: {str(e)}"
        )

@router.get("/ambulance-bookings/{booking_id}")
async def get_ambulance_booking(
    booking_id: UUID,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        booking = db.query(AmbulanceBooking).filter(
            AmbulanceBooking.id == booking_id,
            AmbulanceBooking.patient_id == current_user.id
        ).first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ambulance booking not found"
            )
        
        return booking
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving ambulance booking: {str(e)}"
        )

@router.put("/ambulance-bookings/{booking_id}")
async def update_ambulance_booking(
    booking_id: UUID,
    booking_update: AmbulanceBookingUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        booking = db.query(AmbulanceBooking).filter(
            AmbulanceBooking.id == booking_id,
            AmbulanceBooking.patient_id == current_user.id
        ).first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ambulance booking not found"
            )
        
        if booking.status in [AmbulanceStatus.COMPLETED, AmbulanceStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify completed or cancelled ambulance bookings"
            )
        
        update_data = booking_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if isinstance(value, str):
                    value = sanitize_input(value)
                setattr(booking, field, value)
        
        booking.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
        
        db.commit()
        db.refresh(booking)
        
        return booking
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating ambulance booking: {str(e)}"
        )

@router.delete("/ambulance-bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_ambulance_booking(
    booking_id: UUID,
    cancellation_reason: str = Query(..., min_length=5, max_length=500),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    try:
        booking = db.query(AmbulanceBooking).filter(
            AmbulanceBooking.id == booking_id,
            AmbulanceBooking.patient_id == current_user.id
        ).first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ambulance booking not found"
            )
        
        if booking.status == AmbulanceStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ambulance booking is already cancelled"
            )
        
        booking.status = AmbulanceStatus.CANCELLED
        booking.cancellation_reason = sanitize_input(cancellation_reason)
        booking.cancelled_at = datetime.now(pytz.timezone('Africa/Blantyre'))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling ambulance booking: {str(e)}"
        )

@router.get("/districts")
async def get_districts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        districts = db.query(District).filter(District.is_active == True).all()
        return [{"id": d.id, "name": d.name, "code": d.code} for d in districts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving districts: {str(e)}"
        )

@router.get("/districts/{district_id}/areas")
async def get_district_areas(
    district_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate district exists
        district = db.query(District).filter(
            District.id == district_id,
            District.is_active == True
        ).first()
        if not district:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="District not found or inactive"
            )
        
        areas = db.query(Area).filter(
            Area.district_id == district_id,
            Area.is_serviced == True
        ).all()
        return [{"id": a.id, "name": a.name, "code": a.code} for a in areas]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving areas: {str(e)}"
        )

@router.get("/services")
async def get_services(
    department_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Service).filter(Service.is_active == True)
        
        if department_id:
            # Validate department exists
            department = db.query(Department).filter(
                Department.id == department_id,
                Department.is_active == True
            ).first()
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Department not found or inactive"
                )
            query = query.filter(Service.department_id == department_id)
        
        services = query.all()
        return [{"id": s.id, "name": s.name, "code": s.code} for s in services]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving services: {str(e)}"
        )

@router.get("/departments")
async def get_departments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        departments = db.query(Department).filter(Department.is_active == True).all()
        return [{"id": d.id, "name": d.name, "code": d.code} for d in departments]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving departments: {str(e)}"
        )