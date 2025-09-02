# app/routes/auth/utils.py

from datetime import datetime, timedelta
import re
from typing import Optional, Dict, Any
import secrets
import string
import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import random

from app.config import settings
from app.database import get_db
from app.models.all_models import User

# Initialize security
security = HTTPBearer()

# ================================
# PASSWORD HASHING
# ================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# ================================
# JWT TOKEN MANAGEMENT
# ================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}"
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

# ================================
# USER AUTHENTICATION
# ================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify the token
        payload = verify_token(credentials.credentials, "access")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except HTTPException:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user

async def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user only if email and phone are verified."""
    
    if not current_user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    if not current_user.phone_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone verification required"
        )
    
    return current_user

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

# ================================
# OTP GENERATION AND VALIDATION
# ================================

def generate_otp(length: int = 6) -> str:
    """Generate a random OTP."""
    digits = string.digits
    otp = ''.join(random.choice(digits) for _ in range(length))
    return otp

def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)

# ================================
# EMAIL SERVICES
# ================================

def send_email_otp(email: str, otp: str, first_name: str, template_type: str = "verification"):
    """Send OTP via email."""
    try:
        # Email configuration
        smtp_server = settings.SMTP_SERVER
        smtp_port = settings.SMTP_PORT
        sender_email = settings.SMTP_USERNAME
        sender_password = settings.SMTP_PASSWORD
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = get_email_subject(template_type)
        message["From"] = f"Malawi Health System <{sender_email}>"
        message["To"] = email
        
        # Email templates
        html_body = get_email_template(template_type, first_name, otp)
        text_body = get_email_text_template(template_type, first_name, otp)
        
        # Convert to MIMEText objects
        text_part = MIMEText(text_body, "plain")
        html_part = MIMEText(html_body, "html")
        
        # Add parts to message
        message.attach(text_part)
        message.attach(html_part)
        
        # Create secure connection and send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
        
        return True
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def get_email_subject(template_type: str) -> str:
    """Get email subject based on template type."""
    subjects = {
        "verification": "Verify Your Account - Malawi Health System",
        "password_reset": "Reset Your Password - Malawi Health System",
        "login_alert": "New Login Alert - Malawi Health System"
    }
    return subjects.get(template_type, "Malawi Health System - Verification Code")

def get_email_template(template_type: str, first_name: str, otp: str) -> str:
    """Get HTML email template."""
    
    base_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Malawi Health System</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2c5aa0; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 30px; }}
            .otp-box {{ background-color: #e8f4fd; border: 2px solid #2c5aa0; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
            .otp-code {{ font-size: 32px; font-weight: bold; color: #2c5aa0; letter-spacing: 5px; }}
            .footer {{ background-color: #333; color: white; padding: 20px; text-align: center; font-size: 12px; }}
            .btn {{ display: inline-block; padding: 12px 24px; background-color: #2c5aa0; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏥 Malawi Health System</h1>
                <p>Your Health, Our Priority</p>
            </div>
            <div class="content">
                <h2>Hello {first_name}!</h2>
                {get_template_content(template_type, otp)}
            </div>
            <div class="footer">
                <p>&copy; 2025 Malawi Health System. All rights reserved.</p>
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>If you need assistance, contact us at support@malawihealthsystem.mw</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return base_template

def get_template_content(template_type: str, otp: str) -> str:
    """Get specific content for email templates."""
    templates = {
        "verification": f"""
            <p>Welcome to Malawi Health System! To complete your account verification, please use the following OTP:</p>
            <div class="otp-box">
                <p>Your verification code is:</p>
                <div class="otp-code">{otp}</div>
            </div>
            <p>This code will expire in 10 minutes. If you didn't create an account, please ignore this email.</p>
            <p><strong>Important:</strong> Do not share this code with anyone for security reasons.</p>
        """,
        "password_reset": f"""
            <p>You requested to reset your password for your Malawi Health System account.</p>
            <div class="otp-box">
                <p>Your password reset code is:</p>
                <div class="otp-code">{otp}</div>
            </div>
            <p>This code will expire in 10 minutes. If you didn't request a password reset, please ignore this email.</p>
            <p><strong>Security tip:</strong> Never share your OTP with anyone.</p>
        """
    }
    return templates.get(template_type, f"Your verification code is: {otp}")

def get_email_text_template(template_type: str, first_name: str, otp: str) -> str:
    """Get plain text email template."""
    templates = {
        "verification": f"""
Hello {first_name}!

Welcome to Malawi Health System!

To complete your account verification, please use the following OTP:

Verification Code: {otp}

This code will expire in 10 minutes.

If you didn't create an account, please ignore this email.

Best regards,
Malawi Health System Team
        """,
        "password_reset": f"""
Hello {first_name}!

You requested to reset your password for your Malawi Health System account.

Password Reset Code: {otp}

This code will expire in 10 minutes.

If you didn't request a password reset, please ignore this email.

Best regards,
Malawi Health System Team
        """
    }
    return templates.get(template_type, f"Your verification code is: {otp}")

# ================================
# SMS SERVICES
# ================================

def send_sms_otp(phone: str, otp: str, template_type: str = "verification"):
    """Send OTP via SMS using a SMS gateway service."""
    try:
        # SMS API configuration (replace with your SMS provider)
        sms_api_url = settings.SMS_API_URL
        sms_api_key = settings.SMS_API_KEY
        
        # Format phone number for Malawi
        formatted_phone = format_malawi_phone(phone)
        
        # SMS message templates
        messages = {
            "verification": f"Your Malawi Health System verification code is: {otp}. Valid for 10 minutes. Do not share this code.",
            "password_reset": f"Your Malawi Health System password reset code is: {otp}. Valid for 10 minutes. Do not share this code."
        }
        
        message = messages.get(template_type, f"Your verification code is: {otp}")
        
        # SMS API payload (adjust based on your SMS provider)
        payload = {
            "api_key": sms_api_key,
            "to": formatted_phone,
            "message": message,
            "from": "MalawiHealth"
        }
        
        # Send SMS request
        response = requests.post(sms_api_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            print(f"SMS sending failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False

def format_malawi_phone(phone: str) -> str:
    """Format phone number for Malawi (+265)."""
    # Remove any non-digit characters except +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Add +265 if not present
    if not phone.startswith('+265'):
        if phone.startswith('265'):
            phone = '+' + phone
        elif phone.startswith('0'):
            phone = '+265' + phone[1:]
        else:
            phone = '+265' + phone
    
    return phone

# ================================
# VALIDATION UTILITIES
# ================================

def validate_malawi_phone(phone: str) -> bool:
    """Validate Malawi phone number format."""
    # Remove spaces and dashes
    phone = re.sub(r'[\s\-]', '', phone)
    
    # Check format: +265[18]XXXXXXXX or 0[18]XXXXXXXX or [18]XXXXXXXX
    patterns = [
        r'^\+265[18]\d{8}',  # +265 followed by 1 or 8 and 8 digits
        r'^0[18]\d{8}',      # 0 followed by 1 or 8 and 8 digits
        r'^[18]\d{8}'        # 1 or 8 followed by 8 digits
    ]
    
    return any(re.match(pattern, phone) for pattern in patterns)

def validate_password_strength(password: str) -> Dict[str, bool]:
    """Validate password strength and return detailed results."""
    checks = {
        "length": len(password) >= 8,
        "uppercase": bool(re.search(r'[A-Z]', password)),
        "lowercase": bool(re.search(r'[a-z]', password)),
        "digit": bool(re.search(r'\d', password)),
        "special": bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    }
    
    return {
        **checks,
        "is_strong": all(checks.values()),
        "score": sum(checks.values())
    }

# ================================
# RATE LIMITING UTILITIES
# ================================

def check_rate_limit(identifier: str, limit: int, window: int) -> bool:
    """Check if rate limit is exceeded for an identifier."""
    # This is a simple in-memory rate limiter
    # In production, use Redis or similar for distributed rate limiting
    import time
    from collections import defaultdict, deque
    
    if not hasattr(check_rate_limit, 'requests'):
        check_rate_limit.requests = defaultdict(deque)
    
    now = time.time()
    requests = check_rate_limit.requests[identifier]
    
    # Remove old requests outside the window
    while requests and requests[0] < now - window:
        requests.popleft()
    
    # Check if limit exceeded
    if len(requests) >= limit:
        return False
    
    # Add current request
    requests.append(now)
    return True

# ================================
# SESSION MANAGEMENT
# ================================

def create_session_token() -> str:
    """Create a secure session token."""
    return secrets.token_urlsafe(32)

def invalidate_session(session_token: str):
    """Invalidate a session token (implement with Redis/database)."""
    # Implementation depends on your session storage
    pass

# ================================
# AUDIT LOGGING
# ================================

def log_auth_event(user_id: str, event: str, details: Dict[str, Any], db: Session):
    """Log authentication events for audit purposes."""
    from app.models.all_models import ActivityLog
    
    try:
        log_entry = ActivityLog(
            user_id=user_id,
            action=event,
            model_type="authentication",
            details=details,
            ip_address=details.get('ip_address'),
            user_agent=details.get('user_agent')
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"Failed to log auth event: {e}")
        db.rollback()

# ================================
# ERROR HANDLING
# ================================

class AuthenticationError(Exception):
    """Custom authentication error."""
    pass

class TokenExpiredError(AuthenticationError):
    """Token has expired."""
    pass

class InvalidTokenError(AuthenticationError):
    """Invalid token provided."""
    pass

class RateLimitExceededError(AuthenticationError):
    """Rate limit exceeded."""
    pass