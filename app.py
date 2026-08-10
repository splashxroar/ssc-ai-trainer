import streamlit as st
import os
import json
import time
import pandas as pd
import streamlit.components.v1 as components
from collections import Counter
from supabase import create_client, Client
from google import genai
from dotenv import load_dotenv

# Load secret keys
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- PAGE CONFIG MUST BE FIRST ---
st.set_page_config(page_title="SSC/CPO AI Trainer", layout="wide", initial_sidebar_state="expanded")

# --- 🎨 GOATED CUSTOM CSS INJECTION ---
st.markdown("""
<style>
    /* Force Dark Mode aesthetic */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* Hide default Streamlit headers and footers to look like a standalone pro app */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sleek Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Custom Button Styling with Neon Hover Effects */
    .stButton>button {
        border-radius: 6px;
        border: 1px solid #ff4b4b;
        background-color: #1e1e2f;
        color: #ff4b4b;
        font-weight: 600;
        transition: 0.3s;
    }
    .stButton>button:hover {
        border: 1px solid #ff4b4b;
        background-color: #ff4b4b;
        color: white;
        box-shadow: 0 0 10px #ff4b4b;
    }
    
    /* Cool Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #ff4b4b;
        color: #ff4b4b !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- SECURE LOGIN SCREEN ---
if 'username' not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>🛑 Secure Access</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Enter your Tag and a 4-Digit PIN. First time logins will automatically register your account.</p>", unsafe_allow_html=True)
    
    # Center the login box
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_input = st.text_input("Username").strip()
        pin_input = st.text_input("4-Digit PIN", type="password").strip()
        
        if st.button("Enter Arena", use_container_width=True):
            if user_input and pin_input:
                response = supabase.table("players").select("*").eq("username", user_input).execute()
                if response.data:
                    if response.data[0]['pin'] == pin_input:
                        st.session_state['username'] = user_input
                        st.rerun()
                    else:
                        st.error("❌ Wrong PIN! Stop trying to hack your friend's account.")
                else:
                    supabase.table("players").insert({"username": user_input, "pin": pin_input}).execute()
                    st.success("New account registered!")
                    st.session_state['username'] = user_input
                    st.rerun()
            else:
                st.warning("Fill in both fields.")
    st.stop()

# --- MAIN APP ---
current_user = st.session_state['username']
st.sidebar.markdown(f"### 👤 Player: <span style='color:#ff4b4b;'>{current_user}</span>", unsafe_allow_html=True)
if st.sidebar.button("Logout"):
    del st.session_state['username']
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Exam Settings")
selected_subject = st.sidebar.selectbox("Select Subject", ["GK (Polity, History, etc.)", "Math (Quant)", "English Comprehension", "General Intelligence (Reasoning)"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Moderate", "Hard"])
test_time_limit = st.sidebar.slider("Time Limit (Minutes)", 10, 60, 30)

st.title(f"🚀 SSC/CPO Training Camp")

# --- AUTO-SAVE RECOVERY SYSTEM ---
if 'current_test' not in st.session_state and 'review_data' not in st.session_state:
    recovery = supabase.table("active_sessions").select("*").eq("username", current_user).execute()
    if recovery.data:
        saved_session = recovery.data[0]
        st.session_state['current_test'] = saved_session['test_data']
        st.session_state['start_time'] = saved_session['start_time']
        st.session_state['current_focus'] = saved_session['focus_topic']
        st.session_state['current_difficulty'] = saved_session['difficulty']
        
        st.session_state['q_index'] = 0
        st.session_state['answers'] = {i: None for i in range(len(st.session_state['current_test']))}
        st.warning("🔄 Recovered your active test!")

tab1, tab2, tab3 = st.tabs(["⚔️ The Arena", "🏆 Leaderboard", "📺 Match VODs"])

with tab1:
    response = supabase.table("error_log").select("topic").eq("username", current_user).execute()
    weakest_topic = None

    if response.data:
        topics = [row['topic'] for row in response.data]
        topic_counts = Counter(topics)
        weakest_topic = topic_counts.most_common(1)[0][0]
        st.error(f"💀 **AI Roast:** You are bottom-fragging in **{weakest_topic}**.")

    if 'current_test' not in st.session_state and 'review_data' not in st.session_state:
        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            start_standard = st.button(f"📚 Start {selected_subject} Test", use_container_width=True)
        with col2:
            start_weakest = st.button("🔥 Generate Weakest Topic Test", disabled=not weakest_topic, use_container_width=True)

        def generate_ai_test(focus_topic):
            with st.spinner(f"Cooking a 25-question {difficulty} test for {focus_topic}..."):
                prompt = f"Generate a 25-question multiple-choice test for SSC CGL level. Subject: {focus_topic}. Difficulty Level: {difficulty}. Return ONLY valid JSON format as a list of dictionaries with exactly these keys: 'question', 'options' (list of 4 strings), 'answer' (the exact correct option string), and 'explanation' (a detailed 2-sentence explanation)."
                try:
                    ai_response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                    raw_text = ai_response.text.replace("```json", "").replace("