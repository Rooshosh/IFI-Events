"""API service initialization."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from ..db import db_manager
from dotenv import load_dotenv
import logging

# Module logger
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="IFI Events API",
    description="API service for IFI Events data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db_manager.init_db()

# Include API routes
app.include_router(router, prefix="/api") 