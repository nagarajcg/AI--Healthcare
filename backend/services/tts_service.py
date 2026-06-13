import os
import hashlib
from gtts import gTTS

# Setup storage path
AUDIO_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "audio")
os.makedirs(AUDIO_STORAGE_DIR, exist_ok=True)

# Language mapping from user names to gTTS codes
LANGUAGE_MAP = {
    "English": "en",
    "Hindi": "hi",
    "Kannada": "kn",
    "Telugu": "te",
    "Tamil": "ta"
}

def generate_tts(text: str, language: str) -> str:
    """
    Generates a TTS audio file and returns the filename.
    Uses md5 hash of text and language to cache generated audio.
    """
    if not text.strip():
        raise ValueError("Text cannot be empty")
        
    gtts_lang = LANGUAGE_MAP.get(language, "en")
    
    # Create a unique filename based on hash to avoid regenerating identical TTS
    content_hash = hashlib.md5(f"{gtts_lang}_{text}".encode("utf-8")).hexdigest()
    filename = f"tts_{content_hash}.mp3"
    filepath = os.path.join(AUDIO_STORAGE_DIR, filename)
    
    # If file doesn't exist, generate and save it
    if not os.path.exists(filepath):
        try:
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            tts.save(filepath)
        except Exception as e:
            raise Exception(f"TTS Generation failed: {str(e)}")
            
    return filename
