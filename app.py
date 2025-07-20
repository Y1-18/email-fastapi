import streamlit as st
import openai
import sqlite3
from datetime import datetime
import os
from typing import List, Dict
import json

# Page config
st.set_page_config(
    page_title="🤖 Email Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .main .block-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    
    .chat-message.assistant {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        margin-right: 20%;
    }
    
    .chat-message .message-header {
        font-weight: bold;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    
    .chat-message.user .message-header {
        color: rgba(255,255,255,0.8);
    }
    
    .chat-message.assistant .message-header {
        color: #6c757d;
    }
    
    .chat-input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 1rem 0;
        border-top: 1px solid #e9ecef;
        margin-top: 2rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: transform 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stSelectbox > div > div {
        border-radius: 10px;
    }
    
    .stTextArea > div > div > textarea {
        border-radius: 10px;
    }
    
    .stTextInput > div > div > input {
        border-radius: 10px;
    }
    
    .header-container {
        text-align: center;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #f8f9fa;
    }
    
    .header-title {
        font-size: 2.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    .header-subtitle {
        color: #6c757d;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# Database setup
def init_database():
    """Initialize SQLite database for storing email logs"""
    conn = sqlite3.connect('email_assistant.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT NOT NULL,
            context TEXT,
            response_to TEXT,
            email_length TEXT DEFAULT 'medium',
            tone TEXT DEFAULT 'professional',
            generated_email TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_to_database(user_input: str, context: str, response_to: str, 
                    email_length: str, tone: str, generated_email: str):
    """Save email generation log to database"""
    conn = sqlite3.connect('email_assistant.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO email_logs (user_input, context, response_to, email_length, tone, generated_email)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_input, context or None, response_to or None, email_length, tone, generated_email))
    
    conn.commit()
    conn.close()

def get_email_history() -> List[Dict]:
    """Get email generation history from database"""
    conn = sqlite3.connect('email_assistant.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM email_logs ORDER BY timestamp DESC LIMIT 10
    ''')
    
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def generate_email_with_openai(user_input: str, context: str = None, 
                             response_to: str = None, email_length: str = "medium", 
                             tone: str = "professional") -> str:
    """Generate email using OpenAI API"""
    
    # Check if API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "❌ OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Create system prompt
        system_prompt = f"""You are a professional email assistant. Generate clear, well-structured emails based on user requirements. 
        Adapt your writing style based on the specified tone ({tone}) and length ({email_length}). 
        Always maintain professionalism while matching the requested tone."""
        
        # Create user prompt
        user_prompt = f"Write an email with the following requirements:\n- Main request: {user_input}"
        
        if context:
            user_prompt += f"\n- Additional context: {context}"
        if response_to:
            user_prompt += f"\n- Responding to: {response_to}"
        
        user_prompt += f"\n- Tone: {tone}\n- Length: {email_length}"
        
        # Determine max tokens based on length
        max_tokens_map = {"short": 200, "medium": 400, "long": 600}
        max_tokens = max_tokens_map.get(email_length, 400)
        
        # Generate email
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"❌ Error generating email: {str(e)}"

def display_chat_message(message: str, is_user: bool = False):
    """Display a chat message with proper styling"""
    message_type = "user" if is_user else "assistant"
    header = "You" if is_user else "🤖 Email Assistant"
    
    st.markdown(f"""
    <div class="chat-message {message_type}">
        <div class="message-header">{header}</div>
        <div>{message}</div>
    </div>
    """, unsafe_allow_html=True)

# Initialize database
init_database()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": "👋 Hi! I'm your AI email assistant. I can help you write professional emails quickly and efficiently. Just tell me what kind of email you want to write, and I'll generate it for you!"
        }
    ]

# Header
st.markdown("""
<div class="header-container">
    <h1 class="header-title">🤖 Email Assistant</h1>
    <p class="header-subtitle">Generate professional emails using AI</p>
</div>
""", unsafe_allow_html=True)

# Main chat interface
col1, col2 = st.columns([3, 1])

with col1:
    # Display chat messages
    for message in st.session_state.messages:
        display_chat_message(message["content"], message["role"] == "user")
    
    # Input form
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    
    with st.form("email_form", clear_on_submit=True):
        st.subheader("📝 Email Generation Form")
        
        # Main input
        user_input = st.text_area(
            "What kind of email do you want to write? *",
            placeholder="e.g., Thank you email for the meeting, Follow-up on project status, Request for vacation days...",
            height=100
        )
        
        # Optional fields
        col_a, col_b = st.columns(2)
        
        with col_a:
            response_to = st.text_input(
                "Reply To (optional)",
                placeholder="Original email or message to respond to..."
            )
            
            tone = st.selectbox(
                "Tone",
                options=["professional", "formal", "casual", "friendly", "urgent"],
                index=0
            )
        
        with col_b:
            context = st.text_area(
                "Context (optional)",
                placeholder="Additional context about the email...",
                height=60
            )
            
            email_length = st.selectbox(
                "Length",
                options=["short", "medium", "long"],
                index=1
            )
        
        # Submit button
        submitted = st.form_submit_button("🚀 Generate Email", use_container_width=True)
        
        if submitted and user_input:
            # Add user message to chat
            st.session_state.messages.append({
                "role": "user",
                "content": f"Generate email: {user_input}"
            })
            
            # Show loading message
            with st.spinner("🤖 Generating your email..."):
                # Generate email
                generated_email = generate_email_with_openai(
                    user_input=user_input,
                    context=context,
                    response_to=response_to,
                    email_length=email_length,
                    tone=tone
                )
                
                # Save to database (only if generation was successful)
                if not generated_email.startswith("❌"):
                    save_to_database(
                        user_input=user_input,
                        context=context,
                        response_to=response_to,
                        email_length=email_length,
                        tone=tone,
                        generated_email=generated_email
                    )
                
                # Add assistant response to chat
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": generated_email
                })
            
            # Rerun to show the new messages
            st.rerun()
        
        elif submitted and not user_input:
            st.error("Please enter what kind of email you want to write!")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Sidebar with additional features
with col2:
    st.markdown("### 📊 Email History")
    
    try:
        history = get_email_history()
        
        if history:
            for i, record in enumerate(history[:5]):  # Show last 5 emails
                with st.expander(f"Email #{record['id']} - {record['tone'].title()}"):
                    st.write(f"**Request:** {record['user_input'][:100]}...")
                    st.write(f"**Tone:** {record['tone'].title()}")
                    st.write(f"**Length:** {record['email_length'].title()}")
                    st.write(f"**Generated:** {record['timestamp']}")
                    
                    if st.button(f"View Full Email #{record['id']}", key=f"view_{record['id']}"):
                        st.text_area(
                            "Generated Email:", 
                            value=record['generated_email'], 
                            height=200,
                            key=f"email_content_{record['id']}"
                        )
        else:
            st.info("No emails generated yet.")
            
    except Exception as e:
        st.error(f"Error loading history: {str(e)}")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "👋 Hi! I'm your AI email assistant. I can help you write professional emails quickly and efficiently. Just tell me what kind of email you want to write, and I'll generate it for you!"
            }
        ]
        st.rerun()
    
    # API Configuration
    st.markdown("### ⚙️ Configuration")
    api_key_status = "✅ Configured" if os.getenv("OPENAI_API_KEY") else "❌ Not Set"
    st.info(f"**OpenAI API:** {api_key_status}")
    
    if not os.getenv("OPENAI_API_KEY"):
        st.warning("Set OPENAI_API_KEY environment variable to use the email generator.")
    
    # Instructions
    st.markdown("### 📚 How to Use")
    st.markdown("""
    1. **Describe** what email you want to write
    2. **Add context** if needed (optional)
    3. **Choose tone** and length
    4. **Click Generate** and get your email!
    5. **View history** of generated emails
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6c757d; padding: 1rem;'>"
    "🤖 Email Assistant powered by OpenAI GPT | Built with Streamlit"
    "</div>", 
    unsafe_allow_html=True
)
