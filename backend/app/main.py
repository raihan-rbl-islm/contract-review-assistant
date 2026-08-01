"""
FastAPI app instance, CORS, router mounting, startup event.
See Plan.md §3 (main.py) and §4 (startup data loading).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging
from app.database import create_tables
from app.data.loader import load_all_data
from app.routers import review, feedback, diagnostics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle.
    On startup: configure logging, create DB tables, load all contest data.
    """
    # --- Startup ---
    setup_logging()
    logger.info("Starting Contract Review Assistant backend...")

    # Create DB tables
    await create_tables()
    logger.info("Database tables created/verified")

    # Load all contest data into app.state
    data = load_all_data()
    app.state.data = data
    logger.info(
        f"Data loaded: {len(data.contracts)} contracts, "
        f"{len(data.standards)} standards, "
        f"{len(data.public_test_questions)} PQ, "
        f"{len(data.missing_info_cases)} MI"
    )

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")


app = FastAPI(
    title="Northstar Contract Review Assistant",
    description="AI-assisted contract clause review with human-in-the-loop verification.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server origin only (Plan.md §13)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(review.router, prefix="/api", tags=["Review"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(diagnostics.router, prefix="/api", tags=["Diagnostics"])


@app.get("/api/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
