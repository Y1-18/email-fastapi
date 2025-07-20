import os
from datetime import datetime
from typing import List
from starlette.config import Config
from openai import OpenAI
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio.session import AsyncSession
from database import get_session
from crud import crud_email_logs
from schema import EmailRequest, EmailResponse, EmailLogCreate, EmailLogRead

# Fix: Get the API key from environment variables
current_file_dir = os.path.dirname(os.path.realpath(__file__))
env_path = os.path.join(current_file_dir, ".env")

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client with error handling
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please add it to your Render environment variables.")

open_ai_client = OpenAI(api_key=OPENAI_API_KEY)

# ------- email generation -------
email_router = APIRouter()

@email_router.post("/", response_model=EmailResponse)
async def generate_email(
    request: EmailRequest,
    db: AsyncSession = Depends(get_session)
):
    try:
        # System prompt: how the system should behave
        system_prompt = f"""
        You are a professional email writing assistant. Your role is to generate well-structured, 
        contextually appropriate emails based on user requirements. Always maintain the requested 
        tone and ensure the email is complete, coherent, and professionally formatted.
        
        Guidelines:
        - Write clear and concise emails
        - Use appropriate greetings and closings
        - Maintain the requested tone throughout
        - Include all relevant information provided by the user
        - Format the email properly with paragraphs and structure
        """
        
        # Determine max tokens based on length
        length_tokens = {
            "short": 200,
            "medium": 400,
            "long": 600
        }
        max_tokens = length_tokens.get(request.length, 400)
        
        # Build the prompt with all inputs
        prompt_parts = [
            f"Write an email based on the following requirements:",
            f"- User Input: {request.user_input}",
            f"- Tone: {request.tone}",
            f"- Length: {request.length}",
        ]
        
        if request.context:
            prompt_parts.append(f"- Additional Context: {request.context}")
            
        if request.response_to:
            prompt_parts.append(f"- This email should respond to: {request.response_to}")
            
        prompt_parts.append("\nPlease generate a complete email including subject line, greeting, body, and appropriate closing.")
        
        prompt = "\n".join(prompt_parts)
        
        # Getting the response from the model      
        response = open_ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
       
        generated_email = response.choices[0].message.content.strip()
        
        # Creating logs in the database
        log_entry = EmailLogCreate(
            user_input=request.user_input,
            context=request.context,
            response_to=request.response_to,
            length=request.length,
            tone=request.tone,
            generated_email=generated_email,
            created_at=datetime.utcnow()
        )
        await crud_email_logs.create(db, log_entry)
        
        return EmailResponse(generated_email=generated_email)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")

# ------- logs -------
log_router = APIRouter()

# endpoint to get all logs
@log_router.get("/")
async def read_logs(db: AsyncSession = Depends(get_session)):
    logs = await crud_email_logs.get_multi(db)
    return logs
