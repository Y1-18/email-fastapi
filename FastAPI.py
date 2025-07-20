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

# Enable CORS for Streamlit or other frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client (NEW WAY)
openai_client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
    else:
        print("❌ OPENAI_API_KEY not found in environment variables")
except Exception as e:
    print(f"❌ OpenAI initialization error: {e}")

# Email sending configuration via SMTP
email_conf = None
fm = None
try:
    email_conf = ConnectionConfig(
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
        MAIL_FROM=os.getenv("MAIL_FROM", ""),
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
except Exception as e:
    print(f"⚠️ Email configuration warning: {e}")

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

# Health check endpoint - FIXED
@app.get("/health")
async def health_check():
    """Health check with service status"""
    status = {
        "status": "healthy",
        "service": "Email Assistant API",
        "openai_available": openai_client is not None,
        "email_configured": fm is not None,
        "timestamp": datetime.utcnow().isoformat()
    }
    return status

# Chat endpoint with OpenAI integration - FIXED
@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_request: ChatMessage):
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI service not available. Check API key configuration.")
    
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

        # Append last 10 conversation history messages
        for msg in chat_request.conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Append current user message
        messages.append({"role": "user", "content": chat_request.message})

        # FIXED: Use new OpenAI client syntax
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
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# Email generation endpoint - FIXED
@app.post("/generate-email", response_model=EmailResponse)
async def generate_email(request: EmailGenerationRequest):
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI service not available. Check API key configuration.")
    
    try:
        prompt = f"""
Generate a professional {request.tone} email with the following details:

Email Type: {request.email_type}
Recipient: {request.recipient_name}
Sender: {request.sender_name}
Context: {request.context}

Return a JSON object with fields "subject" and "body".
"""

        # FIXED: Use new OpenAI client syntax
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional email writing assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.6,
        )

        ai_response = response.choices[0].message.content.strip()

        # Parse AI response as JSON for subject and body
        try:
            email_json = json.loads(ai_response)
            subject = email_json.get("subject", "")
            body = email_json.get("body", "")
        except json.JSONDecodeError:
            # Fallback if AI does not respond with JSON
            subject = f"{request.email_type.replace('_', ' ').title()} - {request.recipient_name}"
            body = ai_response

        return EmailResponse(
            subject=subject,
            body=body,
            email_type=request.email_type,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email generation error: {str(e)}")

# Email sending endpoint - IMPROVED ERROR HANDLING
@app.post("/send-email", response_model=EmailSendResponse)
async def send_email(request: EmailSendRequest):
    if not fm:
        return EmailSendResponse(
            success=False,
            message="Email service not configured. Check email environment variables.",
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

# Email stats endpoint (mock data)
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
        }
    }

# WebSocket chat endpoint for real-time interaction - FIXED
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
        await websocket.send_text(message)

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
            
            # FIXED: Use new OpenAI client syntax
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful email assistant."},
                    {"role": "user", "content": data},
                ],
                max_tokens=500,
            )
            ai_response = response.choices[0].message.content
            await manager.send_personal_message(ai_response, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await manager.send_personal_message(f"Error: {str(e)}", websocket)

# Startup event to check configuration
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Email Assistant API...")
    print(f"✅ FastAPI server starting")
    
    # Check OpenAI configuration
    if openai_client:
        try:
            # Test OpenAI connection
            models = openai_client.models.list()
            print("✅ OpenAI connection verified")
        except Exception as e:
            print(f"❌ OpenAI connection test failed: {e}")
    else:
        print("❌ OpenAI not configured - set OPENAI_API_KEY environment variable")
    
    # Check email configuration
    if fm:
        print("✅ Email service configured")
    else:
        print("⚠️ Email service not configured - email sending will be disabled")

# Run with `uvicorn main:app --host 0.0.0.0 --port 8000` or via Railway start command
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
