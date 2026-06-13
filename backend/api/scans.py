"""
DICOM Scan Sharing API — Doctor uploads, Patient views & downloads.
Handles original DICOM file storage, metadata extraction, and preview generation.
"""

import os
import uuid
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from backend import database as db
from backend.services.dicom_service import extract_dicom_metadata, get_file_size_formatted
from backend.services.dicom_preview_service import generate_dicom_preview

router = APIRouter(tags=["DICOM Scans"])

# Storage for original DICOM files
DICOM_STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage", "dicom_uploads"
)
os.makedirs(DICOM_STORAGE_DIR, exist_ok=True)

# Legacy upload storage (for non-DICOM files)
LEGACY_STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage", "uploads"
)
os.makedirs(LEGACY_STORAGE_DIR, exist_ok=True)


def _now():
    return datetime.utcnow().isoformat() + "Z"


def _audit(action, actor, actor_name, target, target_name, detail, scan_id=None):
    """Create an audit log entry."""
    db.audit_logs.append({
        "id": f"AUDIT-{len(db.audit_logs) + 1:03d}",
        "action": action,
        "actor": actor,
        "actor_name": actor_name,
        "target": target,
        "target_name": target_name,
        "detail": detail,
        "scan_id": scan_id,
        "timestamp": _now(),
    })


# ═══════════════════════════════════════════════════════════════
#  DOCTOR: Upload DICOM Scan
# ═══════════════════════════════════════════════════════════════

@router.post("/api/doctor/upload-dicom")
async def upload_dicom(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    doctor_id: str = Form(...),
    scan_title: str = Form(...),
    scan_type: str = Form(...),
    body_part: str = Form(""),
    notes: str = Form(""),
):
    """Upload a DICOM (.dcm) file for a patient. Stores original file."""

    # Validate patient
    patient = next((p for p in db.patients if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Validate doctor
    doctor = next((d for d in db.doctors if d["id"] == doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Validate file type — DICOM or Image
    allowed = (".dcm", ".jpg", ".jpeg", ".png")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Only DICOM (.dcm) or Image (.jpg, .png) files are accepted. Received: '{ext}'"
        )

    # Create patient-specific directory
    patient_dir = os.path.join(DICOM_STORAGE_DIR, patient_id)
    os.makedirs(patient_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_") if file.filename else f"scan{ext}"
    
    if ext in (".jpg", ".jpeg", ".png"):
        # Save temporarily
        temp_name = f"temp_{timestamp}_{safe_name}"
        temp_path = os.path.join(patient_dir, temp_name)
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
            
        # Convert to DICOM
        from backend.services.jpg_to_dicom import jpg_to_dicom
        dcm_name = f"{timestamp}_{safe_name.rsplit('.', 1)[0]}.dcm"
        file_path = os.path.join(patient_dir, dcm_name)
        
        try:
            jpg_to_dicom(
                jpg_path=temp_path,
                output_path=file_path,
                patient_name=patient["name"],
                patient_id=patient_id,
                modality="DX",
                body_part=body_part or "UNKNOWN",
                study_description=scan_title,
                referring_physician=doctor["name"]
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        stored_name = dcm_name
        file.filename = safe_name.rsplit('.', 1)[0] + ".dcm"
        file_size = os.path.getsize(file_path)
    else:
        # Save original DICOM file
        stored_name = f"{timestamp}_{safe_name}"
        file_path = os.path.join(patient_dir, stored_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        file_size = len(content)

    file_size_formatted = get_file_size_formatted(file_path)

    # Extract DICOM metadata
    metadata = extract_dicom_metadata(file_path)

    # Generate study ID
    study_id = f"STD-{len(db.scans) + 1:04d}"

    # Create scan record
    scan_id = f"SCAN-{len(db.scans) + 1:03d}"
    scan = {
        "id": scan_id,
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "study_id": study_id,
        "scan_title": scan_title,
        "scan_type": scan_type,
        "body_part": body_part or metadata.get("body_part", ""),
        "notes": notes,
        "dicom_path": file_path,
        "file_name": file.filename,
        "stored_name": stored_name,
        "file_size": file_size,
        "file_size_formatted": file_size_formatted,
        "preview_type": "dicom",
        "metadata": metadata,
        "status": "uploaded",
        "created_at": _now(),
        # Legacy compat fields
        "file_path": file_path,
        "title": scan_title,
    }
    db.scans.append(scan)

    # Audit log
    _audit(
        "dicom_uploaded", doctor_id, doctor["name"],
        patient_id, patient["name"],
        f"Uploaded DICOM scan: {scan_title} ({scan_type}, {body_part})",
        scan_id
    )

    # Notify patient
    db.notifications.append({
        "id": f"NOTIF-{len(db.notifications) + 1:03d}",
        "patient_id": patient_id,
        "type": "new_scan",
        "title": "🔬 New DICOM Scan Uploaded",
        "message": f"{doctor['name']} has uploaded a new {scan_type} scan: {scan_title}. View it in My Medical Scans.",
        "severity": "normal",
        "read": False,
        "created_at": _now(),
    })

    return {"success": True, "scan": scan}


# ═══════════════════════════════════════════════════════════════
#  DOCTOR: Legacy Upload (any image type)
# ═══════════════════════════════════════════════════════════════

@router.post("/api/doctor/upload-scan")
async def upload_scan(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    doctor_id: str = Form(...),
    title: str = Form(...),
    scan_type: str = Form(...),
    body_part: str = Form(""),
    notes: str = Form(""),
):
    """Upload any scan file (legacy endpoint, accepts multiple formats)."""
    patient = next((p for p in db.patients if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = next((d for d in db.doctors if d["id"] == doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    allowed = (".dcm", ".jpg", ".jpeg", ".png", ".pdf")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported.")

    # If it's a DICOM file, redirect to the DICOM-specific endpoint logic
    if ext == ".dcm":
        # Reset file position
        await file.seek(0)
        return await upload_dicom(
            file=file, patient_id=patient_id, doctor_id=doctor_id,
            scan_title=title, scan_type=scan_type, body_part=body_part, notes=notes
        )

    patient_dir = os.path.join(LEGACY_STORAGE_DIR, patient_id)
    os.makedirs(patient_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_") if file.filename else f"scan{ext}"
    stored_name = f"{timestamp}_{safe_name}"
    file_path = os.path.join(patient_dir, stored_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    preview_type = "image" if ext in (".jpg", ".jpeg", ".png") else ("pdf" if ext == ".pdf" else "dicom")

    scan_id = f"SCAN-{len(db.scans) + 1:03d}"
    scan = {
        "id": scan_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "study_id": f"STD-{len(db.scans) + 1:04d}",
        "title": title,
        "scan_title": title,
        "scan_type": scan_type,
        "body_part": body_part,
        "notes": notes,
        "file_name": file.filename,
        "file_path": file_path,
        "dicom_path": "",
        "stored_name": stored_name,
        "preview_type": preview_type,
        "file_size": len(content),
        "file_size_formatted": get_file_size_formatted(file_path),
        "metadata": {},
        "status": "uploaded",
        "created_at": _now(),
    }
    db.scans.append(scan)

    _audit(
        "scan_uploaded", doctor_id, doctor["name"],
        patient_id, patient["name"],
        f"Uploaded {scan_type} scan: {title}", scan_id
    )

    db.notifications.append({
        "id": f"NOTIF-{len(db.notifications) + 1:03d}",
        "patient_id": patient_id,
        "type": "new_scan",
        "title": "🔬 New Scan Uploaded",
        "message": f"{doctor['name']} has uploaded a new {scan_type} scan: {title}.",
        "severity": "normal",
        "read": False,
        "created_at": _now(),
    })

    return {"success": True, "scan": scan}


# ═══════════════════════════════════════════════════════════════
#  DOCTOR: Get My Uploaded Scans
# ═══════════════════════════════════════════════════════════════

@router.get("/api/doctor/scans")
def doctor_all_scans():
    """Return all scans across all doctors."""
    result = []
    for s in db.scans:
        entry = dict(s)
        pt = next((p for p in db.patients if p["id"] == s["patient_id"]), None)
        doc = next((d for d in db.doctors if d["id"] == s["doctor_id"]), None)
        entry["patient_name"] = pt["name"] if pt else "Unknown"
        entry["doctor_name"] = doc["name"] if doc else "Unknown"
        result.append(entry)
    return {"scans": result}


@router.get("/api/doctor/my-scans/{doctor_id}")
def doctor_scans(doctor_id: str):
    """Return scans uploaded by a specific doctor."""
    scans = [s for s in db.scans if s["doctor_id"] == doctor_id]
    for s in scans:
        pt = next((p for p in db.patients if p["id"] == s["patient_id"]), None)
        s["patient_name"] = pt["name"] if pt else "Unknown"

    _audit(
        "doctor_viewed_scans", doctor_id,
        next((d["name"] for d in db.doctors if d["id"] == doctor_id), "Unknown"),
        doctor_id, "Scan List",
        f"Doctor viewed their uploaded scans list",
    )
    return {"scans": scans}


# ═══════════════════════════════════════════════════════════════
#  DOCTOR: View Scan Metadata
# ═══════════════════════════════════════════════════════════════

@router.get("/api/doctor/scan-metadata/{scan_id}")
def doctor_scan_metadata(scan_id: str):
    """Return DICOM metadata for a scan (doctor view)."""
    scan = next((s for s in db.scans if s["id"] == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    doc = next((d for d in db.doctors if d["id"] == scan["doctor_id"]), None)
    _audit(
        "doctor_viewed_metadata", scan["doctor_id"],
        doc["name"] if doc else "Unknown",
        scan_id, scan.get("scan_title", scan.get("title", "")),
        f"Doctor viewed metadata for: {scan.get('scan_title', scan.get('title', ''))}",
        scan_id
    )

    return {
        "scan": scan,
        "metadata": scan.get("metadata", {}),
    }


# ═══════════════════════════════════════════════════════════════
#  DOCTOR: Delete Scan
# ═══════════════════════════════════════════════════════════════

@router.delete("/api/doctor/scan/{scan_id}")
def delete_scan(scan_id: str):
    """Delete a scan record and its file."""
    scan = next((s for s in db.scans if s["id"] == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Delete file from disk
    file_path = scan.get("dicom_path") or scan.get("file_path", "")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    doc = next((d for d in db.doctors if d["id"] == scan["doctor_id"]), None)
    _audit(
        "scan_deleted", scan["doctor_id"],
        doc["name"] if doc else "Unknown",
        scan_id, scan.get("scan_title", scan.get("title", "")),
        f"Deleted scan: {scan.get('scan_title', scan.get('title', ''))}",
        scan_id
    )

    db.scans.remove(scan)
    return {"success": True, "message": "Scan deleted"}


# ═══════════════════════════════════════════════════════════════
#  PATIENT: View My Scans
# ═══════════════════════════════════════════════════════════════

@router.get("/api/patient/scans/{patient_id}")
def patient_scans(patient_id: str):
    """Return scans uploaded for a specific patient."""
    scans = [s for s in db.scans if s["patient_id"] == patient_id]
    for s in scans:
        doc = next((d for d in db.doctors if d["id"] == s["doctor_id"]), None)
        s["doctor_name"] = doc["name"] if doc else "Unknown"

    _audit(
        "patient_viewed_scans", patient_id,
        next((p["name"] for p in db.patients if p["id"] == patient_id), "Unknown"),
        patient_id, "My Scans",
        f"Patient viewed their medical scans",
    )

    return {"scans": scans}


# ═══════════════════════════════════════════════════════════════
#  PATIENT: View Scan Metadata
# ═══════════════════════════════════════════════════════════════

@router.get("/api/patient/scan-metadata/{scan_id}")
def patient_scan_metadata(scan_id: str):
    """Return DICOM metadata for a scan (patient view)."""
    scan = next((s for s in db.scans if s["id"] == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    pt = next((p for p in db.patients if p["id"] == scan["patient_id"]), None)
    _audit(
        "patient_viewed_metadata", scan["patient_id"],
        pt["name"] if pt else "Unknown",
        scan_id, scan.get("scan_title", scan.get("title", "")),
        f"Patient viewed metadata for: {scan.get('scan_title', scan.get('title', ''))}",
        scan_id
    )

    return {
        "scan": scan,
        "metadata": scan.get("metadata", {}),
    }


# ═══════════════════════════════════════════════════════════════
#  DOWNLOAD: Original DICOM File
# ═══════════════════════════════════════════════════════════════

@router.get("/api/patient/download-dicom/{scan_id}")
def download_dicom(scan_id: str):
    """Download the original unaltered DICOM file."""
    scan = next((s for s in db.scans if s["id"] == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    file_path = scan.get("dicom_path") or scan.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="DICOM file not found on disk")

    pt = next((p for p in db.patients if p["id"] == scan["patient_id"]), None)
    _audit(
        "dicom_downloaded", scan["patient_id"],
        pt["name"] if pt else "Unknown",
        scan_id, scan.get("scan_title", scan.get("title", "")),
        f"Downloaded DICOM file: {scan.get('scan_title', scan.get('title', ''))}",
        scan_id
    )

    return FileResponse(
        file_path,
        filename=scan.get("file_name", f"scan_{scan_id}.dcm"),
        media_type="application/dicom",
    )


# Legacy download endpoint
@router.get("/api/download-scan/{scan_id}")
def download_scan(scan_id: str):
    """Download any scan file (legacy endpoint)."""
    scan = next((s for s in db.scans if s["id"] == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    file_path = scan.get("dicom_path") or scan.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    _audit(
        "scan_downloaded", scan.get("patient_id", ""),
        next((p["name"] for p in db.patients if p["id"] == scan.get("patient_id")), "Unknown"),
        scan_id, scan.get("scan_title", scan.get("title", "")),
        f"Downloaded scan: {scan.get('scan_title', scan.get('title', ''))}",
        scan_id
    )

    return FileResponse(
        file_path,
        filename=scan.get("file_name", f"scan_{scan_id}"),
        media_type="application/octet-stream",
    )


# ═══════════════════════════════════════════════════════════════
#  PREVIEW: DICOM Preview Image
# ═══════════════════════════════════════════════════════════════

@router.get("/api/scan-preview/{scan_id}")
def scan_preview(scan_id: str):
    """Generate and return a preview PNG of a DICOM file."""
    scan = next((s for s in db.scans if s["id"] == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    file_path = scan.get("dicom_path") or scan.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(file_path)[1].lower()

    # For non-DICOM files, serve directly
    if ext in (".jpg", ".jpeg", ".png"):
        media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
        return FileResponse(file_path, media_type=media_types.get(ext, "image/jpeg"))

    if ext == ".pdf":
        return FileResponse(file_path, media_type="application/pdf")

    # For DICOM files, generate preview
    preview_path = generate_dicom_preview(file_path)
    if preview_path and os.path.exists(preview_path):
        return FileResponse(preview_path, media_type="image/png")

    raise HTTPException(status_code=500, detail="Could not generate preview")


# ═══════════════════════════════════════════════════════════════
#  AUDIT LOGS
# ═══════════════════════════════════════════════════════════════

@router.get("/api/audit-logs")
def get_audit_logs():
    """Return all audit logs."""
    return {"logs": db.audit_logs}


@router.get("/api/audit-logs/{scan_id}")
def get_scan_audit(scan_id: str):
    """Return audit logs for a specific scan."""
    logs = [l for l in db.audit_logs if l.get("scan_id") == scan_id]
    return {"logs": logs}
