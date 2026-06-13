"""Doctor API routes."""

from fastapi import APIRouter
from backend import database as db
from backend.models import DoctorApproval

router = APIRouter(prefix="/api/doctors", tags=["Doctors"])


@router.get("/")
def list_doctors():
    """Fetch all active doctors from database with requested fields."""
    active_doctors = [d for d in db.doctors if d.get("status") == "active"]
    
    # Enrich with availability
    result = []
    for d in active_doctors:
        availability = next((a for a in db.doctor_availability if a["doctor_id"] == d["id"]), None)
        result.append({
            "id": d["id"],
            "name": d["name"],
            "specialization": d["specialty"],
            "availability": availability["available_days"] if availability else ["Monday - Friday"],
            "status": d["status"]
        })
    
    if not result:
        # Fallback if no doctors (though seeded above)
        return {"doctors": [
            {"id": "DOC-001", "name": "Dr. Anika Verma", "specialization": "Radiology", "availability": ["Monday", "Wednesday", "Friday"]},
            {"id": "DOC-002", "name": "Dr. Rajesh Kumar", "specialization": "Cardiology", "availability": ["Tuesday", "Thursday"]},
            {"id": "DOC-003", "name": "Dr. Priya Sharma", "specialization": "Neurology", "availability": ["Monday", "Wednesday"]}
        ]}

    return {"doctors": result}


@router.get("/{doctor_id}")
def get_doctor(doctor_id: str):
    doc = next((d for d in db.doctors if d["id"] == doctor_id), None)
    if not doc:
        return {"error": "Doctor not found"}
    # attach assigned images
    images = [i for i in db.imaging_records if i.get("doctor_id") == doctor_id]
    return {"doctor": doc, "assigned_images": images}


@router.get("/{doctor_id}/patients")
def doctor_patients(doctor_id: str):
    image_patient_ids = {
        i["patient_id"]
        for i in db.imaging_records
        if i.get("doctor_id") == doctor_id
    }
    pts = [p for p in db.patients if p["id"] in image_patient_ids]
    return {"patients": pts}


@router.post("/approve")
def approve_report(body: DoctorApproval):
    record = next((r for r in db.imaging_records if r["id"] == body.imaging_id), None)
    if not record:
        return {"error": "Imaging record not found"}
    record["doctor_approved"] = body.approved
    record["doctor_notes"] = body.doctor_notes
    record["status"] = "approved" if body.approved else "rejected"

    # Notify patient
    db.notifications.append({
        "id": f"NOTIF-{len(db.notifications) + 1:03d}",
        "patient_id": record["patient_id"],
        "type": "doctor_review",
        "title": "Doctor reviewed your report",
        "message": f"Your report has been {'approved' if body.approved else 'flagged for further review'} by your doctor."
                   + (f" Doctor's note: {body.doctor_notes}" if body.doctor_notes else ""),
        "severity": "normal",
        "read": False,
        "created_at": db._now(),
    })
    return {"success": True, "record": record}
