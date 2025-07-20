# main.py - Fixed version for Railway
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional
import os
import json
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="Email Assistant API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for services
openai_client = None
email_service_available = False

# Initialize OpenAI client
def init_openai():
    global openai_client
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key.startswith("sk-"):
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized")
            return True
        else:
            print("❌ Invalid or missing OPENAI_API_KEY")
            return False
    except ImportError:
        print("❌ OpenAI package not installed")
        return False
    except Exception as e:
        print(f"❌ OpenAI initialization error: {e}")
        return False

# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Email Assistant API...")
    print(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"Port: {os.getenv('PORT', 'not_set')}")
    
    # Initialize OpenAI
    openai_available = init_openai()
    print(f"OpenAI Status: {'✅ Available' if openai_available else '❌ Not Available'}")
    
    print("✅ Startup completed")

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    service: str
    platform: str
    openai_available: bool
    timestamp: str

class ChatMessage(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = []
    context: Optional[str] = "email_assistant"

class ChatResponse(BaseModel):
    response: str
    tokens_used: Optional[int] = None

class EmailGenerationRequest(BaseModel):
    email_type: str
    recipient_name: str
    context: str
    sender_name: str = "Your Name"
    tone: str = "professional"

class EmailResponse(BaseModel):
    subject: str
    body: str
    email_type: str
    generated_at: str

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Email Assistant API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

# Health check endpoint - SIMPLIFIED for Railway
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Simplified health check for Railway"""
    try:
        return HealthResponse(
            status="healthy",
            service="Email Assistant API",
            platform="railway",
            openai_available=openai_client is not None,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        print(f"Health check error: {e}")
        return HealthResponse(
            status="error",
            service="Email Assistant API",
            platform="railway",
            openai_available=False,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_request: ChatMessage):
    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI service not available. Please check OPENAI_API_KEY."
        )
    
    try:
        messages = [
            {
                "role": "system",
                "content": """You are a professional email assistant AI. You help users:
1. Write professional emails for various purposes
2. Provide email writing advice and best practices
3. Suggest improvements to email tone and content
4. Answer questions about email etiquette
5. Generate email templates for different scenarios

Always be helpful, professional, and provide actionable advice."""
            }
        ]

        # Add conversation history (last 5 messages)
        for msg in chat_request.conversation_history[-5:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Add current message
        messages.append({"role": "user", "content": chat_request.message})

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=800,
            temperature=0.7,
        )

        ai_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return ChatResponse(response=ai_response, tokens_used=tokens_used)
    
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# Email generation endpoint
@app.post("/generate-email", response_model=EmailResponse)
async def generate_email(request: EmailGenerationRequest):
    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI service not available. Please check OPENAI_API_KEY."
        )
    
    try:
        prompt = f"""
Generate a professional {request.tone} email with the following details:

Email Type: {request.email_type}
Recipient: {request.recipient_name}
Sender: {request.sender_name}
Context: {request.context}

Return ONLY a JSON object with "subject" and "body" fields.
"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional email writing assistant. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.6,
        )

        ai_response = response.choices[0].message.content.strip()

        # Parse AI response
        try:
            # Clean response
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].strip()
            
            email_json = json.loads(ai_response)
            subject = email_json.get("subject", f"{request.email_type.replace('_', ' ').title()}")
            body = email_json.get("body", ai_response)
        except json.JSONDecodeError:
            # Fallback
            subject = f"{request.email_type.replace('_', ' ').title()} - {request.recipient_name}"
            body = ai_response

        return EmailResponse(
            subject=subject,
            body=body,
            email_type=request.email_type,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
    
    except Exception as e:
        print(f"Email generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Email generation error: {str(e)}")

# Email templates endpoint
@app.get("/email-templates")
async def get_email_templates():
    return {
        "thank_you": {
            "name": "Thank You Email",
            "description": "Express gratitude and appreciation"
        },
        "follow_up": {
            "name": "Follow-up Email", 
            "description": "Follow up on previous conversations"
        },
        "meeting_request": {
            "name": "Meeting Request",
            "description": "Request a meeting or discussion"
        },
        "project_update": {
            "name": "Project Update",
            "description": "Provide status updates on work"
        },
        "apology": {
            "name": "Apology Email",
            "description": "Apologize professionally for issues"
        },
        "introduction": {
            "name": "Introduction Email",
            "description": "Introduce yourself or connect people"
        }
    }

# Simple stats endpoint
@app.get("/stats")
async def get_stats():
    return {
        "service": "Email Assistant API",
        "status": "running",
        "openai_available": openai_client is not None,
        "deployment": "railway"
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
