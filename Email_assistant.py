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
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL", "https://your-backend-service.up.railway.app")
        self.session = requests.Session()
        self.session.timeout = 30

    def test_connection(self) -> bool:
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("openai_available", False)
            return False
        except:
            return False

    def chat_with_ai(self, message: str, conversation_history: List[Dict] = None) -> str:
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

        except requests.exceptions.RequestException:
            return "Connection error: Unable to reach the AI service. Please check if the API is running."
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_email(self, email_type: str, recipient: str, context: str, sender_name: str = "Your Name") -> Dict[str, str]:
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
