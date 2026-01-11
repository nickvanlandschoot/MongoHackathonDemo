from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "intracesentinel")
GITHUB_PAT = os.getenv("GITHUB_PAT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# AI Analysis Queue Configuration
AI_ANALYSIS_DELAY = float(os.getenv("AI_ANALYSIS_DELAY", "5.0"))  # Seconds between queued AI calls
AI_PRIORITY_THRESHOLD = float(os.getenv("AI_PRIORITY_THRESHOLD", "70.0"))  # Risk score for immediate processing
