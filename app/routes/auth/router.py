# app/routes/auth/router.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import secrets
import bcrypt
import jwt
from email_validator import validate_email, EmailNotValidError

from app.database import get_db
from app.models.all_models import User, PatientProfile, StaffProfile, UserRole, Gender
from app.config import settings
from app.routes.auth.schemas import (
    UserSignupRequest,
    UserLoginRequest,
    UserLoginResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    OTPVerificationRequest,
    ResendOTPRequest,
    ChangePasswordRequest,
    RefreshTokenRequest,
    UserProfileResponse
)
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password,
    generate_otp,
    send_email_otp,
    send_sms_otp,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# ================================
# SIGNUP ENDPOINTS
# ================================

@router.post("/signup", response_model=UserLoginResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserSignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    Supports both patient and staff registration.
    """
    try:
        # Validate email format
        valid = validate_email(user_data.email)
        email = valid.email
    except EmailNotValidError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email format"
        )

    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == email) | (User.phone == user_data.phone)
    ).first()
    
    if existing_user:
        if existing_user.email == email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already registered"
            )

    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Generate OTP for verification
    otp = generate_otp()
    
    # Create user
    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=email,
        phone=user_data.phone,
        password=hashed_password,
        otp=otp,
        role=user_data.role,
        gender=user_data.gender,
        date_of_birth=user_data.date_of_birth,
        preferred_language=user_data.preferred_language or "en",
        accessibility_needs=user_data.accessibility_needs
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create role-specific profile
    if user_data.role == UserRole.PATIENT:
        # Generate unique patient ID
        patient_id = f"PT{new_user.id.hex[:8].upper()}"
        
        patient_profile = PatientProfile(
            user_id=new_user.id,
            patient_id=patient_id,
            emergency_contact_name=user_data.emergency_contact_name,
            emergency_contact_phone=user_data.emergency_contact_phone,
            emergency_contact_relationship=user_data.emergency_contact_relationship,
            address=user_data.address,
            city=user_data.city,
            district_id=user_data.district_id,
            area_id=user_data.area_id,
            national_id=user_data.national_id,
            blood_type=user_data.blood_type,
            allergies=user_data.allergies,
            chronic_conditions=user_data.chronic_conditions,
            current_medications=user_data.current_medications
        )
        db.add(patient_profile)
    
    elif user_data.role in [UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.AMBULANCE_DRIVER]:
        # Generate unique employee ID
        role_prefix = {
            UserRole.DOCTOR: "DR",
            UserRole.NURSE: "NR",
            UserRole.ADMIN: "AD",
            UserRole.RECEPTIONIST: "RC",
            UserRole.AMBULANCE_DRIVER: "AM"
        }
        employee_id = f"{role_prefix[user_data.role]}{new_user.id.hex[:8].upper()}"
        
        staff_profile = StaffProfile(
            user_id=new_user.id,
            employee_id=employee_id,
            department_id=user_data.department_id,
            specialization=user_data.specialization,
            license_number=user_data.license_number,
            qualifications=user_data.qualifications,
            years_of_experience=user_data.years_of_experience or 0,
            consultation_fee=user_data.consultation_fee
        )
        db.add(staff_profile)
    
    db.commit()

    # Send verification OTP
    if user_data.verification_method == "email":
        background_tasks.add_task(send_email_otp, email, otp, new_user.first_name)
    elif user_data.verification_method == "sms":
        background_tasks.add_task(send_sms_otp, user_data.phone, otp)
    else:
        # Send both by default
        background_tasks.add_task(send_email_otp, email, otp, new_user.first_name)
        background_tasks.add_task(send_sms_otp, user_data.phone, otp)

    # Generate tokens
    access_token = create_access_token({"sub": str(new_user.id), "role": new_user.role.value})
    refresh_token = create_refresh_token({"sub": str(new_user.id)})

    return UserLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfileResponse.from_orm(new_user),
        requires_verification=True,
        message="Account created successfully. Please verify your account using the OTP sent to your email/phone."
    )

# ================================
# LOGIN ENDPOINTS
# ================================

@router.post("/login", response_model=UserLoginResponse)
async def login(
    login_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access tokens.
    """
    # Find user by email or phone
    user = db.query(User).filter(
        (User.email == login_data.email_or_phone) | 
        (User.phone == login_data.email_or_phone)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Verify password
    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support."
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Generate tokens
    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email
    })
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Check if verification is required
    requires_verification = (
        user.email_verified_at is None or 
        user.phone_verified_at is None
    )

    return UserLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        # expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        # user=UserProfileResponse.from_orm(user),
        requires_verification=requires_verification,
        message="Login successful"
    )

# ================================
# OTP VERIFICATION ENDPOINTS
# ================================

@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(
    verification_data: OTPVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP for email or phone verification.
    """
    user = db.query(User).filter(
        (User.email == verification_data.email_or_phone) |
        (User.phone == verification_data.email_or_phone)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.otp or user.otp != verification_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    # Verify based on verification type
    now = datetime.utcnow()
    
    if verification_data.verification_type == "email":
        user.email_verified_at = now
    elif verification_data.verification_type == "phone":
        user.phone_verified_at = now
    else:
        # Verify both
        user.email_verified_at = now
        user.phone_verified_at = now

    # Clear OTP
    user.otp = None
    db.commit()

    return {
        "message": f"{verification_data.verification_type.title()} verified successfully",
        "verified": True
    }

@router.post("/resend-otp", status_code=status.HTTP_200_OK)
async def resend_otp(
    resend_data: ResendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Resend OTP for verification.
    """
    user = db.query(User).filter(
        (User.email == resend_data.email_or_phone) |
        (User.phone == resend_data.email_or_phone)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Generate new OTP
    otp = generate_otp()
    user.otp = otp
    db.commit()

    # Send OTP
    if resend_data.method == "email":
        background_tasks.add_task(send_email_otp, user.email, otp, user.first_name)
    elif resend_data.method == "sms":
        background_tasks.add_task(send_sms_otp, user.phone, otp)

    return {
        "message": f"OTP sent successfully via {resend_data.method}",
        "sent": True
    }

# ================================
# PASSWORD MANAGEMENT
# ================================

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset process.
    """
    user = db.query(User).filter(
        (User.email == reset_data.email_or_phone) |
        (User.phone == reset_data.email_or_phone)
    ).first()

    if not user:
        # Don't reveal if user exists for security
        return {
            "message": "If the account exists, password reset instructions have been sent",
            "sent": True
        }

    # Generate OTP for password reset
    otp = generate_otp()
    user.otp = otp
    db.commit()

    # Send reset OTP
    if reset_data.method == "email":
        background_tasks.add_task(send_email_otp, user.email, otp, user.first_name, "password_reset")
    elif reset_data.method == "sms":
        background_tasks.add_task(send_sms_otp, user.phone, otp, "password_reset")

    return {
        "message": "Password reset instructions sent successfully",
        "sent": True
    }

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset password using OTP.
    """
    user = db.query(User).filter(
        (User.email == reset_data.email_or_phone) |
        (User.phone == reset_data.email_or_phone)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.otp or user.otp != reset_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    # Update password
    user.password = hash_password(reset_data.new_password)
    user.otp = None
    db.commit()

    return {
        "message": "Password reset successful",
        "reset": True
    }

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.password = hash_password(password_data.new_password)
    db.commit()

    return {
        "message": "Password changed successfully",
        "changed": True
    }

# ================================
# TOKEN MANAGEMENT
# ================================

@router.post("/refresh-token", response_model=dict)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = verify_token(token_data.refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Generate new access token
        new_access_token = create_access_token({
            "sub": str(user.id),
            "role": user.role.value,
            "email": user.email
        })

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user (client should discard tokens).
    """
    return {
        "message": "Logged out successfully",
        "logged_out": True
    }

# ================================
# PROFILE ENDPOINTS
# ================================

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile information.
    """
    return UserProfileResponse.from_orm(current_user)

@router.get("/verify-token", response_model=dict)
async def verify_token_endpoint(
    current_user: User = Depends(get_current_user)
):
    """
    Verify if the current token is valid.
    """
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "verified": {
            "email": current_user.email_verified_at is not None,
            "phone": current_user.phone_verified_at is not None
        }
    }

# ================================
# ACCOUNT MANAGEMENT
# ================================

@router.post("/deactivate-account", status_code=status.HTTP_200_OK)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate user account.
    """
    current_user.is_active = False
    db.commit()

    return {
        "message": "Account deactivated successfully",
        "deactivated": True
    }

@router.post("/reactivate-account", status_code=status.HTTP_200_OK)
async def reactivate_account(
    reactivation_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Reactivate deactivated account.
    """
    user = db.query(User).filter(
        (User.email == reactivation_data.email_or_phone) |
        (User.phone == reactivation_data.email_or_phone)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not verify_password(reactivation_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    user.is_active = True
    db.commit()

    return {
        "message": "Account reactivated successfully",
        "reactivated": True
    }