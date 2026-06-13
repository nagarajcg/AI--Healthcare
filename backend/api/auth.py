"""Patient Authentication API — JWT login for patients."""

import jwt
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from backend import database as db
from backend.models import PatientLogin

router = APIRouter(prefix="/api/patient", tags=["Patient Auth"])

JWT_SECRET = "healthai-secret-key-2026"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _create_token(patient_id: str) -> str:
    payload = {
        "sub": patient_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_patient(request: Request) -> dict:
    """Extract and validate JWT from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        patient_id = payload.get("sub")
        patient = next((p for p in db.patients if p["id"] == patient_id), None)
        if not patient:
            raise HTTPException(status_code=401, detail="Patient not found")
        return patient
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login")
def patient_login(body: PatientLogin):
    """Authenticate patient by ID only, return JWT."""
    patient = next((p for p in db.patients if p["id"] == body.patientId), None)
    if not patient:
        raise HTTPException(status_code=401, detail="Invalid Patient ID")

    token = _create_token(patient["id"])

    # Return safe patient data (no password hash)
    safe = {k: v for k, v in patient.items() if k != "password_hash"}

    return {
        "success": True,
        "token": token,
        "patient": safe,
    }


@router.get("/me")
def get_current(patient: dict = Depends(get_current_patient)):
    """Return current logged-in patient profile."""
    safe = {k: v for k, v in patient.items() if k != "password_hash"}
    notifs = [n for n in db.notifications if n.get("patient_id") == patient["id"]]
    rpts = [r for r in db.reports if r.get("patient_id") == patient["id"]]
    prescs = [p for p in db.prescriptions if p.get("patient_id") == patient["id"]]
    full_prescs = [p for p in db.full_prescriptions if p.get("patient_id") == patient["id"]]
    apts = [a for a in db.appointments if a.get("patient_id") == patient["id"]]
    images = [i for i in db.imaging_records if i.get("patient_id") == patient["id"]]
    return {
        "patient": safe,
        "notifications": notifs,
        "reports": rpts,
        "prescriptions": prescs,
        "full_prescriptions": full_prescs,
        "appointments": apts,
        "imaging_records": images,
    }
