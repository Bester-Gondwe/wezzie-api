# app/routes/auth/schemas.py

from pydantic import BaseModel, EmailStr, field_validator, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
import re

from app.models.all_models import UserRole, Gender

# ================================
# REQUEST SCHEMAS
# ================================

class UserSignupRequest(BaseModel):
    # Basic information
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8)
    role: UserRole
    gender: Gender
    date_of_birth: Optional[date] = None
    preferred_language: Optional[str] = "en"
    accessibility_needs: Optional[Dict[str, Any]] = None
    verification_method: Optional[str] = Field("both")
    
    # Patient-specific fields
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district_id: Optional[UUID] = None
    area_id: Optional[UUID] = None
    national_id: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    
    # Staff-specific fields
    department_id: Optional[UUID] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    qualifications: Optional[str] = None
    years_of_experience: Optional[int] = None
    consultation_fee: Optional[float] = None

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @field_validator('phone')
    def validate_phone(cls, v):
        # Remove any spaces or dashes
        phone = re.sub(r'[\s\-]', '', v)
        # Check if it's a valid Malawi phone number format
        if not re.match(r'^(\+265)?[18]\d{8}$', phone):
            raise ValueError('Invalid phone number format. Must be a valid Malawi number.')
        return phone

    @field_validator('emergency_contact_phone', 'emergency_contact_relationship')
    def validate_patient_required_fields(cls, v, values):
        if values.get('role') == UserRole.PATIENT and not v:
            raise ValueError('Emergency contact information is required for patients')
        return v

    @field_validator('department_id')
    def validate_staff_required_fields(cls, v, values):
        role = values.get('role')
        if role in [UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST] and not v:
            raise ValueError('Department is required for medical staff')
        return v

class UserLoginRequest(BaseModel):
    email_or_phone: str
    password: str
    remember_me: Optional[bool] = False

class OTPVerificationRequest(BaseModel):
    email_or_phone: str
    otp: str = Field(...,min_length=6, max_length=6)
    verification_type: str = Field("both")

class ResendOTPRequest(BaseModel):
    email_or_phone: str
    method: str = Field(..., )

class PasswordResetRequest(BaseModel):
    email_or_phone: str
    method: str = Field(...)

class PasswordResetConfirm(BaseModel):
    email_or_phone: str
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# ================================
# RESPONSE SCHEMAS
# ================================

class PatientProfileResponse(BaseModel):
    patient_id: str
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    emergency_contact_relationship: Optional[str]
    address: Optional[str]
    city: Optional[str]
    blood_type: Optional[str]
    allergies: Optional[str]
    chronic_conditions: Optional[str]
    
    class Config:
        from_attributes = True

class StaffProfileResponse(BaseModel):
    employee_id: str
    department_id: Optional[UUID]
    specialization: Optional[str]
    license_number: Optional[str]
    qualifications: Optional[str]
    years_of_experience: Optional[int]
    consultation_fee: Optional[float]
    is_available_online: Optional[bool]
    
    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    role: UserRole
    gender: Gender
    date_of_birth: Optional[date]
    profile_image: Optional[str]
    preferred_language: str
    accessibility_needs: Optional[Dict[str, Any]]
    is_active: bool
    email_verified_at: Optional[datetime]
    phone_verified_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime
    patient_profile: Optional[PatientProfileResponse] = None
    staff_profile: Optional[StaffProfileResponse] = None
    
    class Config:
        from_attributes = True

    # @field_validator('patient_profile')
    # def set_patient_profile(cls, v, values):
    #     # Only include patient profile if user is a patient
    #     role = values.get('role')
    #     if role == UserRole.PATIENT:
    #         return v
    #     return None

    # @field_validator('staff_profile')
    # def set_staff_profile(cls, v, values):
    #     # Only include staff profile if user is staff
    #     role = values.get('role')
    #     if role in [UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.AMBULANCE_DRIVER]:
    #         return v
    #     return None

class UserLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # expires_in: int
    # user: UserProfileResponse
    requires_verification: bool = False
    message: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class VerificationResponse(BaseModel):
    message: str
    verified: bool = True

class OTPResponse(BaseModel):
    message: str
    sent: bool = True

# ================================
# UTILITY SCHEMAS
# ================================

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

class UserInDB(BaseModel):
    id: UUID
    email: str
    hashed_password: str
    is_active: bool
    role: UserRole
    
    class Config:
        from_attributes = True