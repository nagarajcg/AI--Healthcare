"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel
from typing import Optional, List


class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    contact: str
    condition: str


class ImagingUpload(BaseModel):
    patient_id: str
    type: str
    doctor_id: str


class AgentAnalysisRequest(BaseModel):
    imaging_id: str


class StaffTaskCreate(BaseModel):
    title: str
    assigned_to: str
    priority: str = "medium"


class DoctorApproval(BaseModel):
    imaging_id: str
    approved: bool
    doctor_notes: Optional[str] = ""


class NotificationRead(BaseModel):
    notification_id: str


# ── Patient Auth ─────────────────────────────────────────────

class PatientLogin(BaseModel):
    patientId: str

class PatientRegister(BaseModel):
    name: str
    age: int
    gender: str
    email: Optional[str] = None


class PatientUpdate(BaseModel):
    preferredLanguage: Optional[str] = None
    phone: Optional[str] = None


# ── Translation ──────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: Optional[str] = ""
    target_language: str = "English"
    report_id: Optional[str] = None

class TranslatedReport(BaseModel):
    report_id: Optional[str]
    language: str
    original_text: str
    simplified_text: str
    translated_text: str
    created_at: str


# ── Scan Categories ──────────────────────────────────────────

class ScanCategoryCreate(BaseModel):
    name: str
    status: str = "active"

class ScanCategoryUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


# ── Appointments ─────────────────────────────────────────────

class AppointmentBook(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_date: str
    time_slot: str
    reason: str
    scan_requirement: str = "None"

class AppointmentApprove(BaseModel):
    assigned_doctor_id: Optional[str] = None


# ── Full Prescriptions ───────────────────────────────────────

class PrescriptionCreate(BaseModel):
    doctor_id: str
    patient_id: str
    diagnosis: str
    medicines: str
    dosage: str
    instructions: str
    test_recommendations: Optional[str] = ""
    follow_up_date: Optional[str] = None
