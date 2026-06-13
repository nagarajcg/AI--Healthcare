import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.services.tts_service import generate_tts, AUDIO_STORAGE_DIR

router = APIRouter(prefix="/api/tts", tags=["TTS"])

class TTSRequest(BaseModel):
    text: str
    language: str

@router.post("/generate-audio")
async def generate_audio(request: TTSRequest):
    try:
        filename = generate_tts(request.text, request.language)
        return {"audio_url": f"/api/tts/audio/{filename}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice generation failed: {str(e)}")

@router.get("/audio/{filename}")
async def get_audio(filename: str):
    filepath = os.path.join(AUDIO_STORAGE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(filepath, media_type="audio/mpeg")
