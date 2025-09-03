# app/routes/staff/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.all_models import (
    User, StaffProfile, Appointment, AmbulanceBooking, Inquiry, InquiryResponse,
    Department, PatientProfile, UserRole, AppointmentStatus,
    AmbulanceStatus, InquiryStatus
)
from app.utils import get_current_user

router = APIRouter(prefix="/staff", tags=["staff"])


# ===== Role-based security helpers =====
def require_roles(allowed_roles: list):
    """Decorator to require specific user roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ===== ROUTES =====

# ---- Staff Profile ----
@router.get("/profile")
async def get_staff_profile(
    current_user: User = Depends(require_roles([
        UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN,
        UserRole.RECEPTIONIST, UserRole.AMBULANCE_DRIVER
    ])),
    db: Session = Depends(get_db)
):
    staff_profile = db.query(StaffProfile).filter(
        StaffProfile.user_id == current_user.id
    ).first()
    if not staff_profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")
    return staff_profile


@router.put("/profile")
async def update_staff_profile(
    profile_update: dict,
    current_user: User = Depends(require_roles([
        UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN,
        UserRole.RECEPTIONIST, UserRole.AMBULANCE_DRIVER
    ])),
    db: Session = Depends(get_db)
):
    staff_profile = db.query(StaffProfile).filter(
        StaffProfile.user_id == current_user.id
    ).first()
    if not staff_profile:
        raise HTTPException(status_code=404, detail="Staff profile not found")

    for field, value in profile_update.items():
        if hasattr(staff_profile, field):
            setattr(staff_profile, field, value)

    db.commit()
    db.refresh(staff_profile)
    return staff_profile


# ---- Appointments ----
@router.get("/appointments")
async def get_staff_appointments(
    status: Optional[AppointmentStatus] = None,
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE])),
    db: Session = Depends(get_db)
):
    query = db.query(Appointment).filter(
        (Appointment.doctor_id == current_user.id) |
        (Appointment.department_id.in_(
            db.query(StaffProfile.department_id).filter(StaffProfile.user_id == current_user.id)
        ))
    )
    if status:
        query = query.filter(Appointment.status == status)

    return query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()


@router.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: UUID,
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE])),
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.put("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: UUID,
    appointment_update: dict,
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE])),
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    for field, value in appointment_update.items():
        if hasattr(appointment, field):
            setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)
    return appointment


# ---- Ambulance ----
@router.get("/ambulance-bookings")
async def get_ambulance_bookings(
    status: Optional[AmbulanceStatus] = None,
    current_user: User = Depends(require_roles([UserRole.AMBULANCE_DRIVER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    query = db.query(AmbulanceBooking)
    if status:
        query = query.filter(AmbulanceBooking.status == status)
    return query.order_by(AmbulanceBooking.requested_datetime.desc()).all()


@router.get("/ambulance-bookings/{booking_id}")
async def get_ambulance_booking(
    booking_id: UUID,
    current_user: User = Depends(require_roles([UserRole.AMBULANCE_DRIVER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    booking = db.query(AmbulanceBooking).filter(AmbulanceBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Ambulance booking not found")
    return booking


@router.put("/ambulance-bookings/{booking_id}")
async def update_ambulance_booking(
    booking_id: UUID,
    booking_update: dict,
    current_user: User = Depends(require_roles([UserRole.AMBULANCE_DRIVER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    booking = db.query(AmbulanceBooking).filter(AmbulanceBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Ambulance booking not found")

    for field, value in booking_update.items():
        if hasattr(booking, field):
            setattr(booking, field, value)

    db.commit()
    db.refresh(booking)
    return booking


# ---- Inquiries ----
@router.get("/inquiries")
async def get_inquiries(
    status: Optional[InquiryStatus] = None,
    category: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.RECEPTIONIST, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    query = db.query(Inquiry)
    if status:
        query = query.filter(Inquiry.status == status)
    if category:
        query = query.filter(Inquiry.category == category)
    return query.order_by(Inquiry.created_at.desc()).all()


@router.get("/inquiries/{inquiry_id}")
async def get_inquiry(
    inquiry_id: UUID,
    current_user: User = Depends(require_roles([UserRole.RECEPTIONIST, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return inquiry


@router.post("/inquiries/{inquiry_id}/respond")
async def respond_to_inquiry(
    inquiry_id: UUID,
    response_data: dict,
    current_user: User = Depends(require_roles([UserRole.RECEPTIONIST, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    response = InquiryResponse(
        inquiry_id=inquiry_id,
        responder_id=current_user.id,
        message=response_data.get("message"),
        is_internal_note=response_data.get("is_internal_note", False),
        response_method=response_data.get("response_method")
    )
    db.add(response)

    if not response_data.get("is_internal_note", False):
        inquiry.status = InquiryStatus.RESOLVED
        inquiry.resolved_at = db.execute(text("CURRENT_TIMESTAMP")).scalar()

    db.commit()
    db.refresh(response)
    return response


# ---- Patients ----
@router.get("/patients")
async def get_patients(
    search: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    query = db.query(User).join(PatientProfile).filter(User.role == UserRole.PATIENT)
    if search:
        query = query.filter(
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%")) |
            (PatientProfile.patient_id.ilike(f"%{search}%"))
        )
    return query.all()


@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: UUID,
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient = db.query(User).filter(User.id == patient_id, User.role == UserRole.PATIENT).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# ---- Departments ----
@router.get("/departments")
async def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).filter(Department.is_active == True).all()


@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department(
    department_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing_department = db.query(Department).filter(
        (Department.name == department_data.get("name")) |
        (Department.code == department_data.get("code"))
    ).first()
    if existing_department:
        raise HTTPException(status_code=400, detail="Department with this name or code already exists")

    department = Department(**department_data)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.put("/departments/{department_id}")
async def update_department(
    department_id: UUID,
    department_update: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    for field, value in department_update.items():
        if hasattr(department, field):
            setattr(department, field, value)

    db.commit()
    db.refresh(department)
    return department


# ---- Staff Members ----
@router.get("/staff-members")
async def get_staff_members(
    department_id: Optional[UUID] = None,
    role: Optional[UserRole] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    query = db.query(User).join(StaffProfile).filter(
        User.role.in_([UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.AMBULANCE_DRIVER])
    )
    if department_id:
        query = query.filter(StaffProfile.department_id == department_id)
    if role:
        query = query.filter(User.role == role)
    return query.all()


# ---- Dashboard ----
@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    return {
        "total_patients": db.query(User).filter(User.role == UserRole.PATIENT).count(),
        "total_appointments": db.query(Appointment).count(),
        "pending_appointments": db.query(Appointment).filter(Appointment.status == AppointmentStatus.SCHEDULED).count(),
        "total_inquiries": db.query(Inquiry).count(),
        "open_inquiries": db.query(Inquiry).filter(Inquiry.status == InquiryStatus.OPEN).count(),
    }


# ---- Reports ----
@router.get("/reports/appointments")
async def get_appointment_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    department_id: Optional[UUID] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)
    if start_date:
        query = query.filter(Appointment.appointment_date >= start_date)
    if end_date:
        query = query.filter(Appointment.appointment_date <= end_date)
    if department_id:
        query = query.filter(Appointment.department_id == department_id)
    return query.all()


@router.get("/reports/ambulance-bookings")
async def get_ambulance_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[AmbulanceStatus] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    query = db.query(AmbulanceBooking)
    if start_date:
        query = query.filter(AmbulanceBooking.requested_datetime >= start_date)
    if end_date:
        query = query.filter(AmbulanceBooking.requested_datetime <= end_date)
    if status:
        query = query.filter(AmbulanceBooking.status == status)
    return query.all()
