from dotenv import load_dotenv
from groq import AsyncGroq
import os

load_dotenv()

groq_client = AsyncGroq(
    api_key=os.getenv("GROQ_API_KEY")
)