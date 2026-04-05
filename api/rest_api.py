"""
REST API - FastAPI-based REST API for Jarvis AI.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Depends, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not available — REST API disabled")


if FASTAPI_AVAILABLE:
    class ChatRequest(BaseModel):
        message: str
        session_id: Optional[str] = None

    class CommandRequest(BaseModel):
        command: str
        args: Optional[Dict[str, Any]] = None

    class NoteRequest(BaseModel):
        title: str = ""
        content: str
        tags: str = ""
        category: str = "general"

    class TaskRequest(BaseModel):
        title: str
        scheduled_time: str
        priority: str = "medium"
        description: str = ""


def create_api_app(config, components: dict):
    """Create and configure the FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required for the REST API. Install with: pip install fastapi uvicorn")

    app = FastAPI(
        title="Jarvis AI API",
        description="Advanced AI Assistant REST API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ai = components.get("ai")
    system = components.get("system")
    memory = components.get("memory")
    db = components.get("db")
    scheduler = components.get("scheduler")

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/", tags=["Health"])
    def root():
        return {
            "name": "Jarvis AI",
            "version": "2.0.0",
            "status": "online",
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/health", tags=["Health"])
    def health():
        return {
            "status": "ok",
            "ai_available": ai.is_available() if ai else False,
            "timestamp": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # AI Chat
    # ------------------------------------------------------------------

    @app.post("/chat", tags=["AI"])
    def chat(req: ChatRequest):
        if not ai:
            raise HTTPException(503, "AI engine not initialized")
        response = ai.chat(req.message)
        if memory:
            memory.add("user", req.message)
            memory.add("assistant", response)
        return {
            "message": req.message,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }

    @app.post("/analyze", tags=["AI"])
    def analyze_intent(req: ChatRequest):
        if not ai:
            raise HTTPException(503, "AI engine not initialized")
        return ai.analyze_intent(req.message)

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    @app.get("/system/status", tags=["System"])
    def system_status():
        if not system:
            raise HTTPException(503, "System control not initialized")
        return system.get_system_status()

    @app.get("/system/processes", tags=["System"])
    def processes(top: int = Query(20, ge=1, le=100)):
        if not system:
            raise HTTPException(503, "System control not initialized")
        return {"processes": system.get_processes(top_n=top)}

    @app.get("/system/info", tags=["System"])
    def system_info():
        if not system:
            raise HTTPException(503, "System control not initialized")
        return system.get_os_info()

    @app.post("/system/command", tags=["System"])
    def run_command(req: CommandRequest):
        if not system:
            raise HTTPException(503, "System control not initialized")
        return system.run_command(req.command)

    @app.get("/system/files", tags=["System"])
    def list_files(path: str = Query(".", description="Directory path")):
        if not system:
            raise HTTPException(503, "System control not initialized")
        return {"files": system.list_directory(path)}

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    @app.get("/memory", tags=["Memory"])
    def get_memory(limit: int = Query(10, ge=1, le=100)):
        if not memory:
            raise HTTPException(503, "Memory system not initialized")
        return {"history": memory.get_recent(limit)}

    @app.delete("/memory", tags=["Memory"])
    def clear_memory():
        if not memory:
            raise HTTPException(503, "Memory system not initialized")
        memory.clear_short_term()
        return {"status": "cleared"}

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    @app.get("/notes", tags=["Notes"])
    def get_notes():
        if not db:
            raise HTTPException(503, "Database not initialized")
        return {"notes": db.get_notes()}

    @app.post("/notes", tags=["Notes"])
    def create_note(req: NoteRequest):
        if not db:
            raise HTTPException(503, "Database not initialized")
        note_id = db.save_note(req.title, req.content, req.tags, req.category)
        return {"id": note_id, "status": "created"}

    @app.get("/history", tags=["History"])
    def get_history(limit: int = Query(50, ge=1, le=200)):
        if not db:
            raise HTTPException(503, "Database not initialized")
        return {"history": db.get_command_history(limit)}

    @app.get("/tasks", tags=["Tasks"])
    def get_tasks():
        if not db:
            raise HTTPException(503, "Database not initialized")
        return {"tasks": db.get_pending_tasks()}

    @app.get("/scheduler/jobs", tags=["Scheduler"])
    def scheduler_jobs():
        if not scheduler:
            return {"jobs": []}
        return {"jobs": scheduler.get_jobs()}

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    @app.get("/models", tags=["AI"])
    def list_models():
        if not ai:
            return {"models": []}
        return {"models": ai.list_models()}

    return app
