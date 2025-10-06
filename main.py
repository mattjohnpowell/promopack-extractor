"""Main entry point for the PromoPack Claim Extractor."""

# Load environment variables from .env file BEFORE any other imports
from dotenv import load_dotenv
load_dotenv()

import uvicorn

from api import app
from database import init_db

# Initialize database on startup
# This gets registered when the module is imported by uvicorn
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    await init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
