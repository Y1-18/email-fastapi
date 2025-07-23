import os
import sys

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings
from fastapi.logger import logger

from database import create_db_and_tables
from routes import email_router, log_router

import nest_asyncio
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

# ✅ Initialize FastAPI app with lifespan handler
app = FastAPI(lifespan=lifespan)

# ✅ Add routes
app.include_router(email_router, prefix="/generate", tags=["Email"])
app.include_router(log_router, prefix="/logs", tags=["Logs"])

# ✅ Add working /health endpoint for Railway
@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy"})
