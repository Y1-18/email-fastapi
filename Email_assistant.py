import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
from typing import Dict, List, Optional
import asyncio
import aiohttp

# Configure the page
st.set_page_config(
    page_title="AI Email Assistant",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    .chat-header {
        text-align: center;
        padding: 25px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }
    
    .email-form {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        margin: 10px 0;
    }
    
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        text-align: center;
    }
    
    .status-success {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    
    .status-error {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    
    .api-status {
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        text-align: center;
        font-weight: bold;
    }
    
    .api-connected {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .api-disconnected {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

class FastAPIEmailAssistant:
    def __init__(self, api_base_url: str = None):
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.session = requests.Session()
        self.session.timeout = 30
        
    def test_connection(self) -> bool:
        """Test connection to FastAPI backend"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def chat_with_ai(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Send chat message to FastAPI backend with OpenAI integration"""
        try:
            payload = {
                "message": message,
                "conversation_history": conversation_history or [],
                "context": "email_assistant"
            }
            
            response = self.session.post(
                f"{self.api_base_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json().get("response", "Sorry, I couldn't process your request.")
            else:
                return f"API Error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return f"Connection error: Unable to reach the AI service. Please check if the API is running."
        except Exception as e:
            return f"Error: {str(e)}"
    
    def generate_email(self, email_type: str, recipient: str, context: str, sender_name: str = "Your Name") -> Dict[str, str]:
        """Generate email using FastAPI backend with OpenAI"""
        try:
            payload = {
                "email_type": email_type,
                "recipient_name": recipient,
                "context": context,
                "sender_name": sender_name,
                "tone": "professional"
            }
            
            response = self.session.post(
                f"{self.api_base_url}/generate-email",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "subject": "Email Generation Failed",
                    "body": f"Failed to generate email. API Error: {response.status_code}",
                    "error": True
                }
                
        except Exception as e:
            return {
                "subject": "Connection Error",
                "body": f"Unable to connect to AI service: {str(e)}",
                "error": True
            }
    
    def send_email(self, recipient_email: str, subject: str, body: str, sender_name: str = "Your Name") -> bool:
        """Send email through FastAPI backend"""
        try:
            payload = {
                "to_email": recipient_email,
                "subject": subject,
                "body": body,
                "sender_name": sender_name
            }
            
            response = self.session.post(
                f"{self.api_base_url}/send-email",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            st.error(f"Error sending email: {str(e)}")
            return False

# Initialize the assistant
if "api_assistant" not in st.session_state:
    st.session_state.api_assistant = FastAPIEmailAssistant()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your AI Email Assistant powered by OpenAI. I can help you write professional emails, provide suggestions, and send them directly. How can I assist you today?"}
    ]

if "generated_email" not in st.session_state:
    st.session_state.generated_email = None

if "api_connected" not in st.session_state:
    st.session_state.api_connected = None

# Check API connection
def check_api_status():
    if st.session_state.api_connected is None:
        st.session_state.api_connected = st.session_state.api_assistant.test_connection()
    return st.session_state.api_connected

# Main header
st.markdown("""
<div class="chat-header">
    <h1>🤖 AI Email Assistant</h1>
    <p>Powered by OpenAI & FastAPI | Professional Email Generation & Management</p>
</div>
""", unsafe_allow_html=True)

# API Status indicator
api_status = check_api_status()
if api_status:
    st.markdown("""
    <div class="api-status api-connected">
        ✅ Connected to FastAPI Backend with OpenAI
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="api-status api-disconnected">
        ⚠️ Cannot connect to FastAPI Backend - Using offline mode
    </div>
    """, unsafe_allow_html=True)

# Create two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat with AI Assistant")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about emails or request help writing one..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
                if api_status:
                    # Use FastAPI + OpenAI for response
                    conversation_history = [
                        {"role": msg["role"], "content": msg["content"]} 
                        for msg in st.session_state.messages[-10:]  # Last 10 messages for context
                    ]
                    response = st.session_state.api_assistant.chat_with_ai(prompt, conversation_history)
                else:
                    # Fallback response when API is not available
                    response = "I'm currently unable to connect to the AI service. Please ensure your FastAPI backend is running with OpenAI integration. You can still use the email generator in the sidebar."
                
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

with col2:
    st.subheader("✉️ Smart Email Generator")
    
    with st.form("email_form"):
        email_type = st.selectbox(
            "Email Type",
            ["thank_you", "follow_up", "meeting_request", "project_update", "apology", "introduction", "proposal", "reminder"],
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        sender_name = st.text_input("Your Name", placeholder="John Doe")
        recipient_name = st.text_input("Recipient Name", placeholder="Jane Smith")
        recipient_email = st.text_input("Recipient Email", placeholder="jane@example.com")
        context = st.text_area(
            "Email Context/Details", 
            placeholder="Provide specific details about what you want to communicate...",
            height=100
        )
        
        tone = st.selectbox("Email Tone", ["professional", "casual", "formal", "friendly"])
        
        if st.form_submit_button("🤖 Generate with AI", type="primary"):
            if recipient_name and context and sender_name:
                if api_status:
                    with st.spinner("Generating email with AI..."):
                        email_content = st.session_state.api_assistant.generate_email(
                            email_type, recipient_name, context, sender_name
                        )
                        
                        if not email_content.get("error"):
                            st.session_state.generated_email = {
                                **email_content,
                                "recipient_email": recipient_email,
                                "sender_name": sender_name
                            }
                            st.success("✅ Email generated successfully with AI!")
                        else:
                            st.error("❌ Failed to generate email with AI")
                else:
                    st.error("❌ Cannot generate email - API backend not available")
            else:
                st.error("Please fill in all required fields.")
    
    # Display generated email
    if st.session_state.generated_email:
        st.subheader("📝 Generated Email")
        
        with st.expander("Preview Email", expanded=True):
            # Editable email content
            edited_subject = st.text_input(
                "Subject", 
                value=st.session_state.generated_email.get("subject", ""),
                key="email_subject"
            )
            edited_body = st.text_area(
                "Body", 
                value=st.session_state.generated_email.get("body", ""),
                height=300,
                key="email_body"
            )
            
            # Update the generated email with edits
            if edited_subject != st.session_state.generated_email.get("subject"):
                st.session_state.generated_email["subject"] = edited_subject
            if edited_body != st.session_state.generated_email.get("body"):
                st.session_state.generated_email["body"] = edited_body

# Sidebar for configuration and features
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # API Configuration
    with st.expander("🔧 API Settings", expanded=False):
        api_url = st.text_input(
            "FastAPI Backend URL", 
            value=st.session_state.api_assistant.api_base_url,
            help="URL of your FastAPI backend (e.g., https://your-app.onrender.com)"
        )
        
        if st.button("Update API URL"):
            st.session_state.api_assistant.api_base_url = api_url
            st.session_state.api_connected = None  # Reset connection status
            st.success("API URL updated!")
            st.rerun()
        
        if st.button("Test API Connection"):
            with st.spinner("Testing connection..."):
                connection_status = st.session_state.api_assistant.test_connection()
                if connection_status:
                    st.success("✅ Connected to FastAPI backend!")
                else:
                    st.error("❌ Cannot connect to FastAPI backend")
                st.session_state.api_connected = connection_status
    
    st.markdown("---")
    
    # Send email section
    if st.session_state.generated_email:
        st.subheader("📧 Send Email")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Send Email", type="primary"):
                if (api_status and 
                    st.session_state.generated_email.get("recipient_email") and
                    st.session_state.generated_email.get("sender_name")):
                    
                    with st.spinner("Sending email..."):
                        success = st.session_state.api_assistant.send_email(
                            st.session_state.generated_email["recipient_email"],
                            st.session_state.generated_email["subject"],
                            st.session_state.generated_email["body"],
                            st.session_state.generated_email["sender_name"]
                        )
                        
                        if success:
                            st.success("✅ Email sent successfully!")
                            # Add to chat
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"✅ Email sent successfully to {st.session_state.generated_email['recipient_email']}!"
                            })
                        else:
                            st.error("❌ Failed to send email")
                else:
                    if not api_status:
                        st.error("❌ API backend not available")
                    else:
                        st.error("❌ Missing recipient email or sender name")
        
        with col2:
            if st.button("🗑️ Clear Email"):
                st.session_state.generated_email = None
                st.rerun()
    
    st.markdown("---")
    
    # Chat controls
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your AI Email Assistant. How can I help you today?"}
        ]
        st.session_state.generated_email = None
        st.rerun()
    
    st.markdown("---")
    
    # Features showcase
    st.subheader("🚀 Features")
    features = [
        "🤖 OpenAI-Powered Responses",
        "📧 Smart Email Generation", 
        "📤 Direct Email Sending",
        "🎨 Multiple Email Types",
        "💬 Conversational AI",
        "⚙️ FastAPI Integration",
        "🔄 Real-time Processing"
    ]
    
    for feature in features:
        st.markdown(f"""
        <div class="feature-card">
            {feature}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Stats and info
    st.subheader("📊 Session Info")
    total_messages = len(st.session_state.messages)
    user_messages = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
    st.metric("Total Messages", total_messages)
    st.metric("Your Messages", user_messages)
    if st.session_state.generated_email:
        st.metric("Generated Emails", 1)
    
    st.markdown("---")
    
    # API Status
    st.subheader("🔗 System Status")
    if api_status:
        st.success("FastAPI Backend: ✅ Online")
        st.success("OpenAI Integration: ✅ Active")
    else:
        st.error("FastAPI Backend: ❌ Offline")
        st.error("OpenAI Integration: ❌ Unavailable")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>🚀 AI Email Assistant | FastAPI + OpenAI + Streamlit | Ready for Production</div>", 
    unsafe_allow_html=True
)