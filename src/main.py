from fastapi import FastAPI
from src.api.router import api_router
from src.core.config import settings

app = FastAPI(
    title="Placement Sentinel",
    description="Secure AI-powered VIT placement notification system",
    version="1.0.0"
)

# Register routers
app.include_router(api_router)

@app.get("/")
def read_root():
    """Health check endpoint for the FastAPI application."""
    return {"status": "ok", "service": "Placement Sentinel"}
