"""
Simulated AI Multi-Agent System for Medical Imaging Analysis.

Agents:
  1. Imaging Agent   – analyzes scan
  2. Doctor Agent    – sends result to doctor
  3. Patient Agent   – sends alerts to patient
  4. Hospital Agent  – stores data
"""

import random
import time
from datetime import datetime
from backend import database as db

# ── Anomaly pools per imaging type ───────────────────────────

_ANOMALIES = {
    "Chest X-Ray": [
        {"finding": "Mild cardiomegaly", "severity": "moderate", "confidence": 0.87, "body_part": "heart", "region": {"x": 38, "y": 30, "w": 24, "h": 28, "label": "Heart enlargement"}},
        {"finding": "No significant abnormalities detected", "severity": "normal", "confidence": 0.95, "body_part": "lungs", "region": None},
        {"finding": "Small pleural effusion (left)", "severity": "moderate", "confidence": 0.78, "body_part": "lungs", "region": {"x": 60, "y": 55, "w": 22, "h": 18, "label": "Pleural effusion"}},
        {"finding": "Possible early-stage pulmonary nodule", "severity": "high", "confidence": 0.72, "body_part": "lungs", "region": {"x": 30, "y": 25, "w": 14, "h": 14, "label": "Pulmonary nodule"}},
    ],
    "Brain MRI": [
        {"finding": "No intracranial abnormality", "severity": "normal", "confidence": 0.93, "body_part": "brain", "region": None},
        {"finding": "Minor white-matter hyperintensities", "severity": "low", "confidence": 0.81, "body_part": "brain", "region": {"x": 35, "y": 40, "w": 30, "h": 20, "label": "White-matter changes"}},
        {"finding": "Small meningioma detected (left frontal)", "severity": "high", "confidence": 0.76, "body_part": "brain", "region": {"x": 20, "y": 18, "w": 18, "h": 18, "label": "Meningioma"}},
    ],
    "Knee X-Ray": [
        {"finding": "Mild osteoarthritis changes", "severity": "moderate", "confidence": 0.88, "body_part": "bone", "region": {"x": 30, "y": 40, "w": 40, "h": 20, "label": "Osteoarthritis"}},
        {"finding": "No fracture or dislocation", "severity": "normal", "confidence": 0.96, "body_part": "bone", "region": None},
        {"finding": "Joint space narrowing (medial compartment)", "severity": "moderate", "confidence": 0.82, "body_part": "bone", "region": {"x": 35, "y": 45, "w": 30, "h": 15, "label": "Joint narrowing"}},
    ],
    "CT Scan": [
        {"finding": "Normal CT appearance", "severity": "normal", "confidence": 0.92, "body_part": "abdomen", "region": None},
        {"finding": "Small hepatic cyst", "severity": "low", "confidence": 0.84, "body_part": "abdomen", "region": {"x": 55, "y": 35, "w": 16, "h": 16, "label": "Hepatic cyst"}},
    ],
    "Dental X-Ray": [
        {"finding": "No dental pathology", "severity": "normal", "confidence": 0.94, "body_part": "dental", "region": None},
        {"finding": "Possible periapical abscess (lower molar)", "severity": "moderate", "confidence": 0.79, "body_part": "dental", "region": {"x": 60, "y": 60, "w": 15, "h": 15, "label": "Periapical abscess"}},
    ],
    "Ultrasound": [
        {"finding": "Normal sonographic findings", "severity": "normal", "confidence": 0.91, "body_part": "soft tissue", "region": None},
        {"finding": "Small fluid collection noted", "severity": "low", "confidence": 0.77, "body_part": "soft tissue", "region": {"x": 40, "y": 50, "w": 20, "h": 15, "label": "Fluid collection"}},
    ],
    "default": [
        {"finding": "Imaging reviewed – no critical findings", "severity": "normal", "confidence": 0.90, "body_part": "general", "region": None},
    ],
}


_SPECIALIST_TEMPLATES = {
    "normal": (
        "Clinical assessment indicates the imaging study is within normal limits. "
        "No acute pathology identified. Recommend routine follow-up as per standard protocol."
    ),
    "low": (
        "Minor incidental findings noted. These are unlikely to be clinically significant at this time. "
        "Suggest follow-up imaging in 6-12 months to monitor any changes."
    ),
    "moderate": (
        "Moderate findings warrant clinical attention. Further diagnostic workup may be indicated. "
        "Correlation with clinical symptoms and possibly additional imaging (CT/MRI) is recommended."
    ),
    "high": (
        "Significant abnormality detected that requires urgent clinical evaluation. "
        "Recommend immediate consultation with the relevant specialist and possible biopsy or advanced imaging."
    ),
}

_PATIENT_TEMPLATES = {
    "normal": (
        "Great news! Your scan looks normal. Your doctor will confirm the details at your next visit. "
        "No action is needed from your side right now."
    ),
    "low": (
        "Your scan showed a very small finding that is most likely nothing to worry about. "
        "Your doctor may suggest a follow-up scan in a few months just to be safe."
    ),
    "moderate": (
        "Your scan showed something that your doctor would like to look at more closely. "
        "This doesn't necessarily mean something is wrong — sometimes we just need more information. "
        "Your doctor will reach out to discuss next steps."
    ),
    "high": (
        "Your scan found something that your doctor wants to review right away. "
        "Please don't panic — your medical team is already preparing the best course of action for you. "
        "You should expect a call from your doctor's office very soon."
    ),
}

_COMPLIANCE_NOTES = [
    "HIPAA-compliant data handling verified.",
    "Image quality meets DICOM standards.",
    "Patient consent form on file — verified.",
    "Audit trail logged successfully.",
]


# ── Agent functions ──────────────────────────────────────────

def _log(agent_name: str, imaging_id: str, message: str, status: str = "completed"):
    entry = {
        "id": f"LOG-{len(db.agent_logs) + 1:03d}",
        "agent": agent_name,
        "imaging_id": imaging_id,
        "message": message,
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    db.agent_logs.append(entry)
    return entry


def imaging_agent(imaging_id: str):
    """Agent 1 — analyzes scan."""
    record = next((r for r in db.imaging_records if r["id"] == imaging_id), None)
    if not record:
        return {"error": "Imaging record not found"}

    pool = _ANOMALIES.get(record["type"], _ANOMALIES["default"])
    finding = random.choice(pool)

    _log("Imaging Agent", imaging_id, f"Anomaly scan complete: {finding['finding']} (confidence {finding['confidence']:.0%})")
    return finding


def doctor_agent(finding: dict):
    """Agent 2 — sends result to doctor."""
    severity = finding.get("severity", "normal")
    report = _SPECIALIST_TEMPLATES[severity]
    _log("Doctor Agent", finding.get("imaging_id", "N/A"), f"Clinical report generated (severity: {severity})")
    return {
        "clinical_report": report,
        "severity": severity,
        "recommendation": "Urgent follow-up" if severity == "high" else "Routine follow-up",
    }


def patient_agent(severity: str):
    """Agent 3 — sends alerts to patient."""
    summary = _PATIENT_TEMPLATES.get(severity, _PATIENT_TEMPLATES["normal"])
    _log("Patient Agent", "N/A", "Patient alert generated")
    return {"patient_alert": summary}


def hospital_agent(imaging_id: str):
    """Agent 4 — stores data."""
    notes = random.sample(_COMPLIANCE_NOTES, k=min(3, len(_COMPLIANCE_NOTES)))
    _log("Hospital Agent", imaging_id, "Data stored and compliance check passed")
    return {"stored": True, "notes": notes}


# ── Orchestrator ─────────────────────────────────────────────

def run_full_pipeline(imaging_id: str):
    """Run all four agents sequentially and return the combined result."""
    # Step 1 – Imaging Agent analyzes
    finding = imaging_agent(imaging_id)
    if "error" in finding:
        return finding
    finding["imaging_id"] = imaging_id

    # Step 2 – Doctor Agent receives report
    doctor_report = doctor_agent(finding)

    # Step 3 – Patient Agent receives alert
    patient = patient_agent(doctor_report["severity"])

    # Step 4 – Hospital Agent stores data
    hospital = hospital_agent(imaging_id)

    # Build composite result
    analysis = {
        "imaging_id": imaging_id,
        "imaging": finding,
        "doctor_report": doctor_report,
        "patient_alert": patient["patient_alert"],
        "hospital_storage": hospital,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }

    # Persist on imaging record
    record = next((r for r in db.imaging_records if r["id"] == imaging_id), None)
    if record:
        record["ai_analysis"] = analysis
        record["status"] = "analyzed"

        # Create notification for the patient
        patient_id = record.get("patient_id")
        if patient_id:
            # 1. AI Report notification
            db.notifications.append({
                "id": f"NOTIF-{len(db.notifications) + 1:03d}",
                "patient_id": patient_id,
                "type": "ai_report_ready",
                "title": "Your scan report is ready",
                "message": patient["patient_alert"],
                "severity": doctor_report["severity"],
                "read": False,
                "created_at": datetime.utcnow().isoformat() + "Z",
            })
            
            # 2. Medicine Reminder notification
            db.notifications.append({
                "id": f"NOTIF-{len(db.notifications) + 1:03d}",
                "patient_id": patient_id,
                "type": "medicine_reminder",
                "title": "💊 Medicine Reminder",
                "message": "Please remember to take your prescribed medication.",
                "severity": "low",
                "read": False,
                "created_at": datetime.utcnow().isoformat() + "Z",
            })
            
            # 3. Doctor Visit Reminder notification
            db.notifications.append({
                "id": f"NOTIF-{len(db.notifications) + 1:03d}",
                "patient_id": patient_id,
                "type": "doctor_visit",
                "title": "📅 Doctor Visit Reminder",
                "message": "A follow-up visit with your doctor has been suggested based on your latest scan.",
                "severity": doctor_report["severity"],
                "read": False,
                "created_at": datetime.utcnow().isoformat() + "Z",
            })

    return analysis
