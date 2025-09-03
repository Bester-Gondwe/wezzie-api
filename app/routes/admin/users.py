from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.database import get_db
from app.models.all_models import User, UserRole
from app.schemas.admin import UserResponse

# Use a unique prefix to avoid conflicts
router = APIRouter(prefix="/admin/user-management", tags=["admin-users"])

@router.get("", response_model=List[UserResponse])
async def get_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    status: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db)
):
    """
    Get users with filtering and pagination (Admin only)
    """
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    if role:
        query = query.filter(User.role == role)
    
    if status is not None:
        query = query.filter(User.is_active == status)
    
    # Apply pagination
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    return users

@router.patch("/{user_id}/status", status_code=status.HTTP_200_OK)
async def update_user_status(
    user_id: str,
    is_active: bool,
    db: Session = Depends(get_db)
):
    """
    Update user active status (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    
    return {"message": "User status updated successfully"}