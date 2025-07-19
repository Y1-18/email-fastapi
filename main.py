import os
import sys

from fastapi import FastAPI
from database import create_db_and_tables
from routes import email_router, log_router

async def lifespan(app):
    await create_db_and_tables()
    yield

app = FastAPI(
    title="Email Assistant API",
    description="An AI-powered email generation assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(email_router, prefix="/generate", tags=["Email Generation"])
app.include_router(log_router, prefix="/logs", tags=["Email Logs"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Email Assistant API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# __init__.py
# (This file should be empty as mentioned in the tutorial)

# requirements.txt (for reference)
"""
fastapi
fastcrud
sqlmodel
openai
aiosqlite
pydantic-settings
uvicorn[standard]
python-multipart
"""

# .env (template)
"""
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
"""
