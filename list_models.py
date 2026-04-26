from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    for model in client.models.list():
        if "flash" in model.name:
            print(model.name)
except Exception as e:
    print(f"Error: {e}")
