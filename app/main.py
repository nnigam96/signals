import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load env before importing config
load_dotenv()

from app.config import settings
from app.api.routes import router
from app.pipeline.mongodb import connect_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    connect_db()
    logger.info("")
    logger.info("🚀 Signals API running on http://localhost:%s", settings.port)
    logger.info("   Front-end: https://lovable.dev/...")
    logger.info("")
    yield
    # Shutdown (if needed)

app = FastAPI(title="Signals", version="0.1.0", lifespan=lifespan)

# Allow Lovable to hit your localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok", "event": "Hack the Stackathon"}