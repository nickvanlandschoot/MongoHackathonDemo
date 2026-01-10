from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "intracesentinel")
GITHUB_PAT = os.getenv("GITHUB_PAT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
