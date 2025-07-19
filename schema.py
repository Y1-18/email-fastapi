from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel

# ------- email log -------
class EmailLogCreate(SQLModel):
    user_input: str
    context: Optional[str] = None
    response_to: Optional[str] = None
    length: Optional[str] = "medium"
    tone: Optional[str] = "formal"
    generated_email: str
    created_at: Optional[datetime] = None

class EmailLogRead(SQLModel):
    id: int
    user_input: str
    context: Optional[str]
    response_to: Optional[str]
    length: str
    tone: str
    generated_email: str
    created_at: datetime

# ------- email -------
class EmailRequest(SQLModel):
    user_input: str
    context: Optional[str] = None
    response_to: Optional[str] = None
    length: Optional[str] = "medium"  # short, medium, long
    tone: Optional[str] = "formal"    # formal, casual, relaxed

class EmailResponse(SQLModel):
    generated_email: str