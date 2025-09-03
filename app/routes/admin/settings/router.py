from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.models.all_models import SystemSetting, UserRole, ActivityLog, Language
from app.database import get_db
from app.utils.auth import require_admin, get_current_user
from app.schemas.user import User
import pytz

router = APIRouter(prefix="/api/settings", tags=["Settings"])

# Pydantic schemas
class RolePermission(BaseModel):
    role: str = Field(..., regex="^(admin|doctor|nurse|receptionist|ambulance_driver|patient)$")
    canManageUsers: bool
    canManageAmbulances: bool
    canManageSchedules: bool

class SystemSettings(BaseModel):
    timeZone: str = Field(..., min_length=1, max_length=100)
    language: str = Field(..., min_length=1, max_length=50)
    emailNotifications: bool
    smsNotifications: bool

class SystemSettingsResponse(BaseModel):
    timeZone: str
    language: str
    emailNotifications: bool
    smsNotifications: bool

class LanguageResponse(BaseModel):
    code: str
    name: str
    native_name: str
    is_active: bool
    is_default: bool

    class Config:
        orm_mode = True

# Helper function to get or create settings
async def get_or_create_setting(db: Session, category: str, key_name: str, default_value: str, data_type: str = "string"):
    setting = db.query(SystemSetting).filter(SystemSetting.category == category, SystemSetting.key_name == key_name).first()
    if not setting:
        setting = SystemSetting(
            category=category,
            key_name=key_name,
            value=default_value,
            data_type=data_type,
            created_at=datetime.now(pytz.timezone('Africa/Blantyre')),
            updated_at=datetime.now(pytz.timezone('Africa/Blantyre'))
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting

# Endpoints
@router.get("/system", response_model=SystemSettingsResponse)
async def get_system_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    await require_admin(current_user)
    
    settings = {
        "timeZone": (await get_or_create_setting(db, "general", "time_zone", "Africa/Blantyre")).value,
        "language": (await get_or_create_setting(db, "general", "language", "English")).value,
        "emailNotifications": (await get_or_create_setting(db, "notifications", "email_enabled", "true", "boolean")).value == "true",
        "smsNotifications": (await get_or_create_setting(db, "notifications", "sms_enabled", "false", "boolean")).value == "true"
    }
    return settings

@router.put("/system", response_model=SystemSettingsResponse)
async def update_system_settings(
    settings: SystemSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await require_admin(current_user)
    
    # Validate time zone
    try:
        pytz.timezone(settings.timeZone)
    except pytz.exceptions.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid time zone")
    
    # Validate language exists
    language = db.query(Language).filter(Language.name == settings.language, Language.is_active == True).first()
    if not language:
        raise HTTPException(status_code=400, detail="Invalid or inactive language")
    
    # Update settings
    time_zone_setting = await get_or_create_setting(db, "general", "time_zone", "Africa/Blantyre")
    time_zone_setting.value = settings.timeZone
    time_zone_setting.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
    
    language_setting = await get_or_create_setting(db, "general", "language", "English")
    language_setting.value = settings.language
    language_setting.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
    
    email_setting = await get_or_create_setting(db, "notifications", "email_enabled", "true", "boolean")
    email_setting.value = str(settings.emailNotifications).lower()
    email_setting.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
    
    sms_setting = await get_or_create_setting(db, "notifications", "sms_enabled", "false", "boolean")
    sms_setting.value = str(settings.smsNotifications).lower()
    sms_setting.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
    
    db.commit()
    
    # Log activity
    db_log = ActivityLog(
        user_id=current_user.id,
        action="UPDATE_SYSTEM_SETTINGS",
        model_type="SystemSetting",
        model_id=None,
        details=settings.dict(),
        created_at=datetime.now(pytz.timezone('Africa/Blantyre'))
    )
    db.add(db_log)
    db.commit()
    
    return settings

@router.get("/permissions", response_model=List[RolePermission])
async def get_role_permissions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    await require_admin(current_user)
    
    setting = db.query(SystemSetting).filter(
        SystemSetting.category == "permissions",
        SystemSetting.key_name == "role_permissions"
    ).first()
    
    if not setting:
        # Default permissions based on UserRole enum
        default_permissions = [
            {"role": role.value, "canManageUsers": role == UserRole.ADMIN, "canManageAmbulances": role in [UserRole.ADMIN, UserRole.AMBULANCE_DRIVER], "canManageSchedules": role in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE]}
            for role in UserRole
        ]
        setting = SystemSetting(
            category="permissions",
            key_name="role_permissions",
            value=str(default_permissions).replace("'", '"'),  # Store as JSON string
            data_type="json",
            created_at=datetime.now(pytz.timezone('Africa/Blantyre')),
            updated_at=datetime.now(pytz.timezone('Africa/Blantyre'))
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    
    import json
    return json.loads(setting.value)

@router.put("/permissions", response_model=List[RolePermission])
async def update_role_permissions(
    permissions: List[RolePermission],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await require_admin(current_user)
    
    # Validate roles
    valid_roles = {role.value for role in UserRole}
    for perm in permissions:
        if perm.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {perm.role}")
    
    # Ensure all roles are covered
    if len(permissions) != len(valid_roles):
        raise HTTPException(status_code=400, detail="All roles must be specified")
    
    setting = db.query(SystemSetting).filter(
        SystemSetting.category == "permissions",
        SystemSetting.key_name == "role_permissions"
    ).first()
    
    if not setting:
        setting = SystemSetting(
            category="permissions",
            key_name="role_permissions",
            data_type="json",
            created_at=datetime.now(pytz.timezone('Africa/Blantyre'))
        )
        db.add(setting)
    
    import json
    setting.value = json.dumps([perm.dict() for perm in permissions])
    setting.updated_at = datetime.now(pytz.timezone('Africa/Blantyre'))
    db.commit()
    
    # Log activity
    db_log = ActivityLog(
        user_id=current_user.id,
        action="UPDATE_ROLE_PERMISSIONS",
        model_type="SystemSetting",
        model_id=setting.id,
        details={"permissions": [perm.dict() for perm in permissions]},
        created_at=datetime.now(pytz.timezone('Africa/Blantyre'))
    )
    db.add(db_log)
    db.commit()
    
    return permissions

@router.get("/languages", response_model=List[LanguageResponse])
async def get_languages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    await require_admin(current_user)
    languages = db.query(Language).all()
    return languages