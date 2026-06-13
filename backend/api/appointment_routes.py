"""
Appointment Booking & Staff Approval API.

Routes:
  POST  /appointments/book                     — patient books appointment
  GET   /staff/appointments                    — staff views all requests
  PUT   /staff/appointments/{id}/approve       — approve appointment
  PUT   /staff/appointments/{id}/reject        — reject appointment
  GET   /appointments/doctors                  — list available doctors
  GET   /appointments/patient/{patient_id}     — patient's own appointments
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend import database as db
from backend.services.firebase_notification_service import (
    notify_staff_new_appointment,
    notify_patient_appointment_approved,
    notify_patient_appointment_rejected,
    notify_doctor_new_appointment,
)

router = APIRouter(prefix="/api", tags=["Appointments"])


# ── Pydantic models ─────────────────────────────────────────────────────────

class AppointmentBook(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_date: str          # ISO date string e.g. "2026-05-10"
    time_slot: str                 # e.g. "10:00 AM"
    reason: str
    scan_requirement: str = "None" # None | X-Ray | CT Scan | MRI | Ultrasound


class AppointmentApprove(BaseModel):
    assigned_doctor_id: Optional[str] = None
    confirmed_date: Optional[str] = None
    confirmed_time: Optional[str] = None


# ── Helper ──────────────────────────────────────────────────────────────────

def _apt_id():
    return f"FAPT-{len(db.full_appointments) + 1:04d}"


def _audit(action: str, actor: str, actor_name: str, target: str, target_name: str, detail: str):
    db.audit_logs.append({
        "id": f"AUDIT-{len(db.audit_logs) + 1:04d}",
        "action": action,
        "actor": actor,
        "actor_name": actor_name,
        "target": target,
        "target_name": target_name,
        "detail": detail,
        "timestamp": db._now(),
    })


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/appointments/doctors")
def list_doctors_for_booking():
    """Return list of all doctors for appointment booking dropdown."""
    return {"doctors": db.doctors}


@router.get("/appointments/patient/{patient_id}")
def get_patient_appointments(patient_id: str):
    """Return all full appointments for a given patient."""
    apts = [a for a in db.full_appointments if a["patient_id"] == patient_id]
    # Enrich with doctor name
    doc_map = {d["id"]: d for d in db.doctors}
    for a in apts:
        doc = doc_map.get(a["doctor_id"], {})
        a["doctor_name"] = doc.get("name", "Unknown")
        a["doctor_specialty"] = doc.get("specialty", "")
    return {"appointments": apts}


@router.get("/appointments/available-slots/{doctor_id}")
def get_available_slots(doctor_id: str, date: str):
    """
    Return available time slots for a doctor on a specific date.
    Checks doctor schedule and filters out already booked slots.
    """
    import datetime
    # 1. Get doctor schedule
    schedule = next((s for s in db.doctor_availability if s["doctor_id"] == doctor_id), None)
    if not schedule:
        return {"slots": []}

    # 2. Check if date is an available day of the week
    try:
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        day_name = dt.strftime("%A")
        if day_name not in schedule["available_days"]:
            return {"slots": [], "reason": f"Doctor does not work on {day_name}s"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # 3. Get all slots
    all_slots = list(schedule["time_slots"])

    # 4. Filter out booked slots for this doctor on this date
    booked_slots = [
        a["time_slot"] for a in db.full_appointments 
        if a["doctor_id"] == doctor_id and a["appointment_date"] == date and a["status"] != "rejected"
    ]
    
    available_slots = [s for s in all_slots if s not in booked_slots]

    return {"slots": available_slots}


@router.post("/appointments/book")
def book_appointment(body: AppointmentBook):
    """Patient books an appointment request (status starts as 'pending')."""
    # Validate patient
    patient = next((p for p in db.patients if p["id"] == body.patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Validate doctor
    doctor = next((d for d in db.doctors if d["id"] == body.doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    appointment = {
        "id": _apt_id(),
        "patient_id": body.patient_id,
        "patient_name": patient["name"],
        "doctor_id": body.doctor_id,
        "doctor_name": doctor["name"],
        "doctor_specialty": doctor.get("specialty", ""),
        "appointment_date": body.appointment_date,
        "time_slot": body.time_slot,
        "reason": body.reason,
        "scan_requirement": body.scan_requirement,
        "status": "pending",
        "created_at": db._now(),
    }
    db.full_appointments.append(appointment)

    # Add a notification for the patient dashboard
    db.notifications.append({
        "id": f"NOTIF-{len(db.notifications) + 1:04d}",
        "patient_id": body.patient_id,
        "type": "appointment_booked",
        "title": "📅 Appointment Request Submitted",
        "message": f"Your appointment request with {doctor['name']} on {body.appointment_date} at {body.time_slot} is pending approval.",
        "severity": "normal",
        "read": False,
        "created_at": db._now(),
    })

    _audit(
        "appointment_booked",
        body.patient_id, patient["name"],
        body.doctor_id, doctor["name"],
        f"Appointment booked for {body.appointment_date} {body.time_slot}",
    )

    # Firebase notification → staff
    notify_staff_new_appointment(patient["name"], appointment["id"])

    return {"success": True, "appointment": appointment}


@router.get("/staff/appointments")
def list_all_appointments():
    """Staff: list all appointment requests with enriched data."""
    apts = list(db.full_appointments)
    doc_map = {d["id"]: d for d in db.doctors}
    pat_map = {p["id"]: p for p in db.patients}
    for a in apts:
        doc = doc_map.get(a["doctor_id"], {})
        pat = pat_map.get(a["patient_id"], {})
        a["doctor_name"] = doc.get("name", a.get("doctor_name", "Unknown"))
        a["doctor_specialty"] = doc.get("specialty", "")
        a["patient_name"] = pat.get("name", a.get("patient_name", "Unknown"))
    return {"appointments": apts}


@router.put("/staff/appointments/{appointment_id}/approve")
def approve_appointment(appointment_id: str, body: AppointmentApprove = None):
    """Staff approves an appointment, optionally reassigning doctor."""
    apt = next((a for a in db.full_appointments if a["id"] == appointment_id), None)
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if body:
        if body.assigned_doctor_id:
            new_doc = next((d for d in db.doctors if d["id"] == body.assigned_doctor_id), None)
            if new_doc:
                apt["doctor_id"] = new_doc["id"]
                apt["doctor_name"] = new_doc["name"]
                apt["doctor_specialty"] = new_doc.get("specialty", "")
        
        if body.confirmed_date:
            apt["appointment_date"] = body.confirmed_date
        if body.confirmed_time:
            apt["time_slot"] = body.confirmed_time

    apt["status"] = "approved"
    apt["approved_at"] = db._now()

    _audit(
        "appointment_approved",
        "STAFF", "Staff",
        apt["patient_id"], apt["patient_name"],
        f"Approved appointment {appointment_id} with {apt['doctor_name']}",
    )

    # Firebase notifications
    notify_patient_appointment_approved(
        apt["patient_id"], apt["doctor_name"], apt["appointment_date"]
    )
    notify_doctor_new_appointment(
        apt["doctor_id"], apt["patient_name"], apt["appointment_date"]
    )

    # In-app notification for patient
    db.notifications.append({
        "id": f"NOTIF-{len(db.notifications) + 1:04d}",
        "patient_id": apt["patient_id"],
        "type": "appointment_approved",
        "title": "✅ Appointment Approved",
        "message": f"Your appointment with {apt['doctor_name']} on {apt['appointment_date']} at {apt['time_slot']} has been approved.",
        "severity": "low",
        "read": False,
        "created_at": db._now(),
    })

    return {"success": True, "appointment": apt}


@router.put("/staff/appointments/{appointment_id}/reject")
def reject_appointment(appointment_id: str):
    """Staff rejects an appointment."""
    apt = next((a for a in db.full_appointments if a["id"] == appointment_id), None)
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    apt["status"] = "rejected"
    apt["rejected_at"] = db._now()

    _audit(
        "appointment_rejected",
        "STAFF", "Staff",
        apt["patient_id"], apt.get("patient_name", apt["patient_id"]),
        f"Rejected appointment {appointment_id}",
    )

    notify_patient_appointment_rejected(apt["patient_id"])

    # In-app notification for patient
    db.notifications.append({
        "id": f"NOTIF-{len(db.notifications) + 1:04d}",
        "patient_id": apt["patient_id"],
        "type": "appointment_rejected",
        "title": "❌ Appointment Not Approved",
        "message": "Your appointment request was not approved. Please contact the hospital for rescheduling.",
        "severity": "moderate",
        "read": False,
        "created_at": db._now(),
    })

    return {"success": True, "appointment": apt}
