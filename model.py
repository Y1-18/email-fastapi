from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class EmailLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_input: str = Field(description="The user's input text for email generation")
    context: Optional[str] = Field(default=None, description="Optional context for the email")
    response_to: Optional[str] = Field(default=None, description="Text the email should respond to")
    length: Optional[str] = Field(default="medium", description="Desired length of the email")
    tone: Optional[str] = Field(default="formal", description="Desired tone of the email")
    generated_email: str = Field(description="The generated email content")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of creation")
