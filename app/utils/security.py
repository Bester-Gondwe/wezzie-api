# from fastapi import HTTPException, Depends, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from jose import JWTError, jwt
# from datetime import datetime, timedelta
# from typing import Optional
# from app.models.all_models import User, UserRole
# from sqlalchemy.orm import Session
# from app.database import get_db
# import os

# # JWT configuration
# SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# security = HTTPBearer()

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     try:
#         payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
#         return payload
#     except JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

# async def get_current_user(
#     token: dict = Depends(verify_token),
#     db: Session = Depends(get_db)
# ):
#     user_id = token.get("sub")
#     if not user_id:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#         )
    
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found",
#         )
    
#     if not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User inactive",
#         )
    
#     return user

# def require_role(required_roles: list[UserRole]):
#     def role_checker(current_user: User = Depends(get_current_user)):
#         if current_user.role not in required_roles:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Insufficient permissions",
#             )
#         return current_user
#     return role_checker

# # Admin role checker
# require_admin = require_role([UserRole.ADMIN])
# # Admin and staff role checker
# require_admin_or_staff = require_role([UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST])