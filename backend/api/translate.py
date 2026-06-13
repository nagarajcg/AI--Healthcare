"""AI-powered medical report translation and simplification."""

import os
import google.generativeai as genai
from fastapi import APIRouter
from backend.models import TranslateRequest
from backend import database as db
from datetime import datetime

router = APIRouter(prefix="/api/reports", tags=["Translation"])

# Initialize Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    # Fallback to a placeholder or print a warning
    print("WARNING: GEMINI_API_KEY not found in environment.")

def _simplify_text(text: str) -> str:
    """Replace medical jargon with patient-friendly language using Gemini."""
    if not api_key:
        return text  # Fallback
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You are a helpful medical assistant. "
            "Please simplify the following medical text so that a patient without medical training can easily understand it. "
            "Replace complex medical jargon with simple, patient-friendly explanations, but keep the original medical meaning intact. "
            "Return ONLY the simplified text, without any conversational filler or introductions.\n\n"
            f"Medical Text:\n{text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Simplification error: {e}")
        return text


def _translate_text(text: str, language: str) -> str:
    """Translate text to the target language using Gemini."""
    if language.lower() == "english":
        return text
        
    if not api_key:
        return text  # Fallback

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"Translate this medical report into {language}. "
            "Keep the medical meaning correct. Make it easy for patient understanding. "
            "Return ONLY the translated text, do not return English unless the target language is English.\n\n"
            f"Text to translate:\n{text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text


@router.post("/translate")
def translate_report(body: TranslateRequest):
    """Simplify medical text and translate to selected language."""
    text_to_translate = body.text
    if body.report_id:
        report = next((r for r in db.reports if r["id"] == body.report_id), None)
        if report and not text_to_translate:
            text_to_translate = report.get("summary", report.get("reportName", ""))
    
    if not text_to_translate:
        return {"error": "No text to translate provided."}

    # Check if translation already exists in DB
    if body.report_id:
        existing = next(
            (t for t in db.translated_reports 
             if t["report_id"] == body.report_id and t["language"] == body.target_language), 
            None
        )
        if existing:
            return {
                "original": existing["original_text"],
                "simplified": existing["simplified_text"],
                "translated": existing["translated_text"],
                "language": body.target_language,
            }

    # Flow: Original -> Simplify -> Translate
    simplified = _simplify_text(text_to_translate)
    translated = _translate_text(simplified, body.target_language)

    # Store in database if report_id provided
    if body.report_id:
        new_translation = {
            "id": f"TRANS-{len(db.translated_reports) + 1:03d}",
            "report_id": body.report_id,
            "language": body.target_language,
            "original_text": text_to_translate,
            "simplified_text": simplified,
            "translated_text": translated,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        db.translated_reports.append(new_translation)

    return {
        "original": text_to_translate,
        "simplified": simplified,
        "translated": translated,
        "language": body.target_language,
    }
