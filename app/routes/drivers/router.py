#app/routes/drivers/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.all_models import User, UserRole, AmbulanceBooking, AmbulanceStatus
   # your db session provider

router = APIRouter(prefix="/drivers", tags=["Drivers"])


# ============================
# Helper: Ensure user is driver
# ============================
def get_driver_or_404(driver_id: UUID, db: Session):
    driver = db.query(User).filter(
        User.id == driver_id,
        User.role == UserRole.AMBULANCE_DRIVER
    ).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with id {driver_id} not found",
        )
    return driver


# ============================
# Endpoints
# ============================

@router.get("/")
def list_drivers(db: Session = Depends(get_db)):
    """List all registered ambulance drivers"""
    drivers = db.query(User).filter(User.role == UserRole.AMBULANCE_DRIVER).all()
    return [
        {
            "id": d.id,
            "first_name": d.first_name,
            "last_name": d.last_name,
            "email": d.email,
            "phone": d.phone,
            "is_active": d.is_active,
            "last_login_at": d.last_login_at,
        }
        for d in drivers
    ]


@router.get("/{driver_id}")
def get_driver(driver_id: UUID, db: Session = Depends(get_db)):
    """Get details of a single driver"""
    driver = get_driver_or_404(driver_id, db)
    return {
        "id": driver.id,
        "first_name": driver.first_name,
        "last_name": driver.last_name,
        "email": driver.email,
        "phone": driver.phone,
        "is_active": driver.is_active,
    }


@router.get("/{driver_id}/bookings")
def get_driver_bookings(driver_id: UUID, db: Session = Depends(get_db)):
    """Get all ambulance bookings assigned to a driver"""
    driver = get_driver_or_404(driver_id, db)
    return [
        {
            "id": b.id,
            "patient_id": b.patient_id,
            "ambulance_id": b.ambulance_id,
            "status": b.status,
            "pickup_location": b.pickup_location,
            "destination": b.destination,
            "requested_datetime": b.requested_datetime,
        }
        for b in driver.ambulance_bookings_as_driver
    ]


@router.patch("/{driver_id}/bookings/{booking_id}/status")
def update_booking_status(
    driver_id: UUID,
    booking_id: UUID,
    status_update: dict,
    db: Session = Depends(get_db)
):
    """Update booking status (driver-only action)"""
    driver = get_driver_or_404(driver_id, db)

    booking = (
        db.query(AmbulanceBooking)
        .filter(AmbulanceBooking.id == booking_id, AmbulanceBooking.driver_id == driver.id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking {booking_id} not found for driver {driver_id}",
        )

    new_status = status_update.get("status")
    if new_status not in AmbulanceStatus.__members__:
        raise HTTPException(status_code=400, detail="Invalid status")

    booking.status = AmbulanceStatus[new_status]
    db.commit()
    db.refresh(booking)

    return {"id": booking.id, "status": booking.status}


@router.patch("/{driver_id}/status")
def update_driver_status(
    driver_id: UUID,
    payload: dict,
    db: Session = Depends(get_db)
):
    """Activate/deactivate a driver"""
    driver = get_driver_or_404(driver_id, db)
    is_active = payload.get("is_active")
    if is_active is None:
        raise HTTPException(status_code=400, detail="is_active field required")

    driver.is_active = is_active
    db.commit()
    db.refresh(driver)

    return {"id": driver.id, "is_active": driver.is_active}
