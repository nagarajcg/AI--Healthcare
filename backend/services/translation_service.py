import os
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Read API key from .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

api_key = os.environ.get("GEMINI_API_KEY")

# 2. Initialize Gemini model correctly
if api_key:
    genai.configure(api_key=api_key)
else:
    print("WARNING: GEMINI_API_KEY not found in backend/.env")

def translate_report(report_text: str, target_language: str) -> str:
    """Translate medical report into the target language using Gemini."""
    if not api_key:
        return "Error: Gemini API Key not configured."
        
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # 4. Force Gemini to reply only in target language
        prompt = f"Translate this medical report into {target_language} using simple patient-friendly language.\n\nMedical Report:\n{report_text}"
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Translation service error: {e}")
        raise e
