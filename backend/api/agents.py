"""AI Agent API routes."""

from fastapi import APIRouter
from backend import database as db
from backend.models import AgentAnalysisRequest, ImagingUpload
from backend.services.agents import run_full_pipeline

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.post("/analyze")
def trigger_analysis(body: AgentAnalysisRequest):
    result = run_full_pipeline(body.imaging_id)
    return {"analysis": result}


@router.get("/logs")
def get_agent_logs():
    return {"logs": db.agent_logs}


@router.get("/logs/{imaging_id}")
def get_logs_for_image(imaging_id: str):
    logs = [l for l in db.agent_logs if l.get("imaging_id") == imaging_id]
    return {"logs": logs}


@router.post("/imaging")
def upload_imaging(body: ImagingUpload):
    new_id = f"IMG-{len(db.imaging_records) + 1:03d}"
    record = {
        "id": new_id,
        "patient_id": body.patient_id,
        "type": body.type,
        "uploaded_at": db._now(),
        "status": "pending",
        "doctor_id": body.doctor_id,
        "ai_analysis": None,
    }
    db.imaging_records.append(record)
    
    # Analyze image
    analysis = run_full_pipeline(new_id)
    
    # Map to requested output
    screener_finding = analysis.get("screener", {}).get("finding", "Unknown")
    severity = analysis.get("specialist_report", {}).get("severity", "normal")
    risk_map = {"normal": "Low", "low": "Low", "moderate": "Medium", "high": "High"}
    
    return {
        "result": screener_finding,
        "risk": risk_map.get(severity, "Unknown"),
        "explanation": analysis.get("patient_summary", ""),
        "success": True,
        "imaging": record
    }


@router.get("/imaging")
def list_imaging():
    return {"imaging_records": db.imaging_records}


@router.get("/imaging/{imaging_id}")
def get_imaging(imaging_id: str):
    record = next((r for r in db.imaging_records if r["id"] == imaging_id), None)
    if not record:
        return {"error": "Imaging record not found"}
    return {"imaging": record}
