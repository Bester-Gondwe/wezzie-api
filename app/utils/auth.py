# app/utils/auth_utils.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
import bcrypt
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
import pytz

# Local imports
from app.database import get_db
from app.config import settings

# Timezone setup
BLANTYRE_TZ = pytz.timezone('Africa/Blantyre')

def blantyre_now():
    return datetime.now(BLANTYRE_TZ)

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def generate_otp(length: int = 6) -> str:
    """Generate a random OTP of specified length."""
    characters = string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_access_token(data: Dict[str, str], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = blantyre_now() + expires_delta
    else:
        expire = blantyre_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, str], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = blantyre_now() + expires_delta
    else:
        expire = blantyre_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict:
    """Verify a JWT token and return its payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type, expected {token_type}"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def send_email_otp(email: str, otp: str, recipient_name: str, purpose: str = "verification") -> None:
    """Send an OTP via email."""
    smtp_server = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_password = settings.SMTP_PASSWORD
    sender_email = settings.SENDER_EMAIL

    subject = "Your OTP for Account Verification" if purpose == "verification" else "Your OTP for Password Reset"
    body = f"""
    Dear {recipient_name},

    Your one-time password (OTP) is: {otp}
    This OTP is valid for the next 10 minutes. Please use it to complete your {purpose.replace('_', ' ')}.

    If you did not request this, please ignore this email or contact support.

    Best regards,
    Your Application Team
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email OTP: {str(e)}"
        )

async def send_sms_otp(phone: str, otp: str, purpose: str = "verification") -> None:
    """Send an OTP via SMS (placeholder for actual SMS service integration)."""
    # Note: This is a placeholder. In production, integrate with an SMS service provider (e.g., Twilio, Nexmo).
    # For now, we'll simulate the SMS sending logic and log the OTP for debugging.
    try:
        # Simulated SMS sending logic
        print(f"Sending SMS to {phone}: OTP {otp} for {purpose}")
        # Example with Twilio (uncomment and configure for actual use):
        """
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your OTP is {otp}. Valid for 10 minutes.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone
        )
        """
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send SMS OTP: {str(e)}"
        )

# Import User model here to avoid circular imports
from app.models.all_models import User, UserRole

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Retrieve the current authenticated user from the JWT token."""
    token = credentials.credentials
    payload = verify_token(token, token_type="access")
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require admin role for accessing protected routes.
    
    Usage:
    @router.get("/admin-only")
    async def admin_only_route(user: User = Depends(require_admin)):
        # Only users with admin role can access this route
        return {"message": "Welcome admin!"}
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required."
        )
    
    return current_user

async def require_staff(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require staff role (doctor, nurse, receptionist, admin) for accessing protected routes.
    
    Usage:
    @router.get("/staff-only")
    async def staff_only_route(user: User = Depends(require_staff)):
        # Only staff members can access this route
        return {"message": "Welcome staff member!"}
    """
    staff_roles = [UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST]
    
    if current_user.role not in staff_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Staff role required."
        )
    
    return current_user

async def require_roles(
    allowed_roles: list[UserRole],
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require specific roles for accessing protected routes.
    
    Usage:
    @router.get("/doctors-only")
    async def doctors_only_route(user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN]))):
        # Only doctors and admins can access this route
        return {"message": "Welcome doctor or admin!"}
    """
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required roles: " + ", ".join([role.value for role in allowed_roles])
        )
    
    return current_user