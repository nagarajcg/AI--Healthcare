from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.translation_service import translate_report

router = APIRouter(tags=["Translation"])

class TranslateReportRequest(BaseModel):
    report_text: str
    target_language: str

@router.post("/translate-report")
def translate_report_endpoint(body: TranslateReportRequest):
    """
    Translates a medical report into the target language.
    """
    if not body.report_text:
        raise HTTPException(status_code=400, detail="Report text is required.")
    
    # If language is English or original, just return the text
    if body.target_language.lower() in ["english", "en"]:
        return {"translated_text": body.report_text}
        
    try:
        translated_text = translate_report(body.report_text, body.target_language)
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
