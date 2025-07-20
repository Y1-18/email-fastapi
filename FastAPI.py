# main.py - Fixed for Railway deployment
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional
import os
import asyncio
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from datetime import datetime
import json

# Import OpenAI client (updated for v1.0+)
from openai import OpenAI

# Initialize FastAPI app
app = FastAPI(title="Email Assistant API", version="1.0.0")

# RAILWAY FIX: Enable CORS for Railway domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Railway needs this for cross-origin requests
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAILWAY FIX: Initialize OpenAI client with better error handling
openai_client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith("sk-"):
        openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
    else:
        print("❌ Invalid or missing OPENAI_API_KEY")
except Exception as e:
    print(f"❌ OpenAI initialization error: {e}")

# Email configuration (optional for Railway)
email_conf = None
fm = None
try:
    if all([os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"), os.getenv("MAIL_FROM")]):
        email_conf = ConnectionConfig(
            MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
            MAIL_FROM=os.getenv("MAIL_FROM"),
            MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
            MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "Email Assistant"),
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        fm = FastMail(email_conf)
        print("✅ Email configuration initialized")
    else:
        print("⚠️ Email configuration skipped - missing environment variables")
except Exception as e:
    print(f"⚠️ Email configuration error: {e}")

# Pydantic models
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

class EmailSendRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    sender_name: str = "Your Name"

class EmailSendResponse(BaseModel):
    success: bool
    message: str

# RAILWAY FIX: Root endpoint for Railway health checks
@app.get("/")
async def root():
    return {
        "message": "Email Assistant API is running on Railway",
        "status": "healthy",
        "deployment": "railway",
        "services": {
            "openai": openai_client is not None,
            "email": fm is not None
        }
    }

# Health check endpoint - Railway compatible
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "Email Assistant API",
        "platform": "railway",
        "openai_available": openai_client is not None,
        "email_configured": fm is not None,
        "timestamp": datetime.utcnow().isoformat(),
        "environment_vars": {
            "OPENAI_API_KEY": "set" if os.getenv("OPENAI_API_KEY") else "missing",
            "PORT": os.getenv("PORT", "not_set"),
            "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT", "not_railway")
        }
    }

# Chat endpoint with OpenAI integration
@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_request: ChatMessage):
    if not openai_client:
        raise HTTPException(
            status_code=503, 
            detail="OpenAI service not available. Please check OPENAI_API_KEY environment variable in Railway."
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

Always be helpful, professional, and provide actionable advice.
If asked to write an email, ask for specific details like recipient, purpose, and context.
"""
            }
        ]

        # Append conversation history (last 10 messages)
        for msg in chat_request.conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Append current user message
        messages.append({"role": "user", "content": chat_request.message})

        # Use new OpenAI client syntax
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )

        ai_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return ChatResponse(response=ai_response, tokens_used=tokens_used)
    
    except Exception as e:
        print(f"Chat error: {str(e)}")  # Railway logs
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# Email generation endpoint
@app.post("/generate-email", response_model=EmailResponse)
async def generate_email(request: EmailGenerationRequest):
    if not openai_client:
        raise HTTPException(
            status_code=503, 
            detail="OpenAI service not available. Please check OPENAI_API_KEY environment variable."
        )
    
    try:
        prompt = f"""
Generate a professional {request.tone} email with the following details:

Email Type: {request.email_type}
Recipient: {request.recipient_name}
Sender: {request.sender_name}
Context: {request.context}

Return a JSON object with fields "subject" and "body".
"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional email writing assistant. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.6,
        )

        ai_response = response.choices[0].message.content.strip()

        # Parse AI response as JSON
        try:
            # Clean response if it has markdown code blocks
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].strip()
            
            email_json = json.loads(ai_response)
            subject = email_json.get("subject", "")
            body = email_json.get("body", "")
        except json.JSONDecodeError:
            # Fallback if AI doesn't return valid JSON
            subject = f"{request.email_type.replace('_', ' ').title()} - {request.recipient_name}"
            body = ai_response

        return EmailResponse(
            subject=subject,
            body=body,
            email_type=request.email_type,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
    
    except Exception as e:
        print(f"Email generation error: {str(e)}")  # Railway logs
        raise HTTPException(status_code=500, detail=f"Email generation error: {str(e)}")

# Email sending endpoint
@app.post("/send-email", response_model=EmailSendResponse)
async def send_email(request: EmailSendRequest):
    if not fm:
        return EmailSendResponse(
            success=False,
            message="Email service not configured. Set MAIL_USERNAME, MAIL_PASSWORD, and MAIL_FROM environment variables.",
        )
    
    try:
        message = MessageSchema(
            subject=request.subject,
            recipients=[request.to_email],
            body=request.body,
            subtype="html" if "<" in request.body else "plain",
        )

        await fm.send_message(message)
        return EmailSendResponse(
            success=True,
            message=f"Email sent successfully to {request.to_email}",
        )
    except Exception as e:
        print(f"Email sending error: {str(e)}")  # Railway logs
        return EmailSendResponse(
            success=False,
            message=f"Failed to send email: {str(e)}",
        )

# Email templates endpoint
@app.get("/email-templates")
async def get_email_templates():
    templates = {
        "thank_you": {
            "name": "Thank You Email",
            "description": "Express gratitude and appreciation",
            "example": "Thank someone for their time, help, or support",
        },
        "follow_up": {
            "name": "Follow-up Email",
            "description": "Follow up on previous conversations or meetings",
            "example": "Check on project status or continue a discussion",
        },
        "meeting_request": {
            "name": "Meeting Request",
            "description": "Request a meeting or schedule discussion",
            "example": "Schedule a call, meeting, or presentation",
        },
        "project_update": {
            "name": "Project Update",
            "description": "Provide status updates on ongoing work",
            "example": "Share progress, milestones, or changes",
        },
        "apology": {
            "name": "Apology Email",
            "description": "Apologize professionally for mistakes or delays",
            "example": "Address errors, missed deadlines, or misunderstandings",
        },
        "introduction": {
            "name": "Introduction Email",
            "description": "Introduce yourself or connect people",
            "example": "Network, introduce services, or make connections",
        },
        "proposal": {
            "name": "Proposal Email",
            "description": "Present ideas, suggestions, or business proposals",
            "example": "Pitch services, suggest solutions, or present offers",
        },
        "reminder": {
            "name": "Reminder Email",
            "description": "Gentle reminders for deadlines or commitments",
            "example": "Remind about meetings, payments, or deliverables",
        },
    }
    return templates

# Email stats endpoint
@app.get("/email-stats")
async def get_email_stats():
    return {
        "emails_generated_today": 0,
        "emails_sent_today": 0,
        "most_popular_template": "follow_up",
        "ai_tokens_used": 0,
        "services_available": {
            "openai": openai_client is not None,
            "email": fm is not None
        },
        "deployment": "railway"
    }

# WebSocket for real-time chat (Railway compatible)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            # Remove disconnected websocket
            self.disconnect(websocket)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            if not openai_client:
                await manager.send_personal_message(
                    "OpenAI service is not available. Please check configuration.", 
                    websocket
                )
                continue
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful email assistant."},
                    {"role": "user", "content": data},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            ai_response = response.choices[0].message.content
            await manager.send_personal_message(ai_response, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {str(e)}")  # Railway logs
        manager.disconnect(websocket)

# Railway startup event
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Email Assistant API on Railway...")
    print(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'unknown')}")
    print(f"Port: {os.getenv('PORT', 'not_set')}")
    
    # Check OpenAI
    if openai_client:
        try:
            models = openai_client.models.list()
            print("✅ OpenAI connection verified")
        except Exception as e:
            print(f"❌ OpenAI connection failed: {e}")
    else:
        print("❌ OpenAI not configured")
    
    # Check email
    if fm:
        print("✅ Email service configured")
    else:
        print("⚠️ Email service not configured")

# RAILWAY FIX: Proper port binding
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # Railway provides PORT env var
    print(f"Starting server on port {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
