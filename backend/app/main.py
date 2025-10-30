"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api import router
from app.core import get_settings

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Astro Planner API",
    description="Astrophotography session planner for Seestar S50 smart telescope",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Route for shared plan viewer
frontend_path = Path(__file__).parent.parent / "frontend"

@app.get("/plan/{plan_id}")
async def serve_plan_viewer(plan_id: str):
    """Serve the plan viewer page for shared plans."""
    plan_html = frontend_path / "plan.html"
    if plan_html.exists():
        return FileResponse(plan_html)
    else:
        return {"error": "Plan viewer not found"}

# Serve static frontend files
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
else:
    print(f"⚠️  Frontend not found at {frontend_path}")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("🚀 Astro Planner API starting...")
    print(f"📍 Default location: {settings.default_location_name}")
    print(f"🔭 Seestar S50 FOV: {settings.seestar_fov_width}° × {settings.seestar_fov_height}°")
    print(f"⏰ Min target duration: {settings.min_target_duration_minutes} minutes")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("👋 Astro Planner API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
