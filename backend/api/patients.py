"""Patient API routes."""

from fastapi import APIRouter
from backend import database as db
from backend.models import PatientCreate, NotificationRead

router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.get("/")
def list_patients():
    return {"patients": db.patients}


@router.get("/{patient_id}")
def get_patient(patient_id: str):
    pt = next((p for p in db.patients if p["id"] == patient_id), None)
    if not pt:
        return {"error": "Patient not found"}
    images = [i for i in db.imaging_records if i["patient_id"] == patient_id]
    notifs = [n for n in db.notifications if n.get("patient_id") == patient_id]
    return {"patient": pt, "imaging_records": images, "notifications": notifs}


@router.post("/")
def create_patient(body: PatientCreate):
    new_id = f"PAT-{len(db.patients) + 1:03d}"
    patient = {
        "id": new_id,
        "name": body.name,
        "age": body.age,
        "gender": body.gender,
        "contact": body.contact,
        "condition": body.condition,
        "status": "active",
        "created_at": db._now(),
    }
    db.patients.append(patient)
    return {"success": True, "patient": patient}


@router.get("/{patient_id}/notifications")
def patient_notifications(patient_id: str):
    notifs = [n for n in db.notifications if n.get("patient_id") == patient_id]
    return {"notifications": notifs}


@router.post("/notifications/read")
def mark_notification_read(body: NotificationRead):
    notif = next((n for n in db.notifications if n["id"] == body.notification_id), None)
    if not notif:
        return {"error": "Notification not found"}
    notif["read"] = True
    return {"success": True}
