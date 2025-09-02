# app/models/all_models.py
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Float, JSON, Enum, Date, Time, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import uuid
from datetime import datetime
import pytz

Base = declarative_base()

# Timezone setup
BLANTYRE_TZ = pytz.timezone('Africa/Blantyre')

def blantyre_now():
    return datetime.now(BLANTYRE_TZ)

# Enums
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    NURSE = "nurse"
    ADMIN = "admin"
    RECEPTIONIST = "receptionist"
    AMBULANCE_DRIVER = "ambulance_driver"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"
    CRITICAL = "critical"

class AmbulancePriority(str, enum.Enum):
    ROUTINE = "routine"          # Non-urgent transfers
    URGENT = "urgent"            # Stable but needs quick transport
    EMERGENCY = "emergency"      # Life-threatening but stable
    CRITICAL = "critical"        # Life-threatening, unstable
    CODE_RED = "code_red"        # Mass casualty, disaster response

class AmbulanceStatus(str, enum.Enum):
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    EN_ROUTE_PICKUP = "en_route_pickup"
    ARRIVED_PICKUP = "arrived_pickup"
    TRANSPORTING = "transporting"
    EN_ROUTE_HOSPITAL = "en_route_hospital"
    ARRIVED_HOSPITAL = "arrived_hospital"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CaseSeverity(str, enum.Enum):
    MINOR = "minor"              # Minor injuries/illness
    MODERATE = "moderate"        # Requires medical attention but not urgent
    SERIOUS = "serious"          # Requires urgent medical attention
    SEVERE = "severe"            # Life-threatening condition
    CRITICAL = "critical"        # Immediate life-saving intervention needed

class InquiryCategory(str, enum.Enum):
    GENERAL = "general"
    APPOINTMENT = "appointment"
    SERVICES = "services"
    NAVIGATION = "navigation"
    EMERGENCY = "emergency"
    BILLING = "billing"
    FEEDBACK = "feedback"
    OTHER = "other"

class InquiryStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ResponseMethod(str, enum.Enum):
    SYSTEM = "system"
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    WHATSAPP = "whatsapp"

class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class LocationType(str, enum.Enum):
    BUILDING = "building"
    FLOOR = "floor"
    DEPARTMENT = "department"
    ROOM = "room"
    FACILITY = "facility"
    LANDMARK = "landmark"

class VisitType(str, enum.Enum):
    OPD = "opd"
    IPD = "ipd"
    EMERGENCY = "emergency"
    ANTENATAL = "antenatal"
    THEATRE = "theatre"
    DIAGNOSTIC = "diagnostic"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"

class NotificationType(str, enum.Enum):
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    AMBULANCE_UPDATE = "ambulance_update"
    INQUIRY_RESPONSE = "inquiry_response"
    SYSTEM_ALERT = "system_alert"
    PROMOTION = "promotion"
    OTHER = "other"

class DataType(str, enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"

class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

# ================================
# SERVICE CATEGORY TABLE
# ================================

class ServiceCategory(Base):
    __tablename__ = "service_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    color_code = Column(String(7))  # HEX color
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    services = relationship("Service", back_populates="category")

# ================================
# GEOGRAPHICAL MODELS
# ================================

class District(Base):
    __tablename__ = "districts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(10), unique=True, nullable=False)
    region = Column(String(50))  # Northern, Central, Southern
    population = Column(Integer)
    area_sq_km = Column(Float)
    coordinates = Column(JSON)  # Polygon coordinates for mapping
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    areas = relationship("Area", back_populates="district", cascade="all, delete-orphan")
    ambulance_coverage = relationship("AmbulanceCoverage", back_populates="district", cascade="all, delete-orphan")
    patient_profiles = relationship("PatientProfile", back_populates="district")

class Area(Base):
    __tablename__ = "areas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    district_id = Column(UUID(as_uuid=True), ForeignKey("districts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(10), nullable=False)
    type = Column(Enum('urban', 'rural', 'periurban', name="area_type"), default='urban')
    population_density = Column(Enum('low', 'medium', 'high', 'very_high', name="density_level"))
    coordinates = Column(JSON)  # Polygon coordinates
    is_serviced = Column(Boolean, default=True)  # Whether ambulance service is available
    estimated_response_time = Column(Integer)  # Minutes
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    district = relationship("District", back_populates="areas")
    ambulance_coverage = relationship("AmbulanceCoverage", back_populates="area", cascade="all, delete-orphan")
    patient_profiles = relationship("PatientProfile", back_populates="area")
    
    __table_args__ = (
        UniqueConstraint('district_id', 'code', name='uq_area_district_code'),
    )

class AmbulanceCoverage(Base):
    __tablename__ = "ambulance_coverage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    district_id = Column(UUID(as_uuid=True), ForeignKey("districts.id"))
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"))
    ambulance_id = Column(UUID(as_uuid=True), ForeignKey("ambulances.id"), nullable=False)
    coverage_radius_km = Column(Float, default=50.0)
    is_active = Column(Boolean, default=True)
    available_from = Column(Time)
    available_to = Column(Time)
    weekdays = Column(JSON)  # ['monday', 'tuesday', ...]
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    district = relationship("District", back_populates="ambulance_coverage")
    area = relationship("Area", back_populates="ambulance_coverage")
    ambulance = relationship("Ambulance", back_populates="coverage_areas")

class Ambulance(Base):
    __tablename__ = "ambulances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    registration_number = Column(String(20), unique=True, nullable=False)
    vehicle_type = Column(Enum('basic', 'advanced', 'mobile_icu', 'neonatal', 'patient_transport', name="ambulance_type"))
    model = Column(String(50))
    year = Column(Integer)
    capacity = Column(Integer)  # Number of patients
    equipment = Column(JSON)  # List of medical equipment
    is_operational = Column(Boolean, default=True)
    current_location = Column(String(255))
    current_coordinates = Column(String(100))  # lat,lng
    fuel_level = Column(Enum('empty', 'low', 'medium', 'full', name="fuel_level"))
    last_maintenance = Column(Date)
    next_maintenance = Column(Date)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    coverage_areas = relationship("AmbulanceCoverage", back_populates="ambulance", cascade="all, delete-orphan")
    bookings = relationship("AmbulanceBooking", back_populates="ambulance_vehicle")

# ================================
# CORE USER MANAGEMENT MODELS
# ================================

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), unique=True)
    password = Column(String(255), nullable=True)
    otp = Column(String(6), nullable=True)
    role = Column(ENUM(UserRole, name="user_role"), nullable=False, default=UserRole.PATIENT)
    email_verified_at = Column(DateTime)
    phone_verified_at = Column(DateTime)
    profile_image = Column(String(255))
    date_of_birth = Column(Date)
    gender = Column(ENUM(Gender, name="gender"), nullable=False)
    preferred_language = Column(String(10), default="en")
    accessibility_needs = Column(JSON)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    staff_profile = relationship("StaffProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    appointments_as_patient = relationship("Appointment", foreign_keys="Appointment.patient_id", back_populates="patient")
    appointments_as_doctor = relationship("Appointment", foreign_keys="Appointment.doctor_id", back_populates="doctor")
    created_appointments = relationship("Appointment", foreign_keys="Appointment.created_by", back_populates="creator")
    ambulance_bookings_as_patient = relationship("AmbulanceBooking", foreign_keys="AmbulanceBooking.patient_id", back_populates="patient")
    ambulance_bookings_as_driver = relationship("AmbulanceBooking", foreign_keys="AmbulanceBooking.driver_id", back_populates="driver")
    inquiries = relationship("Inquiry", foreign_keys="Inquiry.user_id", back_populates="user")
    assigned_inquiries = relationship("Inquiry", foreign_keys="Inquiry.assigned_to", back_populates="assigned_staff")
    inquiry_responses = relationship("InquiryResponse", back_populates="responder")
    sent_messages = relationship("ChatMessage", foreign_keys="ChatMessage.sender_id", back_populates="sender")
    received_messages = relationship("ChatMessage", foreign_keys="ChatMessage.receiver_id", back_populates="receiver")
    visits_as_patient = relationship("PatientVisit", foreign_keys="PatientVisit.patient_id", back_populates="patient")
    visits_as_doctor = relationship("PatientVisit", foreign_keys="PatientVisit.doctor_id", back_populates="doctor")
    notifications = relationship("Notification", back_populates="user")
    activity_logs = relationship("ActivityLog", back_populates="user")
    department_head = relationship("Department", foreign_keys="Department.head_of_department_id", back_populates="head_of_department")
    dispatch_logs = relationship("AmbulanceDispatchLog", foreign_keys="AmbulanceDispatchLog.dispatcher_id", back_populates="dispatcher")

class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(String(20), unique=True, nullable=False)
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    emergency_contact_relationship = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    district_id = Column(UUID(as_uuid=True), ForeignKey("districts.id"))
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"))
    postal_code = Column(String(20))
    national_id = Column(String(50))
    insurance_provider = Column(String(100))
    insurance_number = Column(String(100))
    blood_type = Column(String(5))
    allergies = Column(Text)
    chronic_conditions = Column(Text)
    current_medications = Column(Text)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    user = relationship("User", back_populates="patient_profile")
    district = relationship("District", back_populates="patient_profiles")
    area = relationship("Area", back_populates="patient_profiles")

class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(String(20), unique=True, nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    specialization = Column(String(100))
    license_number = Column(String(100))
    qualifications = Column(Text)
    years_of_experience = Column(Integer, default=0)
    consultation_fee = Column(Float)
    is_available_online = Column(Boolean, default=True)
    working_hours = Column(JSON)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    user = relationship("User", back_populates="staff_profile")
    department = relationship("Department", back_populates="staff_members")

# ================================
# ORGANIZATIONAL STRUCTURE
# ================================

class Department(Base):
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    description = Column(Text)
    head_of_department_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    floor_number = Column(Integer)
    location_description = Column(Text)
    phone = Column(String(20))
    email = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    head_of_department = relationship("User", foreign_keys=[head_of_department_id], back_populates="department_head")
    staff_members = relationship("StaffProfile", back_populates="department")
    services = relationship("Service", back_populates="department")
    appointments = relationship("Appointment", back_populates="department")
    patient_visits = relationship("PatientVisit", back_populates="department")

class Service(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("service_categories.id"), nullable=False)
    description = Column(Text)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    base_cost = Column(Float)
    duration_minutes = Column(Integer, default=30)
    requires_appointment = Column(Boolean, default=True)
    is_emergency_service = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    category = relationship("ServiceCategory", back_populates="services")
    department = relationship("Department", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")
    patient_visits = relationship("PatientVisit", back_populates="service")

# ================================
# APPOINTMENT & BOOKING SYSTEM
# ================================

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    estimated_duration = Column(Integer, default=30)
    status = Column(ENUM(AppointmentStatus, name="appointment_status"), default=AppointmentStatus.SCHEDULED)
    priority = Column(ENUM(Priority, name="priority"), default=Priority.MEDIUM)
    symptoms = Column(Text)
    special_requirements = Column(Text)
    notes = Column(Text)
    confirmation_method = Column(ENUM(ResponseMethod, name="confirmation_method"))
    confirmed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], back_populates="appointments_as_patient")
    doctor = relationship("User", foreign_keys=[doctor_id], back_populates="appointments_as_doctor")
    service = relationship("Service", back_populates="appointments")
    department = relationship("Department", back_populates="appointments")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_appointments")
    patient_visit = relationship("PatientVisit", back_populates="appointment", uselist=False)

class AmbulanceBooking(Base):
    __tablename__ = "ambulance_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    ambulance_id = Column(UUID(as_uuid=True), ForeignKey("ambulances.id"))
    case_severity = Column(ENUM(CaseSeverity, name="case_severity"), nullable=False)
    priority = Column(ENUM(AmbulancePriority, name="ambulance_priority"), nullable=False)
    
    # Location details
    pickup_location = Column(Text, nullable=False)
    pickup_district_id = Column(UUID(as_uuid=True), ForeignKey("districts.id"))
    pickup_area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"))
    pickup_coordinates = Column(String(100))
    
    destination = Column(Text, nullable=False)
    destination_district_id = Column(UUID(as_uuid=True), ForeignKey("districts.id"))
    destination_area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"))
    destination_coordinates = Column(String(100))
    
    requested_datetime = Column(DateTime, nullable=False)
    status = Column(ENUM(AmbulanceStatus, name="ambulance_status"), default=AmbulanceStatus.REQUESTED)
    
    # Medical details
    patient_condition = Column(Text)
    special_equipment_needed = Column(Text)
    vital_signs = Column(JSON)  # {bp: '120/80', pulse: 72, spo2: 98}
    medical_history = Column(Text)
    
    # Contact information
    contact_person_name = Column(String(100))
    contact_person_phone = Column(String(20))
    
    # Financial details
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    distance_km = Column(Float)
    insurance_coverage = Column(Boolean, default=False)
    
    # Timestamps for status tracking
    notes = Column(Text)
    assigned_at = Column(DateTime)
    en_route_pickup_at = Column(DateTime)
    arrived_pickup_at = Column(DateTime)
    transporting_at = Column(DateTime)
    en_route_hospital_at = Column(DateTime)
    arrived_hospital_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], back_populates="ambulance_bookings_as_patient")
    driver = relationship("User", foreign_keys=[driver_id], back_populates="ambulance_bookings_as_driver")
    ambulance_vehicle = relationship("Ambulance", back_populates="bookings")
    pickup_district = relationship("District", foreign_keys=[pickup_district_id])
    pickup_area = relationship("Area", foreign_keys=[pickup_area_id])
    destination_district = relationship("District", foreign_keys=[destination_district_id])
    destination_area = relationship("Area", foreign_keys=[destination_area_id])
    dispatch_logs = relationship("AmbulanceDispatchLog", back_populates="booking")

# ================================
# COMMUNICATION & INQUIRY SYSTEM
# ================================

class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    guest_name = Column(String(100))
    guest_email = Column(String(255))
    guest_phone = Column(String(20))
    category = Column(ENUM(InquiryCategory, name="inquiry_category"), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(ENUM(Priority, name="inquiry_priority"), default=Priority.MEDIUM)
    status = Column(ENUM(InquiryStatus, name="inquiry_status"), default=InquiryStatus.OPEN)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    preferred_response_method = Column(ENUM(ResponseMethod, name="preferred_response_method"))
    language = Column(String(10), default="en")
    is_anonymous = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="inquiries")
    assigned_staff = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_inquiries")
    responses = relationship("InquiryResponse", back_populates="inquiry", cascade="all, delete-orphan")

class InquiryResponse(Base):
    __tablename__ = "inquiry_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    inquiry_id = Column(UUID(as_uuid=True), ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False)
    responder_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False)
    response_method = Column(ENUM(ResponseMethod, name="response_method"))
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    inquiry = relationship("Inquiry", back_populates="responses")
    responder = relationship("User", back_populates="inquiry_responses")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    conversation_id = Column(String(100), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    message_type = Column(ENUM(MessageType, name="message_type"), default=MessageType.TEXT)
    file_url = Column(String(255))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

# ================================
# NAVIGATION & FACILITY MANAGEMENT
# ================================

class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    type = Column(ENUM(LocationType, name="location_type"), nullable=False)
    parent_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"))
    floor_number = Column(Integer)
    room_number = Column(String(20))
    description = Column(Text)
    coordinates = Column(String(100))
    accessibility_features = Column(JSON)
    is_public_access = Column(Boolean, default=True)
    operating_hours = Column(JSON)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    parent_location = relationship("Location", remote_side=[id], backref="child_locations")

class NavigationRoute(Base):
    __tablename__ = "navigation_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    from_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    to_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    route_description = Column(Text)
    estimated_walk_time = Column(Integer)
    accessibility_friendly = Column(Boolean, default=True)
    waypoints = Column(JSON)
    instructions = Column(JSON)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])

# ================================
# MEDICAL RECORDS & VISITS
# ================================

class PatientVisit(Base):
    __tablename__ = "patient_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"))
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    visit_type = Column(ENUM(VisitType, name="visit_type"), nullable=False)
    visit_date = Column(Date, nullable=False)
    check_in_time = Column(DateTime)
    check_out_time = Column(DateTime)
    chief_complaint = Column(Text)
    diagnosis = Column(Text)
    treatment_plan = Column(Text)
    prescriptions = Column(Text)
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(Date)
    visit_cost = Column(Float)
    payment_status = Column(ENUM(PaymentStatus, name="payment_status"), default=PaymentStatus.PENDING)
    notes = Column(Text)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], back_populates="visits_as_patient")
    doctor = relationship("User", foreign_keys=[doctor_id], back_populates="visits_as_doctor")
    appointment = relationship("Appointment", back_populates="patient_visit")
    service = relationship("Service", back_populates="patient_visits")
    department = relationship("Department", back_populates="patient_visits")

# ================================
# NOTIFICATIONS & ALERTS
# ================================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(ENUM(NotificationType, name="notification_type"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON)
    channels = Column(JSON)
    priority = Column(ENUM(Priority, name="notification_priority"), default=Priority.MEDIUM)
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    read_at = Column(DateTime)
    scheduled_for = Column(DateTime)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    user = relationship("User", back_populates="notifications")

# ================================
# SYSTEM CONFIGURATION
# ================================

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    category = Column(String(50), nullable=False)
    key_name = Column(String(100), nullable=False)
    value = Column(Text)
    data_type = Column(ENUM(DataType, name="data_type"), default=DataType.STRING)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint('category', 'key_name', name='unique_category_key'),
    )

class Language(Base):
    __tablename__ = "languages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    native_name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

class Translation(Base):
    __tablename__ = "translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    language_code = Column(String(10), ForeignKey("languages.code", ondelete="CASCADE"), nullable=False)
    translation_key = Column(String(255), nullable=False)
    translation_value = Column(Text)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    language = relationship("Language")

    __table_args__ = (
        UniqueConstraint('language_code', 'translation_key', name='unique_lang_key'),
    )

# ================================
# AUDIT & LOGGING
# ================================

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    model_type = Column(String(100))
    model_id = Column(UUID(as_uuid=True))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    user = relationship("User", back_populates="activity_logs")

# ================================
# ADDITIONAL TABLES FOR AMBULANCE MANAGEMENT
# ================================

class AmbulanceDispatchLog(Base):
    __tablename__ = "ambulance_dispatch_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    ambulance_booking_id = Column(UUID(as_uuid=True), ForeignKey("ambulance_bookings.id"), nullable=False)
    dispatcher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(Enum('assigned', 'reassigned', 'status_update', 'cancelled', 'completed', name="dispatch_action"))
    previous_status = Column(String(50))
    new_status = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    booking = relationship("AmbulanceBooking", back_populates="dispatch_logs")
    dispatcher = relationship("User", back_populates="dispatch_logs")

class EmergencyProtocol(Base):
    __tablename__ = "emergency_protocols"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    case_severity = Column(ENUM(CaseSeverity, name="case_severity"), nullable=False)
    priority_level = Column(ENUM(AmbulancePriority, name="ambulance_priority"), nullable=False)
    response_time_target = Column(Integer)  # Minutes
    required_equipment = Column(JSON)
    protocol_steps = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, default=blantyre_now, onupdate=blantyre_now, server_default=text("CURRENT_TIMESTAMP"))