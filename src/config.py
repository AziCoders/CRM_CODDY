import os
from pathlib import Path
from dotenv import load_dotenv
from notion_client import AsyncClient

# 1. Load Environment Variables once
load_dotenv()

# 2. Define Root Directory Robustly
# Assuming config.py is in src/config.py, so root is one level up
ROOT_DIR = Path(__file__).resolve().parent.parent

# 3. Define Cities
CITIES = ["Malgobek", "Karabulak", "Sunja", "Nazran", "Magas",  "Magas_test"]

# 4. Notion Client Factory
_notion_client = None

def get_notion_client() -> AsyncClient:
    """
    Returns a shared instance of AsyncClient.
    If it doesn't exist, creates one.
    """
    global _notion_client
    if _notion_client is None:
        api_key = os.getenv("NOTION_API_KEY")
        if not api_key:
            raise ValueError("❌ NOTION_API_KEY not found in environment variables")
        _notion_client = AsyncClient(auth=api_key)
    return _notion_client

async def close_notion_client():
    """Closes the shared Notion client if it exists."""
    global _notion_client
    if _notion_client:
        await _notion_client.aclose()
        _notion_client = None
