"""
Doctor Prescription System + Patient Prescription View + PDF Download.

Routes:
  POST  /doctor/prescription                        — doctor creates prescription
  GET   /doctor/prescriptions/{doctor_id}           — doctor views their prescriptions
  GET   /patient/full-prescriptions/{patient_id}    — patient views their prescriptions
  GET   /patient/download-prescription/{id}         — PDF download
"""

import io
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from backend import database as db
from backend.services.firebase_notification_service import notify_patient_prescription_ready

router = APIRouter(prefix="/api", tags=["Prescriptions"])


# ── Pydantic models ─────────────────────────────────────────────────────────

from pydantic import BaseModel, field_validator
import re

class PrescriptionCreate(BaseModel):
    doctor_id: str
    patient_id: str
    diagnosis: str
    medicines: str
    dosage: str
    instructions: str
    test_recommendations: Optional[str] = ""
    follow_up_date: Optional[str] = None

    @field_validator("follow_up_date")
    @classmethod
    def validate_date_format(cls, v):
        if v and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("follow_up_date must be in YYYY-MM-DD format")
        return v


# ── Helpers ─────────────────────────────────────────────────────────────────

def _prx_id():
    return f"PRX-{len(db.full_prescriptions) + 1:04d}"


def _audit(action, actor, actor_name, target, target_name, detail):
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


def _generate_prescription_pdf(prx: dict) -> bytes:
    """Generate a styled prescription PDF using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # ── Header ──────────────────────────────────────────
    c.setFillColor(HexColor("#0a0e1a"))
    c.rect(0, h - 90, w, 90, fill=1, stroke=0)

    c.setFillColor(HexColor("#06b6d4"))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(30, h - 45, "HealthAI")

    c.setFillColor(HexColor("#94a3b8"))
    c.setFont("Helvetica", 10)
    c.drawString(30, h - 65, "AI Healthcare Imaging Data Regulator")
    c.drawRightString(w - 30, h - 45, "PRESCRIPTION")
    c.drawRightString(w - 30, h - 65, f"ID: {prx['id']}")

    # ── Title ────────────────────────────────────────────
    y = h - 120
    c.setFillColor(HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, y, "Medical Prescription")

    # ── Patient & Doctor info ────────────────────────────
    y -= 30
    c.setStrokeColor(HexColor("#e2e8f0"))
    c.line(30, y, w - 30, y)
    y -= 20

    def row(label, val, ypos):
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(HexColor("#64748b"))
        c.drawString(30, ypos, f"{label}:")
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#1e293b"))
        c.drawString(160, ypos, str(val))
        return ypos - 18

    # Patient info
    patient = next((p for p in db.patients if p["id"] == prx.get("patient_id")), {})
    doctor = next((d for d in db.doctors if d["id"] == prx.get("doctor_id")), {})

    y = row("Patient Name", patient.get("name", prx.get("patient_id", "N/A")), y)
    y = row("Patient ID", prx.get("patient_id", "N/A"), y)
    y = row("Age / Gender", f"{patient.get('age', 'N/A')} / {patient.get('gender', 'N/A')}", y)
    y = row("Prescribing Doctor", doctor.get("name", prx.get("doctor_id", "N/A")), y)
    y = row("Specialty", doctor.get("specialty", "N/A"), y)
    y = row("Date Issued", prx.get("created_at", "")[:10], y)
    if prx.get("follow_up_date"):
        y = row("Follow-up Date", prx["follow_up_date"], y)

    # ── Divider ──────────────────────────────────────────
    y -= 10
    c.line(30, y, w - 30, y)
    y -= 20

    # ── Diagnosis ────────────────────────────────────────
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(HexColor("#0f172a"))
    c.drawString(30, y, "Diagnosis")
    y -= 18
    c.setFont("Helvetica", 11)
    c.setFillColor(HexColor("#334155"))
    c.drawString(30, y, prx.get("diagnosis", "N/A"))
    y -= 30

    # ── Medicines ────────────────────────────────────────
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(HexColor("#0f172a"))
    c.drawString(30, y, "Medicines Prescribed")
    y -= 18
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#334155"))
    medicines = prx.get("medicines", "N/A")
    for med in medicines.split(","):
        med = med.strip()
        if med:
            c.drawString(40, y, f"• {med}")
            y -= 16
    y -= 10

    # ── Dosage ───────────────────────────────────────────
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(HexColor("#0f172a"))
    c.drawString(30, y, "Dosage Instructions")
    y -= 18
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#334155"))

    words = prx.get("dosage", "").split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if c.stringWidth(test, "Helvetica", 10) > w - 80:
            c.drawString(30, y, line)
            y -= 16
            line = word
        else:
            line = test
    if line:
        c.drawString(30, y, line)
        y -= 20

    # ── Instructions ─────────────────────────────────────
    if prx.get("instructions"):
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(HexColor("#0f172a"))
        c.drawString(30, y, "Special Instructions")
        y -= 18
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#334155"))
        words = prx["instructions"].split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if c.stringWidth(test, "Helvetica", 10) > w - 80:
                c.drawString(30, y, line)
                y -= 16
                line = word
            else:
                line = test
        if line:
            c.drawString(30, y, line)
            y -= 16

    # ── Doctor signature line ─────────────────────────────
    y -= 30
    c.line(30, y, 200, y)
    y -= 14
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#64748b"))
    c.drawString(30, y, f"Dr. {doctor.get('name', '')} — {doctor.get('specialty', '')}")

    # ── Footer ───────────────────────────────────────────
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#94a3b8"))
    c.drawString(30, 30, f"Generated by HealthAI System — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    c.drawRightString(w - 30, 30, "CONFIDENTIAL — For authorized use only")

    c.save()
    buf.seek(0)
    return buf.read()


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/doctor/prescriptions/create")
def create_prescription(body: PrescriptionCreate):
    """Doctor creates a prescription for a patient."""
    try:
        patient = next((p for p in db.patients if p["id"] == body.patient_id), None)
        if not patient:
            return {"success": False, "error": "Patient not found"}

        doctor = next((d for d in db.doctors if d["id"] == body.doctor_id), None)
        if not doctor:
            return {"success": False, "error": "Doctor not found"}

        prx = {
            "id": _prx_id(),
            "doctor_id": body.doctor_id,
            "doctor_name": doctor["name"],
            "doctor_specialty": doctor.get("specialty", ""),
            "patient_id": body.patient_id,
            "patient_name": patient["name"],
            "diagnosis": body.diagnosis,
            "medicines": body.medicines,
            "dosage": body.dosage,
            "instructions": body.instructions,
            "test_recommendations": body.test_recommendations or "",
            "follow_up_date": body.follow_up_date,
            "status": "active",
            "created_at": db._now(),
        }
        db.full_prescriptions.append(prx)

        _audit(
            "prescription_created",
            body.doctor_id, doctor["name"],
            body.patient_id, patient["name"],
            f"Prescription {prx['id']} created: {body.diagnosis}",
        )

        # Notify patient
        db.notifications.append({
            "id": f"NOTIF-{len(db.notifications) + 1:04d}",
            "patient_id": body.patient_id,
            "type": "prescription_ready",
            "title": "💊 New Prescription Available",
            "message": f"Dr. {doctor['name']} has issued a prescription for you. Diagnosis: {body.diagnosis}",
            "severity": "low",
            "read": False,
            "created_at": db._now(),
        })

        # Notify staff
        db.notifications.append({
            "id": f"NOTIF-{len(db.notifications) + 1:04d}",
            "type": "new_prescription_staff",
            "title": "📋 Prescription Issued",
            "message": f"Dr. {doctor['name']} issued a prescription for {patient['name']} (ID: {patient['id']}).",
            "severity": "low",
            "read": False,
            "created_at": db._now(),
        })

        notify_patient_prescription_ready(body.patient_id, doctor["name"])

        return {"success": True, "message": "Prescription created", "prescription": prx}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/doctor/prescriptions/{doctor_id}")
def doctor_prescriptions(doctor_id: str):
    """Return all prescriptions created by a doctor."""
    prxs = [p for p in db.full_prescriptions if p["doctor_id"] == doctor_id]
    return {"prescriptions": prxs}


@router.get("/patient/full-prescriptions/{patient_id}")
def patient_prescriptions(patient_id: str):
    """Return all full prescriptions for a patient."""
    prxs = [p for p in db.full_prescriptions if p["patient_id"] == patient_id]
    return {"prescriptions": prxs}


@router.get("/patient/view-prescription/{prescription_id}")
def view_prescription(prescription_id: str):
    """Return a single prescription and log the view."""
    prx = next((p for p in db.full_prescriptions if p["id"] == prescription_id), None)
    if not prx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    _audit(
        "prescription_viewed",
        prx["patient_id"], prx.get("patient_name", prx["patient_id"]),
        prx["doctor_id"], prx.get("doctor_name", prx["doctor_id"]),
        f"Patient viewed prescription {prescription_id}",
    )
    return {"prescription": prx}


@router.get("/patient/download-prescription/{prescription_id}")
def download_prescription(prescription_id: str):
    """Generate and stream a prescription PDF."""
    prx = next((p for p in db.full_prescriptions if p["id"] == prescription_id), None)
    if not prx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    _audit(
        "prescription_downloaded",
        prx["patient_id"], prx.get("patient_name", prx["patient_id"]),
        prx["doctor_id"], prx.get("doctor_name", prx["doctor_id"]),
        f"Downloaded prescription {prescription_id}",
    )

    pdf_bytes = _generate_prescription_pdf(prx)
    filename = f"Prescription_{prescription_id}_{prx.get('patient_name', 'patient').replace(' ', '_')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
