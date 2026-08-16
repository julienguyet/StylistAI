import streamlit as st
import requests
import uuid

ADK_API_URL = "http://stylist-agent:8015"
APP_NAME = "stylist_agent"
USER_ID = "u_streamlit"

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Björn – AI Stylist",
    page_icon="👗",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* Hide Streamlit default header and footer for a cleaner look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- SIDEBAR (Portfolio Context) ---
with st.sidebar:
    st.title("👗 About Björn")
    st.markdown("""
    Welcome to **Björn**, your personal AI fashion stylist.
    
    This project is built using:
    - **Streamlit** for the frontend
    - **ADK** for the multi-agent framework
    - **GenAI** for understanding fashion trends
    """)
    st.divider()
    
    st.markdown("### Controls")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = f"s_{uuid.uuid4().hex[:8]}"
        st.session_state.initialized = False
        st.rerun()

    st.divider()
    st.caption("Developed by [Your Name]") # User can update this


def create_session(session_id: str) -> bool:
    """Create an ADK session; returns True on success."""
    url = f"{ADK_API_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
    try:
        r = requests.post(url, json={}, timeout=10)
        return r.status_code in (200, 201)
    except requests.RequestException as e:
        st.sidebar.error(f"⚠️ Agent API offline: {e}")
        return False

def send_message(session_id: str, text: str) -> str:
    """Send a message and return the agent's reply text."""
    url = f"{ADK_API_URL}/run"
    payload = {
        "appName": APP_NAME,
        "userId": USER_ID,
        "sessionId": session_id,
        "newMessage": {
            "role": "user",
            "parts": [{"text": text}]
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()

        for event in reversed(data):
            content = event.get("content", {})
            role    = content.get("role", "")
            parts   = content.get("parts", [])
            if role == "model" and parts:
                texts = [p["text"] for p in parts if "text" in p]
                if texts:
                    return "\n".join(texts)

        return "_(no text response from agent)_"

    except requests.RequestException as e:
        return f"❌ Request error: {e}"
    except Exception as e:
        return f"❌ Unexpected error: {e}"


# --- SESSION INITIALIZATION ---
if "session_id" not in st.session_state:
    st.session_state.session_id  = f"s_{uuid.uuid4().hex[:8]}"
    st.session_state.initialized = False
    st.session_state.messages    = []

def ensure_session():
    if not st.session_state.initialized:
        ok = create_session(st.session_state.session_id)
        if ok:
            st.session_state.initialized = True
        else:
            st.stop()


# --- MAIN CHAT INTERFACE ---
st.title("👗 Björn – AI Fashion Stylist")
st.markdown("Ask for outfit recommendations, style tips, or item pairings!")

# Onboarding / Empty State Welcome Message
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="👗"):
        st.markdown("Hello! I'm Björn, your personal fashion stylist. ✨ How can I elevate your wardrobe today?")
        st.info("**Try asking:**\n- *What should I wear to a casual summer wedding?*\n- *How do I style a black turtleneck?*\n- *What are some trendy sneaker options right now?*")

# Display chat history
for msg in st.session_state.messages:
    # Set avatar based on role
    avatar = "👤" if msg["role"] == "user" else "👗"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask Björn anything about style…"):
    ensure_session()

    # Append and show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Fetch and show assistant response
    with st.chat_message("assistant", avatar="👗"):
        with st.spinner("✨ Björn is tailoring your response…"):
            reply = send_message(st.session_state.session_id, prompt)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
