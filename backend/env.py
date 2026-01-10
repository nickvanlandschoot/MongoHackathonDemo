from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
GITHUB_PAT = os.getenv("GITHUB_PAT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
