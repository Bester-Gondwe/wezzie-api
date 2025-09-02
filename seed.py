import uuid
import argparse
from datetime import datetime
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import bcrypt
from app.models.all_models import Base, User, StaffProfile, UserRole, Gender, blantyre_now
from app.config import settings

def create_admin_user(email, password, first_name, last_name, phone, employee_id, gender="male"):
    # Database connection (adjust connection string as needed)
    DATABASE_URL = settings.DATABASE_URL
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if admin user already exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            print(f"Error: User with email {email} already exists")
            return

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Create new admin user
        new_user = User(
            id=uuid.uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=hashed_password,
            role=UserRole.ADMIN,
            gender=Gender[gender.upper()],
            is_active=True,
            created_at=blantyre_now(),
            updated_at=blantyre_now()
        )

        # Create corresponding staff profile
        new_staff_profile = StaffProfile(
            id=uuid.uuid4(),
            user_id=new_user.id,
            employee_id=employee_id,
            is_available_online=False,
            created_at=blantyre_now(),
            updated_at=blantyre_now()
        )

        # Add to session and commit
        session.add(new_user)
        session.add(new_staff_profile)
        session.commit()
        
        print(f"Admin user created successfully: {email}")
        print(f"Employee ID: {employee_id}")

    except Exception as e:
        session.rollback()
        print(f"Error creating admin user: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--first-name", required=True, help="First name")
    parser.add_argument("--last-name", required=True, help="Last name")
    parser.add_argument("--phone", required=True, help="Phone number")
    parser.add_argument("--employee-id", required=True, help="Employee ID")
    parser.add_argument("--gender", default="male", choices=["male", "female", "other"], help="Gender")

    args = parser.parse_args()

    create_admin_user(
        email=args.email,
        password=args.password,
        first_name=args.first_name,
        last_name=args.last_name,
        phone=args.phone,
        employee_id=args.employee_id,
        gender=args.gender
    )