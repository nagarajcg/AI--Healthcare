"""Hospital Staff API routes — includes patient intake with auto-doctor assignment."""

from fastapi import APIRouter
from backend import database as db
from backend.models import StaffTaskCreate
from backend.services.agents import run_full_pipeline
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/staff", tags=["Staff"])


# ── Auto-assign mapping ─────────────────────────────────────
# Keywords in the problem description → specialty → doctor
_SPECIALTY_KEYWORDS = {
    "Radiology": ["chest", "lung", "x-ray", "xray", "ct scan", "scan", "imaging", "pulmonary", "respiratory", "breathing", "cough"],
    "Neurology": ["head", "brain", "headache", "migraine", "neuro", "seizure", "dizziness", "mri brain"],
    "Orthopedics": ["bone", "knee", "joint", "fracture", "spine", "back pain", "shoulder", "hip", "ortho", "leg", "arm"],
    "ENT": ["ear", "nose", "throat", "ent", "sinus", "hearing", "tonsil", "voice"],
    "Cardiology": ["heart", "chest pain", "cardiac", "palpitation", "blood pressure"],
    "Dental": ["tooth", "teeth", "dental", "jaw", "gum"],
}


def _auto_assign_doctor(problem: str) -> dict:
    """Find the best-matching doctor based on problem description keywords."""
    problem_lower = problem.lower()
    matched_specialty = None

    for specialty, keywords in _SPECIALTY_KEYWORDS.items():
        for kw in keywords:
            if kw in problem_lower:
                matched_specialty = specialty
                break
        if matched_specialty:
            break

    # Find an online doctor of that specialty, else any doctor
    if matched_specialty:
        doc = next((d for d in db.doctors if d["specialty"] == matched_specialty and d["status"] == "online"), None)
        if not doc:
            doc = next((d for d in db.doctors if d["specialty"] == matched_specialty), None)
    if not matched_specialty or not doc:
        # fallback: first online doctor
        doc = next((d for d in db.doctors if d["status"] == "online"), db.doctors[0] if db.doctors else None)

    return doc


# ── Patient intake model ────────────────────────────────────
class PatientIntake(BaseModel):
    name: str
    age: int
    gender: str = "Not specified"
    contact: str = ""
    problem: str
    scan_type: str = "Chest X-Ray"


@router.post("/intake")
def intake_patient(body: PatientIntake):
    """Register new patient, auto-assign doctor, create imaging record, and trigger AI pipeline."""

    # 1. Create patient
    new_pid = f"PAT-{len(db.patients) + 1:03d}"
    patient = {
        "id": new_pid,
        "name": body.name,
        "age": body.age,
        "gender": body.gender,
        "contact": body.contact,
        "condition": body.problem,
        "status": "active",
        "created_at": db._now(),
    }
    db.patients.append(patient)

    # 2. Auto-assign doctor
    doctor = _auto_assign_doctor(body.problem)
    assigned_doctor = doctor if doctor else {"id": "UNASSIGNED", "name": "Unassigned", "specialty": "General"}

    # 3. Create imaging record
    new_iid = f"IMG-{len(db.imaging_records) + 1:03d}"
    imaging = {
        "id": new_iid,
        "patient_id": new_pid,
        "type": body.scan_type,
        "uploaded_at": db._now(),
        "status": "pending",
        "doctor_id": assigned_doctor["id"],
        "ai_analysis": None,
    }
    db.imaging_records.append(imaging)

    # 4. Auto-trigger AI pipeline
    analysis = run_full_pipeline(new_iid)

    # 5. Create a staff task for follow-up
    db.staff_tasks.append({
        "id": f"TASK-{len(db.staff_tasks) + 1:03d}",
        "title": f"Review AI report for {body.name} ({body.scan_type})",
        "assigned_to": assigned_doctor.get("name", "Unassigned"),
        "status": "pending",
        "priority": "high" if analysis.get("specialist_report", {}).get("severity") == "high" else "medium",
        "created_at": db._now(),
    })

    return {
        "success": True,
        "patient": patient,
        "assigned_doctor": assigned_doctor,
        "imaging": imaging,
        "analysis": analysis,
    }


# ── Existing endpoints ───────────────────────────────────────

@router.get("/tasks")
def list_tasks():
    return {"tasks": db.staff_tasks}


@router.post("/tasks")
def create_task(body: StaffTaskCreate):
    task = {
        "id": f"TASK-{len(db.staff_tasks) + 1:03d}",
        "title": body.title,
        "assigned_to": body.assigned_to,
        "status": "pending",
        "priority": body.priority,
        "created_at": db._now(),
    }
    db.staff_tasks.append(task)
    return {"success": True, "task": task}


@router.patch("/tasks/{task_id}/status")
def update_task_status(task_id: str, status: str):
    task = next((t for t in db.staff_tasks if t["id"] == task_id), None)
    if not task:
        return {"error": "Task not found"}
    task["status"] = status
    return {"success": True, "task": task}


@router.get("/dashboard")
def staff_dashboard():
    total_patients = len(db.patients)
    active_patients = len([p for p in db.patients if p["status"] == "active"])
    total_images = len(db.imaging_records)
    analyzed = len([i for i in db.imaging_records if i["status"] == "analyzed"])
    pending = len([i for i in db.imaging_records if i["status"] == "pending"])
    approved = len([i for i in db.imaging_records if i.get("status") == "approved"])
    tasks_pending = len([t for t in db.staff_tasks if t["status"] == "pending"])
    tasks_progress = len([t for t in db.staff_tasks if t["status"] == "in_progress"])
    tasks_done = len([t for t in db.staff_tasks if t["status"] == "completed"])
    critical = len([
        i for i in db.imaging_records
        if i.get("ai_analysis", {}) and (i.get("ai_analysis") or {}).get("specialist_report", {}).get("severity") == "high"
    ])
    pending_appointments = len([a for a in db.full_appointments if a["status"] == "pending"])
    total_scans = len(db.scans)
    return {
        "stats": {
            "total_patients": total_patients,
            "active_patients": active_patients,
            "total_images": total_images,
            "images_analyzed": analyzed,
            "images_pending": pending,
            "images_approved": approved,
            "images_critical": critical,
            "tasks_pending": tasks_pending,
            "tasks_in_progress": tasks_progress,
            "tasks_completed": tasks_done,
            "doctors_online": len([d for d in db.doctors if d["status"] == "online"]),
            "pending_appointments": pending_appointments,
            "total_scans": total_scans,
        }
    }


# ── Staff Notifications Feed ────────────────────────────────

@router.get("/notifications")
def staff_notifications():
    """Aggregate notifications relevant to staff: appointment requests, doctor updates, scan uploads."""
    feed = []

    # 1. Appointment requests from patients
    for apt in db.full_appointments:
        feed.append({
            "id": f"SFEED-APT-{apt['id']}",
            "type": "appointment_request",
            "title": f"📅 Appointment Request from {apt.get('patient_name', apt['patient_id'])}",
            "message": f"Requested {apt.get('doctor_name', apt['doctor_id'])} on {apt['appointment_date']} at {apt['time_slot']}. Reason: {apt['reason']}",
            "status": apt["status"],
            "reference_id": apt["id"],
            "created_at": apt["created_at"],
        })

    # 2. Doctor updates (approvals, reports, etc.)
    for notif in db.notifications:
        if notif["type"] in ("doctor_review", "new_scan", "ai_report_ready"):
            feed.append({
                "id": f"SFEED-DOC-{notif['id']}",
                "type": "doctor_update",
                "title": f"🩺 {notif['title']}",
                "message": notif["message"],
                "status": "info",
                "reference_id": notif.get("patient_id", ""),
                "created_at": notif["created_at"],
            })

    # 3. Recent audit events (scan uploads, prescription creation)
    for log in db.audit_logs[-20:]:
        if log["action"] in ("scan_uploaded", "dicom_uploaded", "prescription_created"):
            feed.append({
                "id": f"SFEED-AUDIT-{log['id']}",
                "type": "audit_event",
                "title": f"📋 {log['action'].replace('_', ' ').title()}",
                "message": f"{log['actor_name']}: {log['detail']}",
                "status": "info",
                "reference_id": log.get("scan_id", log.get("target", "")),
                "created_at": log["timestamp"],
            })

    # Sort by time (newest first)
    feed.sort(key=lambda x: x["created_at"], reverse=True)
    return {"notifications": feed}


# ── Staff: Approve appointment with date/time ────────────────

class StaffAppointmentApproval(BaseModel):
    appointment_date: Optional[str] = None
    time_slot: Optional[str] = None
    assigned_doctor_id: Optional[str] = None

@router.put("/appointments/{appointment_id}/approve-full")
def staff_approve_appointment_full(appointment_id: str, body: StaffAppointmentApproval):
    """Approve appointment with selected date, time, and optional doctor reassignment."""
    apt = next((a for a in db.full_appointments if a["id"] == appointment_id), None)
    if not apt:
        return {"error": "Appointment not found"}

    # Override date/time if staff selected new ones
    if body.appointment_date:
        apt["appointment_date"] = body.appointment_date
    if body.time_slot:
        apt["time_slot"] = body.time_slot
    if body.assigned_doctor_id:
        new_doc = next((d for d in db.doctors if d["id"] == body.assigned_doctor_id), None)
        if new_doc:
            apt["doctor_id"] = new_doc["id"]
            apt["doctor_name"] = new_doc["name"]
            apt["doctor_specialty"] = new_doc.get("specialty", "")

    apt["status"] = "approved"
    apt["approved_at"] = db._now()

    # Notify patient
    db.notifications.append({
        "id": f"NOTIF-{len(db.notifications) + 1:04d}",
        "patient_id": apt["patient_id"],
        "type": "appointment_approved",
        "title": "✅ Appointment Confirmed",
        "message": f"Your appointment with {apt['doctor_name']} has been confirmed for {apt['appointment_date']} at {apt['time_slot']}.",
        "severity": "low",
        "read": False,
        "created_at": db._now(),
    })

    return {"success": True, "appointment": apt}

