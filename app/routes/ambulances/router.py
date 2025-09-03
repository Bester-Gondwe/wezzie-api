# app/routes/ambulances/router.py

from fastapi import APIRouter, Depends, HTTPException, status, Security, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import get_db
from app.models.all_models import Ambulance, User, UserRole, AmbulanceBooking
from app.utils.auth import require_admin, require_roles, get_current_user

# Create the router instance
router = APIRouter(prefix="/ambulances", tags=["Ambulances"])

# Import BLANTYRE_TZ from your models or define it here
from app.models.all_models import BLANTYRE_TZ

# Status mapping between frontend and backend
FRONTEND_TO_BACKEND_STATUS = {
    "Available": "is_operational",
    "In Transit": "en_route",
    "Occupied": "transporting",
    "In Repair": "maintenance",
    "Unavailable": "not_operational"
}

BACKEND_TO_FRONTEND_STATUS = {
    "is_operational": "Available",
    "en_route": "In Transit", 
    "transporting": "Occupied",
    "maintenance": "In Repair",
    "not_operational": "Unavailable"
}

@router.get("/")
def list_ambulances(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Security(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    """
    Get all ambulances with optional filtering and search (Admin/Receptionist only)
    """
    query = db.query(Ambulance)
    
    # Apply status filter if provided
    if status_filter:
        if status_filter in FRONTEND_TO_BACKEND_STATUS:
            backend_status = FRONTEND_TO_BACKEND_STATUS[status_filter]
            if backend_status == "is_operational":
                query = query.filter(Ambulance.is_operational == True)
            elif backend_status == "not_operational":
                query = query.filter(Ambulance.is_operational == False)
    
    # Apply search if provided
    if search:
        search_filter = or_(
            Ambulance.registration_number.ilike(f"%{search}%"),
            Ambulance.model.ilike(f"%{search}%"),
            Ambulance.current_location.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    ambulances = query.order_by(Ambulance.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to response format with frontend status
    response = []
    for ambulance in ambulances:
        # Determine frontend status based on operational status and bookings
        frontend_status = "Available"  # Default
        
        if not ambulance.is_operational:
            frontend_status = "Unavailable"
        else:
            # Check if ambulance has active bookings
            active_bookings = db.query(AmbulanceBooking).filter(
                AmbulanceBooking.ambulance_id == ambulance.id,
                AmbulanceBooking.status.in_([
                    "assigned", "en_route_pickup", "arrived_pickup", 
                    "transporting", "en_route_hospital"
                ])
            ).first()
            
            if active_bookings:
                if active_bookings.status in ["transporting", "arrived_pickup"]:
                    frontend_status = "Occupied"
                else:
                    frontend_status = "In Transit"
        
        # Create response object
        response_data = {
            "id": ambulance.id,
            "registration_number": ambulance.registration_number,
            "vehicle_type": ambulance.vehicle_type,
            "model": ambulance.model,
            "year": ambulance.year,
            "capacity": ambulance.capacity,
            "equipment": ambulance.equipment or [],
            "is_operational": ambulance.is_operational,
            "current_location": ambulance.current_location,
            "current_coordinates": ambulance.current_coordinates,
            "fuel_level": ambulance.fuel_level,
            "last_maintenance": ambulance.last_maintenance,
            "next_maintenance": ambulance.next_maintenance,
            "created_at": ambulance.created_at,
            "updated_at": ambulance.updated_at,
            "frontend_status": frontend_status
        }
        response.append(response_data)
    
    return response

@router.get("/{ambulance_id}")
def get_ambulance(
    ambulance_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Security(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    """
    Get a specific ambulance by ID (Admin/Receptionist only)
    """
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    
    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ambulance not found"
        )
    
    # Determine frontend status
    frontend_status = "Available"
    if not ambulance.is_operational:
        frontend_status = "Unavailable"
    else:
        active_bookings = db.query(AmbulanceBooking).filter(
            AmbulanceBooking.ambulance_id == ambulance.id,
            AmbulanceBooking.status.in_([
                "assigned", "en_route_pickup", "arrived_pickup", 
                "transporting", "en_route_hospital"
            ])
        ).first()
        
        if active_bookings:
            if active_bookings.status in ["transporting", "arrived_pickup"]:
                frontend_status = "Occupied"
            else:
                frontend_status = "In Transit"
    
    response_data = {
        "id": ambulance.id,
        "registration_number": ambulance.registration_number,
        "vehicle_type": ambulance.vehicle_type,
        "model": ambulance.model,
        "year": ambulance.year,
        "capacity": ambulance.capacity,
        "equipment": ambulance.equipment or [],
        "is_operational": ambulance.is_operational,
        "current_location": ambulance.current_location,
        "current_coordinates": ambulance.current_coordinates,
        "fuel_level": ambulance.fuel_level,
        "last_maintenance": ambulance.last_maintenance,
        "next_maintenance": ambulance.next_maintenance,
        "created_at": ambulance.created_at,
        "updated_at": ambulance.updated_at,
        "frontend_status": frontend_status
    }
    
    return response_data

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_ambulance(
    ambulance_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Security(require_admin)
):
    """
    Create a new ambulance (Admin only)
    """
    # Check if registration number already exists
    existing_ambulance = db.query(Ambulance).filter(
        Ambulance.registration_number == ambulance_data.get("registration_number")
    ).first()
    
    if existing_ambulance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ambulance with this registration number already exists"
        )
    
    # Convert frontend status to backend operational status
    frontend_status = ambulance_data.get("frontend_status", "Available")
    is_operational = frontend_status in ["Available", "In Transit", "Occupied"]
    
    ambulance = Ambulance(
        registration_number=ambulance_data.get("registration_number"),
        vehicle_type=ambulance_data.get("vehicle_type"),
        model=ambulance_data.get("model"),
        year=ambulance_data.get("year"),
        capacity=ambulance_data.get("capacity"),
        equipment=ambulance_data.get("equipment", []),
        is_operational=is_operational,
        current_location=ambulance_data.get("current_location"),
        current_coordinates=ambulance_data.get("current_coordinates"),
        fuel_level=ambulance_data.get("fuel_level", "full"),
        last_maintenance=ambulance_data.get("last_maintenance"),
        next_maintenance=ambulance_data.get("next_maintenance")
    )
    
    db.add(ambulance)
    db.commit()
    db.refresh(ambulance)
    
    response_data = {
        "id": ambulance.id,
        "registration_number": ambulance.registration_number,
        "vehicle_type": ambulance.vehicle_type,
        "model": ambulance.model,
        "year": ambulance.year,
        "capacity": ambulance.capacity,
        "equipment": ambulance.equipment or [],
        "is_operational": ambulance.is_operational,
        "current_location": ambulance.current_location,
        "current_coordinates": ambulance.current_coordinates,
        "fuel_level": ambulance.fuel_level,
        "last_maintenance": ambulance.last_maintenance,
        "next_maintenance": ambulance.next_maintenance,
        "created_at": ambulance.created_at,
        "updated_at": ambulance.updated_at,
        "frontend_status": frontend_status
    }
    
    return response_data

@router.put("/{ambulance_id}")
def update_ambulance(
    ambulance_id: UUID,
    ambulance_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Security(require_admin)
):
    """
    Update an ambulance (Admin only)
    """
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    
    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ambulance not found"
        )
    
    # Check if registration number is being changed to one that already exists
    new_registration = ambulance_data.get("registration_number")
    if new_registration and new_registration != ambulance.registration_number:
        existing_ambulance = db.query(Ambulance).filter(
            Ambulance.registration_number == new_registration
        ).first()
        
        if existing_ambulance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ambulance with this registration number already exists"
            )
    
    # Handle frontend status conversion
    if 'frontend_status' in ambulance_data:
        frontend_status = ambulance_data['frontend_status']
        is_operational = frontend_status in ["Available", "In Transit", "Occupied"]
        ambulance_data['is_operational'] = is_operational
        del ambulance_data['frontend_status']
    
    # Update fields
    for field, value in ambulance_data.items():
        if value is not None and hasattr(ambulance, field):
            setattr(ambulance, field, value)
    
    db.commit()
    db.refresh(ambulance)
    
    # Determine frontend status for response
    frontend_status = "Available"
    if not ambulance.is_operational:
        frontend_status = "Unavailable"
    else:
        active_bookings = db.query(AmbulanceBooking).filter(
            AmbulanceBooking.ambulance_id == ambulance.id,
            AmbulanceBooking.status.in_([
                "assigned", "en_route_pickup", "arrived_pickup", 
                "transporting", "en_route_hospital"
            ])
        ).first()
        
        if active_bookings:
            if active_bookings.status in ["transporting", "arrived_pickup"]:
                frontend_status = "Occupied"
            else:
                frontend_status = "In Transit"
    
    response_data = {
        "id": ambulance.id,
        "registration_number": ambulance.registration_number,
        "vehicle_type": ambulance.vehicle_type,
        "model": ambulance.model,
        "year": ambulance.year,
        "capacity": ambulance.capacity,
        "equipment": ambulance.equipment or [],
        "is_operational": ambulance.is_operational,
        "current_location": ambulance.current_location,
        "current_coordinates": ambulance.current_coordinates,
        "fuel_level": ambulance.fuel_level,
        "last_maintenance": ambulance.last_maintenance,
        "next_maintenance": ambulance.next_maintenance,
        "created_at": ambulance.created_at,
        "updated_at": ambulance.updated_at,
        "frontend_status": frontend_status
    }
    
    return response_data

@router.patch("/{ambulance_id}/status")
def update_ambulance_status(
    ambulance_id: UUID,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Security(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    """
    Update ambulance status (Admin/Receptionist only)
    """
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    
    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ambulance not found"
        )
    
    status_value = status_data.get("status")
    if not status_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status field is required"
        )
    
    # Convert frontend status to backend operational status
    is_operational = status_value in ["Available", "In Transit", "Occupied"]
    
    ambulance.is_operational = is_operational
    
    # If marking as "In Repair" or "Unavailable", cancel any active bookings
    if status_value in ["In Repair", "Unavailable"]:
        active_bookings = db.query(AmbulanceBooking).filter(
            AmbulanceBooking.ambulance_id == ambulance.id,
            AmbulanceBooking.status.in_([
                "assigned", "en_route_pickup", "arrived_pickup", 
                "transporting", "en_route_hospital"
            ])
        ).all()
        
        for booking in active_bookings:
            booking.status = "cancelled"
            booking.cancelled_at = datetime.now(BLANTYRE_TZ)
    
    db.commit()
    db.refresh(ambulance)
    
    response_data = {
        "id": ambulance.id,
        "registration_number": ambulance.registration_number,
        "vehicle_type": ambulance.vehicle_type,
        "model": ambulance.model,
        "year": ambulance.year,
        "capacity": ambulance.capacity,
        "equipment": ambulance.equipment or [],
        "is_operational": ambulance.is_operational,
        "current_location": ambulance.current_location,
        "current_coordinates": ambulance.current_coordinates,
        "fuel_level": ambulance.fuel_level,
        "last_maintenance": ambulance.last_maintenance,
        "next_maintenance": ambulance.next_maintenance,
        "created_at": ambulance.created_at,
        "updated_at": ambulance.updated_at,
        "frontend_status": status_value
    }
    
    return response_data

@router.delete("/{ambulance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ambulance(
    ambulance_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Security(require_admin)
):
    """
    Delete an ambulance (Admin only)
    """
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    
    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ambulance not found"
        )
    
    # Check if ambulance has active bookings
    active_bookings = db.query(AmbulanceBooking).filter(
        AmbulanceBooking.ambulance_id == ambulance.id,
        AmbulanceBooking.status.in_([
            "assigned", "en_route_pickup", "arrived_pickup", 
            "transporting", "en_route_hospital"
        ])
    ).first()
    
    if active_bookings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete ambulance with active bookings"
        )
    
    db.delete(ambulance)
    db.commit()
    
    return None

@router.get("/{ambulance_id}/bookings")
def get_ambulance_bookings(
    ambulance_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Security(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    """
    Get all bookings for a specific ambulance (Admin/Receptionist only)
    """
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    
    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ambulance not found"
        )
    
    bookings = db.query(AmbulanceBooking).filter(
        AmbulanceBooking.ambulance_id == ambulance_id
    ).order_by(AmbulanceBooking.requested_datetime.desc()).all()
    
    return [
        {
            "id": booking.id,
            "patient_id": booking.patient_id,
            "driver_id": booking.driver_id,
            "status": booking.status.value,
            "pickup_location": booking.pickup_location,
            "destination": booking.destination,
            "requested_datetime": booking.requested_datetime,
            "priority": booking.priority.value,
            "case_severity": booking.case_severity.value
        }
        for booking in bookings
    ]