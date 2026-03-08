import streamlit as st
import requests
import uuid

ADK_API_URL = "http://stylist-agent:8015"
APP_NAME = "stylist_agent"
USER_ID = "u_streamlit"

def create_session(session_id: str) -> bool:
    """Create an ADK session; returns True on success."""
    url = f"{ADK_API_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
    try:
        r = requests.post(url, json={}, timeout=10)
        return r.status_code in (200, 201)
    except requests.RequestException as e:
        st.error(f"Could not reach the agent API: {e}")
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


if "session_id" not in st.session_state:
    st.session_state.session_id  = f"s_{uuid.uuid4().hex[:8]}"
    st.session_state.initialized = False
    st.session_state.messages    = []

st.set_page_config(page_title="Erling – Stylist Agent", page_icon="👗")
st.title("👗 Erling – Stylist Agent")

def ensure_session():
    if not st.session_state.initialized:
        ok = create_session(st.session_state.session_id)
        if ok:
            st.session_state.initialized = True
        else:
            st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask Erling anything about style…"):
    ensure_session()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Erling is thinking…"):
            reply = send_message(st.session_state.session_id, prompt)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
