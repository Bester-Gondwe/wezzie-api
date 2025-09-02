# # app/routes/patients/router.py
# from fastapi import APIRouter, Depends, HTTPException, status, Query
# from sqlalchemy import text
# from sqlalchemy.orm import Session
# from typing import List, Optional
# from uuid import UUID

# from app.database import get_db
# from app.models.all_models import (
#     User, PatientProfile, Appointment, AmbulanceBooking, 
#     District, Area, Service, Department, UserRole, Gender,
#     AppointmentStatus, CaseSeverity, AmbulancePriority, AmbulanceStatus
# )
# from app.schemas.patient_schemas import (
#     PatientCreate, PatientResponse, PatientUpdate,
#     AppointmentCreate, AppointmentResponse, AppointmentUpdate,
#     AmbulanceBookingCreate, AmbulanceBookingResponse, AmbulanceBookingUpdate
# )

# router = APIRouter(prefix="/patients", tags=["patients"])

# # Helper function to get current patient user (would be implemented with authentication)
# async def get_current_patient_user(db: Session = Depends(get_db)):
#     # This would be replaced with actual authentication logic
#     # For now, returning a mock user for demonstration
#     patient_user = db.query(User).filter(User.role == UserRole.PATIENT).first()
#     if not patient_user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Patient user not found"
#         )
#     return patient_user

# @router.get("/profile", response_model=PatientResponse)
# async def get_patient_profile(
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get the current patient's profile information.
#     """
#     patient_profile = db.query(PatientProfile).filter(
#         PatientProfile.user_id == current_user.id
#     ).first()
    
#     if not patient_profile:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Patient profile not found"
#         )
    
#     return patient_profile

# @router.put("/profile", response_model=PatientResponse)
# async def update_patient_profile(
#     profile_update: PatientUpdate,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Update the current patient's profile information.
#     """
#     patient_profile = db.query(PatientProfile).filter(
#         PatientProfile.user_id == current_user.id
#     ).first()
    
#     if not patient_profile:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Patient profile not found"
#         )
    
#     # Update profile fields
#     update_data = profile_update.dict(exclude_unset=True)
#     for field, value in update_data.items():
#         setattr(patient_profile, field, value)
    
#     db.commit()
#     db.refresh(patient_profile)
    
#     return patient_profile

# @router.get("/appointments", response_model=List[AppointmentResponse])
# async def get_patient_appointments(
#     status: Optional[AppointmentStatus] = None,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all appointments for the current patient.
#     Optionally filter by status.
#     """
#     query = db.query(Appointment).filter(
#         Appointment.patient_id == current_user.id
#     )
    
#     if status:
#         query = query.filter(Appointment.status == status)
    
#     appointments = query.order_by(
#         Appointment.appointment_date.desc(),
#         Appointment.appointment_time.desc()
#     ).all()
    
#     return appointments

# @router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
# async def create_appointment(
#     appointment_data: AppointmentCreate,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Create a new appointment for the current patient.
#     """
#     # Validate service exists
#     service = db.query(Service).filter(Service.id == appointment_data.service_id).first()
#     if not service:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Service not found"
#         )
    
#     # Validate department exists
#     department = db.query(Department).filter(Department.id == appointment_data.department_id).first()
#     if not department:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Department not found"
#         )
    
#     # Create appointment
#     appointment = Appointment(
#         patient_id=current_user.id,
#         service_id=appointment_data.service_id,
#         department_id=appointment_data.department_id,
#         appointment_date=appointment_data.appointment_date,
#         appointment_time=appointment_data.appointment_time,
#         symptoms=appointment_data.symptoms,
#         special_requirements=appointment_data.special_requirements,
#         notes=appointment_data.notes,
#         priority=appointment_data.priority,
#         created_by=current_user.id
#     )
    
#     db.add(appointment)
#     db.commit()
#     db.refresh(appointment)
    
#     return appointment

# @router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
# async def get_appointment(
#     appointment_id: UUID,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get a specific appointment by ID.
#     """
#     appointment = db.query(Appointment).filter(
#         Appointment.id == appointment_id,
#         Appointment.patient_id == current_user.id
#     ).first()
    
#     if not appointment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Appointment not found"
#         )
    
#     return appointment

# @router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
# async def update_appointment(
#     appointment_id: UUID,
#     appointment_update: AppointmentUpdate,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Update a specific appointment.
#     """
#     appointment = db.query(Appointment).filter(
#         Appointment.id == appointment_id,
#         Appointment.patient_id == current_user.id
#     ).first()
    
#     if not appointment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Appointment not found"
#         )
    
#     # Check if appointment can be modified
#     if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cannot modify completed or cancelled appointments"
#         )
    
#     # Update appointment fields
#     update_data = appointment_update.dict(exclude_unset=True)
#     for field, value in update_data.items():
#         setattr(appointment, field, value)
    
#     db.commit()
#     db.refresh(appointment)
    
#     return appointment

# @router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def cancel_appointment(
#     appointment_id: UUID,
#     cancellation_reason: str = Query(..., description="Reason for cancellation"),
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Cancel a specific appointment.
#     """
#     appointment = db.query(Appointment).filter(
#         Appointment.id == appointment_id,
#         Appointment.patient_id == current_user.id
#     ).first()
    
#     if not appointment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Appointment not found"
#         )
    
#     if appointment.status == AppointmentStatus.CANCELLED:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Appointment is already cancelled"
#         )
    
#     appointment.status = AppointmentStatus.CANCELLED
#     appointment.cancellation_reason = cancellation_reason
#     appointment.cancelled_at = db.execute(text("CURRENT_TIMESTAMP")).scalar()
    
#     db.commit()

# @router.get("/ambulance-bookings", response_model=List[AmbulanceBookingResponse])
# async def get_patient_ambulance_bookings(
#     status: Optional[AmbulanceStatus] = None,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all ambulance bookings for the current patient.
#     Optionally filter by status.
#     """
#     query = db.query(AmbulanceBooking).filter(
#         AmbulanceBooking.patient_id == current_user.id
#     )
    
#     if status:
#         query = query.filter(AmbulanceBooking.status == status)
    
#     bookings = query.order_by(
#         AmbulanceBooking.requested_datetime.desc()
#     ).all()
    
#     return bookings

# @router.post("/ambulance-bookings", response_model=AmbulanceBookingResponse, status_code=status.HTTP_201_CREATED)
# async def create_ambulance_booking(
#     booking_data: AmbulanceBookingCreate,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Create a new ambulance booking for the current patient.
#     """
#     # Validate districts and areas exist
#     if booking_data.pickup_district_id:
#         pickup_district = db.query(District).filter(District.id == booking_data.pickup_district_id).first()
#         if not pickup_district:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Pickup district not found"
#             )
    
#     if booking_data.pickup_area_id:
#         pickup_area = db.query(Area).filter(Area.id == booking_data.pickup_area_id).first()
#         if not pickup_area:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Pickup area not found"
#             )
    
#     if booking_data.destination_district_id:
#         dest_district = db.query(District).filter(District.id == booking_data.destination_district_id).first()
#         if not dest_district:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Destination district not found"
#             )
    
#     if booking_data.destination_area_id:
#         dest_area = db.query(Area).filter(Area.id == booking_data.destination_area_id).first()
#         if not dest_area:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Destination area not found"
#             )
    
#     # Create ambulance booking
#     booking = AmbulanceBooking(
#         patient_id=current_user.id,
#         case_severity=booking_data.case_severity,
#         priority=booking_data.priority,
#         pickup_location=booking_data.pickup_location,
#         pickup_district_id=booking_data.pickup_district_id,
#         pickup_area_id=booking_data.pickup_area_id,
#         pickup_coordinates=booking_data.pickup_coordinates,
#         destination=booking_data.destination,
#         destination_district_id=booking_data.destination_district_id,
#         destination_area_id=booking_data.destination_area_id,
#         destination_coordinates=booking_data.destination_coordinates,
#         requested_datetime=booking_data.requested_datetime,
#         patient_condition=booking_data.patient_condition,
#         special_equipment_needed=booking_data.special_equipment_needed,
#         vital_signs=booking_data.vital_signs,
#         medical_history=booking_data.medical_history,
#         contact_person_name=booking_data.contact_person_name,
#         contact_person_phone=booking_data.contact_person_phone,
#         insurance_coverage=booking_data.insurance_coverage,
#         notes=booking_data.notes
#     )
    
#     db.add(booking)
#     db.commit()
#     db.refresh(booking)
    
#     return booking

# @router.get("/ambulance-bookings/{booking_id}", response_model=AmbulanceBookingResponse)
# async def get_ambulance_booking(
#     booking_id: UUID,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get a specific ambulance booking by ID.
#     """
#     booking = db.query(AmbulanceBooking).filter(
#         AmbulanceBooking.id == booking_id,
#         AmbulanceBooking.patient_id == current_user.id
#     ).first()
    
#     if not booking:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Ambulance booking not found"
#         )
    
#     return booking

# @router.put("/ambulance-bookings/{booking_id}", response_model=AmbulanceBookingResponse)
# async def update_ambulance_booking(
#     booking_id: UUID,
#     booking_update: AmbulanceBookingUpdate,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Update a specific ambulance booking.
#     """
#     booking = db.query(AmbulanceBooking).filter(
#         AmbulanceBooking.id == booking_id,
#         AmbulanceBooking.patient_id == current_user.id
#     ).first()
    
#     if not booking:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Ambulance booking not found"
#         )
    
#     # Check if booking can be modified
#     if booking.status in [AmbulanceStatus.COMPLETED, AmbulanceStatus.CANCELLED]:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cannot modify completed or cancelled ambulance bookings"
#         )
    
#     # Update booking fields
#     update_data = booking_update.dict(exclude_unset=True)
#     for field, value in update_data.items():
#         setattr(booking, field, value)
    
#     db.commit()
#     db.refresh(booking)
    
#     return booking

# @router.delete("/ambulance-bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def cancel_ambulance_booking(
#     booking_id: UUID,
#     current_user: User = Depends(get_current_patient_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Cancel a specific ambulance booking.
#     """
#     booking = db.query(AmbulanceBooking).filter(
#         AmbulanceBooking.id == booking_id,
#         AmbulanceBooking.patient_id == current_user.id
#     ).first()
    
#     if not booking:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Ambulance booking not found"
#         )
    
#     if booking.status == AmbulanceStatus.CANCELLED:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Ambulance booking is already cancelled"
#         )
    
#     booking.status = AmbulanceStatus.CANCELLED
#     booking.cancelled_at = db.execute(text("CURRENT_TIMESTAMP")).scalar()
    
#     db.commit()

# @router.get("/districts", response_model=List[District])
# async def get_districts(
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all available districts.
#     """
#     districts = db.query(District).filter(District.is_active == True).all()
#     return districts

# @router.get("/districts/{district_id}/areas", response_model=List[Area])
# async def get_district_areas(
#     district_id: UUID,
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all areas for a specific district.
#     """
#     areas = db.query(Area).filter(
#         Area.district_id == district_id,
#         Area.is_serviced == True
#     ).all()
#     return areas

# @router.get("/services", response_model=List[Service])
# async def get_services(
#     department_id: Optional[UUID] = None,
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all available services.
#     Optionally filter by department.
#     """
#     query = db.query(Service).filter(Service.is_active == True)
    
#     if department_id:
#         query = query.filter(Service.department_id == department_id)
    
#     services = query.all()
#     return services

# @router.get("/departments", response_model=List[Department])
# async def get_departments(
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all available departments.
#     """
#     departments = db.query(Department).filter(Department.is_active == True).all()
#     return departments