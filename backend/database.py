"""
In-memory database for the AI Healthcare Imaging System.
All data is stored in Python dicts/lists for demo purposes.
Can be swapped to Firebase/MongoDB later.
"""

import uuid
import hashlib
from datetime import datetime


def _id():
    return str(uuid.uuid4())[:8]


def _now():
    return datetime.utcnow().isoformat() + "Z"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Seed data ────────────────────────────────────────────────

users = [
    {
        "id": "USR-001",
        "name": "Rahul Sharma",
        "email": "patient@example.com",
        "password_hash": _hash_password("password123"),
        "role": "patient",
        "reference_id": "PAT-001",
        "created_at": "2026-04-20T09:00:00Z",
    },
    {
        "id": "USR-002",
        "name": "Dr. Anika Verma",
        "email": "doctor@example.com",
        "password_hash": _hash_password("password123"),
        "role": "doctor",
        "reference_id": "DOC-001",
        "created_at": "2026-04-20T09:00:00Z",
    },
    {
        "id": "USR-003",
        "name": "Admin Reena",
        "email": "staff@example.com",
        "password_hash": _hash_password("password123"),
        "role": "staff",
        "reference_id": "STAFF-001",
        "created_at": "2026-04-20T09:00:00Z",
    }
]

patients = [
    {
        "id": "PAT-001",
        "name": "Rahul Sharma",
        "age": 45,
        "gender": "Male",
        "contact": "+91-98765-43210",
        "phone": "+91-98765-43210",
        "password_hash": _hash_password("health123"),
        "preferredLanguage": "English",
        "condition": "Chest discomfort, routine screening",
        "status": "active",
        "created_at": "2026-04-20T09:00:00Z",
    },
    {
        "id": "PAT-002",
        "name": "Priya Menon",
        "age": 32,
        "gender": "Female",
        "contact": "+91-87654-32100",
        "phone": "+91-87654-32100",
        "password_hash": _hash_password("health123"),
        "preferredLanguage": "Hindi",
        "condition": "Recurring headaches, MRI scheduled",
        "status": "active",
        "created_at": "2026-04-22T11:30:00Z",
    },
    {
        "id": "PAT-003",
        "name": "Amit Patel",
        "age": 58,
        "gender": "Male",
        "contact": "+91-76543-21000",
        "phone": "+91-76543-21000",
        "password_hash": _hash_password("health123"),
        "preferredLanguage": "English",
        "condition": "Knee joint pain, X-ray review",
        "status": "active",
        "created_at": "2026-04-25T14:15:00Z",
    },
    {
        "id": "PAT-004",
        "name": "Sneha Reddy",
        "age": 27,
        "gender": "Female",
        "contact": "+91-65432-10000",
        "phone": "+91-65432-10000",
        "password_hash": _hash_password("health123"),
        "preferredLanguage": "Telugu",
        "condition": "Routine dental imaging",
        "status": "completed",
        "created_at": "2026-04-18T08:00:00Z",
    },
]

doctors = [
    {
        "id": "DOC-001",
        "name": "Dr. Anika Verma",
        "specialty": "Radiology",
        "email": "anika@healthai.com",
        "status": "active",
    },
    {
        "id": "DOC-002",
        "name": "Dr. Rajesh Kumar",
        "specialty": "Cardiology",
        "email": "rajesh@healthai.com",
        "status": "active",
    },
    {
        "id": "DOC-003",
        "name": "Dr. Priya Sharma",
        "specialty": "Neurology",
        "email": "priya@healthai.com",
        "status": "active",
    },
    {
        "id": "DOC-004",
        "name": "Dr. Suresh Nair",
        "specialty": "ENT",
        "email": "suresh@healthai.com",
        "status": "active",
    },
    {
        "id": "DOC-005",
        "name": "Dr. Meera Joshi",
        "specialty": "Cardiology",
        "email": "meera@healthai.com",
        "status": "active",
    },
    {
        "id": "DOC-006",
        "name": "Dr. Arif Khan",
        "specialty": "Dental",
        "email": "arif@healthai.com",
        "status": "active",
    },
]


doctor_availability = [
    {
        "doctor_id": "DOC-001",
        "available_days": ["Monday", "Wednesday", "Friday"],
        "time_slots": ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM"],
    },
    {
        "doctor_id": "DOC-002",
        "available_days": ["Tuesday", "Thursday"],
        "time_slots": ["10:00 AM", "11:00 AM", "12:00 PM", "04:00 PM", "05:00 PM"],
    },
    {
        "doctor_id": "DOC-003",
        "available_days": ["Monday", "Tuesday", "Wednesday"],
        "time_slots": ["08:00 AM", "09:00 AM", "01:00 PM", "02:00 PM"],
    },
    {
        "doctor_id": "DOC-005",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "time_slots": ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM"],
    },
]

imaging_records = [
    {
        "id": "IMG-001",
        "patient_id": "PAT-001",
        "type": "Chest X-Ray",
        "uploaded_at": "2026-04-26T10:00:00Z",
        "status": "analyzed",
        "doctor_id": "DOC-001",
        "ai_analysis": None,
    },
    {
        "id": "IMG-002",
        "patient_id": "PAT-002",
        "type": "Brain MRI",
        "uploaded_at": "2026-04-27T09:30:00Z",
        "status": "pending",
        "doctor_id": "DOC-002",
        "ai_analysis": None,
    },
    {
        "id": "IMG-003",
        "patient_id": "PAT-003",
        "type": "Knee X-Ray",
        "uploaded_at": "2026-04-28T13:00:00Z",
        "status": "analyzed",
        "doctor_id": "DOC-003",
        "ai_analysis": {
            "patient_summary": "You have a mild fracture. Take medicine twice daily.",
            "specialist_report": {
                "severity": "moderate",
                "recommendation": "Rest and medication"
            },
            "compliance": {
                "compliant": True
            }
        },
    },
]

notifications = [
    {
        "id": "NOTIF-001",
        "patient_id": "PAT-001",
        "type": "health_warning",
        "title": "Health Warning",
        "message": "Your recent heart rate has been irregular. Please avoid strenuous activities today.",
        "severity": "high",
        "read": False,
        "created_at": "2026-04-28T09:00:00Z",
    },
    {
        "id": "NOTIF-002",
        "patient_id": "PAT-001",
        "type": "medicine_reminder",
        "title": "Medicine Reminder",
        "message": "Don't forget to take your prescribed medicine (Atorvastatin) after lunch.",
        "severity": "low",
        "read": False,
        "created_at": "2026-04-29T12:00:00Z",
    },
    {
        "id": "NOTIF-003",
        "patient_id": "PAT-003",
        "type": "ai_report_ready",
        "title": "Your scan report is ready",
        "message": "You have a mild fracture. Take medicine twice daily.",
        "severity": "moderate",
        "read": False,
        "created_at": "2026-04-29T14:00:00Z",
    },
    {
        "id": "NOTIF-004",
        "patient_id": "PAT-003",
        "type": "follow_up",
        "title": "Follow-up Notification",
        "message": "Please book a follow-up appointment with Dr. Fatima Sheikh next week.",
        "severity": "moderate",
        "read": False,
        "created_at": "2026-04-29T15:00:00Z",
    },
    {
        "id": "NOTIF-005",
        "patient_id": "PAT-002",
        "type": "new_report",
        "title": "📄 New Report Uploaded",
        "message": "Your Brain MRI report has been uploaded. View it in the Reports section.",
        "severity": "normal",
        "read": False,
        "created_at": "2026-04-29T10:00:00Z",
    },
    {
        "id": "NOTIF-006",
        "patient_id": "PAT-004",
        "type": "medicine_reminder",
        "title": "💊 Medicine Reminder",
        "message": "Take your prescribed pain relief medication before bed.",
        "severity": "low",
        "read": False,
        "created_at": "2026-04-29T20:00:00Z",
    },
]

agent_logs = []

staff_tasks = [
    {
        "id": "TASK-001",
        "title": "Schedule MRI for PAT-002",
        "assigned_to": "Nurse Kavita",
        "status": "in_progress",
        "priority": "high",
        "created_at": "2026-04-27T08:00:00Z",
    },
    {
        "id": "TASK-002",
        "title": "Prepare X-Ray room B",
        "assigned_to": "Tech Arjun",
        "status": "completed",
        "priority": "medium",
        "created_at": "2026-04-26T07:30:00Z",
    },
    {
        "id": "TASK-003",
        "title": "Follow-up call to PAT-004",
        "assigned_to": "Admin Reena",
        "status": "pending",
        "priority": "low",
        "created_at": "2026-04-28T10:00:00Z",
    },
]

# ── New collections for Patient Portal ───────────────────────

reports = [
    {
        "id": "RPT-001",
        "patient_id": "PAT-001",
        "reportName": "Chest X-Ray Report",
        "reportType": "pdf",
        "filePath": "",
        "uploadDate": "2026-04-26T11:00:00Z",
        "doctor": "Dr. Anika Verma",
        "summary": "Mild cardiomegaly detected. Heart size slightly enlarged. No acute infiltrates. Lungs are clear. Recommend follow-up echocardiogram.",
        "imaging_id": "IMG-001",
    },
    {
        "id": "RPT-002",
        "patient_id": "PAT-001",
        "reportName": "Blood Test Results",
        "reportType": "pdf",
        "filePath": "",
        "uploadDate": "2026-04-25T09:00:00Z",
        "doctor": "Dr. Meera Joshi",
        "summary": "Complete blood count within normal range. Cholesterol slightly elevated at 215 mg/dL. LDL 140 mg/dL. Recommend dietary modifications.",
        "imaging_id": None,
    },
    {
        "id": "RPT-003",
        "patient_id": "PAT-002",
        "reportName": "Brain MRI Report",
        "reportType": "pdf",
        "filePath": "",
        "uploadDate": "2026-04-27T14:00:00Z",
        "doctor": "Dr. Rajesh Kumar",
        "summary": "Minor white-matter hyperintensities noted. No intracranial mass or hemorrhage. Ventricles are normal in size. Recommend follow-up in 6 months.",
        "imaging_id": "IMG-002",
    },
    {
        "id": "RPT-004",
        "patient_id": "PAT-003",
        "reportName": "Knee X-Ray Report",
        "reportType": "pdf",
        "filePath": "",
        "uploadDate": "2026-04-28T15:00:00Z",
        "doctor": "Dr. Fatima Sheikh",
        "summary": "Mild osteoarthritis changes with joint space narrowing in medial compartment. No acute fracture. Recommend physiotherapy and anti-inflammatory medication.",
        "imaging_id": "IMG-003",
    },
    {
        "id": "RPT-005",
        "patient_id": "PAT-003",
        "reportName": "Bone Density Scan",
        "reportType": "pdf",
        "filePath": "",
        "uploadDate": "2026-04-27T11:00:00Z",
        "doctor": "Dr. Fatima Sheikh",
        "summary": "T-score of -1.8 indicates osteopenia. Recommend calcium and Vitamin D supplementation. Follow-up DEXA scan in 12 months.",
        "imaging_id": None,
    },
    {
        "id": "RPT-006",
        "patient_id": "PAT-004",
        "reportName": "Dental X-Ray Report",
        "reportType": "pdf",
        "filePath": "",
        "uploadDate": "2026-04-19T10:00:00Z",
        "doctor": "Dr. Arif Khan",
        "summary": "No dental pathology detected. Teeth and surrounding structures appear normal. Routine dental hygiene recommended.",
        "imaging_id": None,
    },
]

prescriptions = [
    {
        "id": "PRSC-001",
        "patient_id": "PAT-001",
        "medication": "Atorvastatin 10mg",
        "dosage": "Once daily after dinner",
        "doctor": "Dr. Meera Joshi",
        "startDate": "2026-04-26T00:00:00Z",
        "endDate": "2026-07-26T00:00:00Z",
        "status": "active",
        "notes": "For cholesterol management. Avoid grapefruit juice.",
    },
    {
        "id": "PRSC-002",
        "patient_id": "PAT-001",
        "medication": "Aspirin 75mg",
        "dosage": "Once daily after breakfast",
        "doctor": "Dr. Meera Joshi",
        "startDate": "2026-04-26T00:00:00Z",
        "endDate": "2026-10-26T00:00:00Z",
        "status": "active",
        "notes": "Blood thinner for cardiac care.",
    },
    {
        "id": "PRSC-003",
        "patient_id": "PAT-002",
        "medication": "Sumatriptan 50mg",
        "dosage": "As needed for migraine (max 2/day)",
        "doctor": "Dr. Rajesh Kumar",
        "startDate": "2026-04-22T00:00:00Z",
        "endDate": "2026-06-22T00:00:00Z",
        "status": "active",
        "notes": "Take at onset of migraine. Do not exceed 2 tablets in 24 hours.",
    },
    {
        "id": "PRSC-004",
        "patient_id": "PAT-003",
        "medication": "Ibuprofen 400mg",
        "dosage": "Twice daily after meals",
        "doctor": "Dr. Fatima Sheikh",
        "startDate": "2026-04-28T00:00:00Z",
        "endDate": "2026-05-28T00:00:00Z",
        "status": "active",
        "notes": "Anti-inflammatory for knee joint pain. Take with food.",
    },
    {
        "id": "PRSC-005",
        "patient_id": "PAT-003",
        "medication": "Calcium + Vitamin D",
        "dosage": "Once daily morning",
        "doctor": "Dr. Fatima Sheikh",
        "startDate": "2026-04-28T00:00:00Z",
        "endDate": "2026-10-28T00:00:00Z",
        "status": "active",
        "notes": "Supplementation for osteopenia.",
    },
]

appointments = [
    {
        "id": "APT-001",
        "patient_id": "PAT-001",
        "doctor": "Dr. Meera Joshi",
        "specialty": "Cardiology",
        "date": "2026-05-05T10:00:00Z",
        "type": "Follow-up",
        "status": "scheduled",
        "notes": "Echocardiogram follow-up",
    },
    {
        "id": "APT-002",
        "patient_id": "PAT-001",
        "doctor": "Dr. Anika Verma",
        "specialty": "Radiology",
        "date": "2026-05-15T14:00:00Z",
        "type": "Routine Check",
        "status": "scheduled",
        "notes": "Follow-up chest X-ray",
    },
    {
        "id": "APT-003",
        "patient_id": "PAT-002",
        "doctor": "Dr. Rajesh Kumar",
        "specialty": "Neurology",
        "date": "2026-05-10T11:00:00Z",
        "type": "Follow-up",
        "status": "scheduled",
        "notes": "MRI results review",
    },
    {
        "id": "APT-004",
        "patient_id": "PAT-003",
        "doctor": "Dr. Fatima Sheikh",
        "specialty": "Orthopedics",
        "date": "2026-05-08T09:30:00Z",
        "type": "Follow-up",
        "status": "scheduled",
        "notes": "Knee joint review and physiotherapy plan",
    },
    {
        "id": "APT-005",
        "patient_id": "PAT-004",
        "doctor": "Dr. Arif Khan",
        "specialty": "Dental",
        "date": "2026-05-20T15:00:00Z",
        "type": "Routine Check",
        "status": "scheduled",
        "notes": "6-month dental check-up",
    },
]

# ── Scan Sharing (DICOM-ready) ───────────────────────────────

scans = [
    {
        "id": "SCAN-001",
        "patient_id": "PAT-001",
        "doctor_id": "DOC-001",
        "study_id": "STD-0001",
        "title": "Chest X-Ray Anterior",
        "scan_title": "Chest X-Ray Anterior",
        "scan_type": "X-Ray",
        "body_part": "Chest",
        "notes": "Routine screening. Please check for cardiomegaly.",
        "file_name": "chest_xray_anterior.dcm",
        "file_path": "",
        "dicom_path": "",
        "stored_name": "demo_chest_xray.dcm",
        "preview_type": "dicom",
        "file_size": 2048576,
        "file_size_formatted": "2.0 MB",
        "metadata": {
            "patient_name": "Rahul Sharma",
            "patient_id": "PAT-001",
            "study_date": "2026-04-26",
            "modality": "DX",
            "body_part": "CHEST",
            "image_dimensions": "2048 x 2048",
            "study_description": "PA Chest X-Ray",
            "institution": "HealthAI Hospital",
            "manufacturer": "Siemens",
            "bits_allocated": 16,
            "_simulated": True,
        },
        "status": "uploaded",
        "created_at": "2026-04-26T10:30:00Z",
    },
    {
        "id": "SCAN-002",
        "patient_id": "PAT-002",
        "doctor_id": "DOC-002",
        "study_id": "STD-0002",
        "title": "Brain MRI Sagittal",
        "scan_title": "Brain MRI Sagittal",
        "scan_type": "MRI",
        "body_part": "Brain",
        "notes": "Follow-up scan for recurring headaches. Compare with previous results.",
        "file_name": "brain_mri_sagittal.dcm",
        "file_path": "",
        "dicom_path": "",
        "stored_name": "demo_brain_mri.dcm",
        "preview_type": "dicom",
        "file_size": 5242880,
        "file_size_formatted": "5.0 MB",
        "metadata": {
            "patient_name": "Priya Menon",
            "patient_id": "PAT-002",
            "study_date": "2026-04-27",
            "modality": "MR",
            "body_part": "BRAIN",
            "image_dimensions": "512 x 512",
            "study_description": "MRI Brain Sagittal T1",
            "institution": "HealthAI Hospital",
            "manufacturer": "GE Medical Systems",
            "bits_allocated": 16,
            "_simulated": True,
        },
        "status": "uploaded",
        "created_at": "2026-04-27T10:00:00Z",
    },
    {
        "id": "SCAN-003",
        "patient_id": "PAT-003",
        "doctor_id": "DOC-003",
        "study_id": "STD-0003",
        "title": "Knee X-Ray Lateral",
        "scan_title": "Knee X-Ray Lateral",
        "scan_type": "X-Ray",
        "body_part": "Knee",
        "notes": "Check for joint space narrowing and osteoarthritis progression.",
        "file_name": "knee_xray_lateral.dcm",
        "file_path": "",
        "dicom_path": "",
        "stored_name": "demo_knee_xray.dcm",
        "preview_type": "dicom",
        "file_size": 1572864,
        "file_size_formatted": "1.5 MB",
        "metadata": {
            "patient_name": "Amit Patel",
            "patient_id": "PAT-003",
            "study_date": "2026-04-28",
            "modality": "DX",
            "body_part": "KNEE",
            "image_dimensions": "1024 x 1024",
            "study_description": "Knee Lateral View",
            "institution": "HealthAI Hospital",
            "manufacturer": "Philips",
            "bits_allocated": 12,
            "_simulated": True,
        },
        "status": "uploaded",
        "created_at": "2026-04-28T13:30:00Z",
    },
]

audit_logs = [
    {
        "id": "AUDIT-001",
        "action": "scan_uploaded",
        "actor": "DOC-001",
        "actor_name": "Dr. Anika Verma",
        "target": "PAT-001",
        "target_name": "Rahul Sharma",
        "detail": "Uploaded X-Ray scan: Chest X-Ray Anterior",
        "scan_id": "SCAN-001",
        "timestamp": "2026-04-26T10:30:00Z",
    },
    {
        "id": "AUDIT-002",
        "action": "scan_uploaded",
        "actor": "DOC-002",
        "actor_name": "Dr. Rajesh Kumar",
        "target": "PAT-002",
        "target_name": "Priya Menon",
        "detail": "Uploaded MRI scan: Brain MRI Sagittal",
        "scan_id": "SCAN-002",
        "timestamp": "2026-04-27T10:00:00Z",
    },
    {
        "id": "AUDIT-003",
        "action": "scan_uploaded",
        "actor": "DOC-003",
        "actor_name": "Dr. Fatima Sheikh",
        "target": "PAT-003",
        "target_name": "Amit Patel",
        "detail": "Uploaded X-Ray scan: Knee X-Ray Lateral",
        "scan_id": "SCAN-003",
        "timestamp": "2026-04-28T13:30:00Z",
    },
]

translated_reports = []

# ── Scan Categories ──────────────────────────────────────────

scan_categories = [
    {"id": "SC-001", "name": "None",       "status": "active", "created_at": "2026-04-20T09:00:00Z"},
    {"id": "SC-002", "name": "X-Ray",      "status": "active", "created_at": "2026-04-20T09:00:00Z"},
    {"id": "SC-003", "name": "CT Scan",    "status": "active", "created_at": "2026-04-20T09:00:00Z"},
    {"id": "SC-004", "name": "MRI",        "status": "active", "created_at": "2026-04-20T09:00:00Z"},
    {"id": "SC-005", "name": "Ultrasound", "status": "active", "created_at": "2026-04-20T09:00:00Z"},
]

# ── Full Appointment Requests (structured booking) ───────────

full_appointments = []

# ── Full Prescriptions (doctor-authored) ─────────────────────

full_prescriptions = []
