"""FastAPI application entry point for SAR Narrative Generator."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import init_db
from backend.api.routes import router

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-assisted compliance system for generating SAR narratives",
    version="1.0.0",
)

# Configure CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup."""
    init_db()

    # Initialize vector store with prompts (lazy loading)
    from backend.rag.vectorstore import initialize_vectorstore
    try:
        initialize_vectorstore()
    except Exception as e:
        print(f"Warning: Could not initialize vector store: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from backend.llm.client import check_ollama_available, reset_ollama_check

    # Reset cache to get fresh status
    reset_ollama_check()
    ollama_status = check_ollama_available()

    return {
        "status": "healthy",
        "ollama_available": ollama_status,
        "mode": "llm" if ollama_status else "unavailable",
    }
