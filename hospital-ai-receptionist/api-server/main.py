"""
FastAPI entry point for the Hospital AI Receptionist API server.
Handles patient management, appointment booking, and reminder scheduling.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.conversation import router as conversation_router
from routes.health import router as health_router
from services.scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("api-server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the APScheduler on startup, shut it down on exit."""
    logger.info("Starting APScheduler…")
    start_scheduler()
    yield
    logger.info("Shutting down APScheduler…")
    shutdown_scheduler()


app = FastAPI(
    title="Hospital AI Receptionist — API Server",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["Health"])
app.include_router(conversation_router, prefix="/conversation", tags=["Conversation"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
