from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import vrp, preview, fm, websocket, data
import os

app = FastAPI(
    title="VRP API",
    description="Vehicle Route Planning API with VROOM + OSRM",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(vrp.router)
app.include_router(preview.router)
app.include_router(fm.router)
app.include_router(websocket.router)
app.include_router(data.router)


@app.get("/")
async def root():
    """Serve the frontend"""
    static_index = os.path.join(static_dir, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return {
        "message": "VRP API",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "/static/index.html"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
