import os
import sys

from fastapi import FastAPI
from contextlib import asynccontextmanager  
from database import create_db_and_tables
from routes import email_router, log_router
from pydantic_settings import BaseSettings
from fastapi.logger import logger
from fastapi.responses import JSONResponse


import nest_asyncio
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy"})
    
app = FastAPI(lifespan=lifespan)
app.include_router(email_router, prefix="/generate", tags=["Email"])
app.include_router(log_router, prefix="/logs", tags=["Logs"])
