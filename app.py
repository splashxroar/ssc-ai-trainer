import streamlit as st
import os
import json
import time
import pandas as pd
from collections import Counter
from supabase import create_client, Client
from google import genai
from dotenv import load_dotenv

# Load your secret keys from the .env file
load_dotenv()

# Connect to Supabase & Gemini
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="SSC/CPO AI Trainer", layout="wide")

# --- LOGIN SCREEN ---
if 'username' not in st.session_state:
    st.title("🛑 Hold Up. Identify Yourself.")
    st.write("Welcome to the 5-Stack Training Camp. Enter your tag to access the tests.")
    user_input = st.text_input("Enter your Username:")
    if st.button("Enter Arena"):
        if user_input.strip():
            st.session_state['username'] = user_input.strip()
            st.rerun()
        else:
            st.error("Don't be shy, type a name.")
    st.stop() # Stops the rest of the app from loading until logged in

# --- MAIN APP (Only runs if logged in) ---
current_user = st.session_state['username']

# Sidebar
st.sidebar.header(f"👤 Player: {current_user}")
if st.sidebar.button("Logout"):
    del st.session_state['username']
    st.rerun()

st.sidebar.header("⚙️ Exam Settings")
selected_subject = st.sidebar.selectbox("Select Subject", ["GK (Polity, History, etc.)", "Math (Quant)", "English Comprehension", "General Intelligence (Reasoning)"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Moderate", "Hard"])
test_time_limit = st.sidebar.slider("Time Limit (Minutes)", 10, 60, 30)

st.title(f"🚀 SSC/CPO Training Camp")

# --- TABS: Play vs Profile ---
tab1, tab2 = st.tabs(["⚔️ The Arena (Take Tests)", "🏆 Profile & Leaderboard"])

with tab1:
    # --- AI Analytics Dashboard (Personalized) ---
    st.subheader(f"📊 {current_user}'s Performance Data")
    response = supabase.table("error_log").select("topic").eq("username", current_user).execute()
    weakest_topic = None

    if response.data:
        topics = [row['topic'] for row in response.data]
        topic_counts = Counter(topics)
        weakest_topic = topic_counts.most_common(1)[0][0]
        st.error(f"💀 **AI Roast:** You are officially bottom-fragging in **{weakest_topic}**. The AI is tracking your fails.")
    else:
        st.info("No errors logged yet! Go take a test.")

    # --- Test Generation ---
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        start_standard = st.button(f"📚 Start {selected_subject} Test")
    with col2:
        start_weakest = st.button("🔥 Generate Weakest Topic Test", disabled=not weakest_topic)

    def generate_ai_test(focus_topic):
        with st.spinner(f"AI is cooking a 25-question {difficulty} test for {focus_topic}..."):
            prompt = f"Generate a 25-question multiple-choice test for SSC CGL level. Subject: {focus_topic}. Difficulty Level: {difficulty}. Return ONLY valid JSON format as a list of dictionaries with keys: 'question', 'options' (list of 4 strings), and 'answer'."
            try:
                ai_response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                raw_text = ai_response.text.replace("```json", "").replace("```", "").strip()
                st.session_state['current_test'] = json.loads(raw_text)
                st.session_state['start_time'] = time.time()
                st.session_state['current_focus'] = focus_topic
                st.rerun() 
            except Exception as e:
                st.error(f"Failed to generate test. Try again.")

    if start_standard:
        generate_ai_test(selected_subject)
    elif start_weakest and weakest_topic:
        generate_ai_test(weakest_topic)

    # --- Render the interactive test ---
    if 'current_test' in st.session_state:
        st.write("---")
        st.subheader(f"📝 Active Test: {st.session_state['current_focus']} ({difficulty})")
        
        user_answers = {}
        for i, q in enumerate(st.session_state['current_test']):
            st.markdown(f"**Q{i+1}: {q['question']}**")
            user_answers[i] = st.radio("Select an option:", q['options'], key=f"q_{i}", index=None)
            st.write("")
            
        if st.button("Submit Test"):
            score = 0
            for i, q in enumerate(st.session_state['current_test']):
                if user_answers[i] == q['answer']:
                    score += 1
                elif user_answers[i] is not None:
                    # Log mistake with username
                    supabase.table("error_log").insert({
                        "username": current_user,
                        "topic": st.session_state['current_focus'],
                        "question": q['question'],
                        "correct_answer": q['answer']
                    }).execute()
            
            # Save the score to the leaderboard history
            total_q = len(st.session_state['current_test'])
            supabase.table("test_history").insert({
                "username": current_user,
                "subject": st.session_state['current_focus'],
                "score": score,
                "total": total_q
            }).execute()
                    
            st.success(f"Test Submitted! You scored {score}/{total_q}.")
            del st.session_state['current_test']
            if st.button("Refresh Analytics"):
                st.rerun()

with tab2:
    st.subheader("🏆 Global Leaderboard & Match History")
    history_response = supabase.table("test_history").select("*").order("created_at", desc=True).limit(50).execute()
    
    if history_response.data:
        # Convert database response to a nice table
        df = pd.DataFrame(history_response.data)
        df['Accuracy'] = (df['score'] / df['total'] * 100).round(1).astype(str) + '%'
        
        # Show Leaderboard (Highest Scores)
        st.write("### 🥇 Top Scores")
        leaderboard = df.sort_values(by='score', ascending=False).head(10)
        st.dataframe(leaderboard[['username', 'subject', 'score', 'total', 'Accuracy']], use_container_width=True, hide_index=True)
        
        # Show Recent Matches
        st.write("### 🕒 Recent Matches")
        st.dataframe(df[['username', 'subject', 'score', 'total', 'created_at']], use_container_width=True, hide_index=True)
    else:
        st.info("No tests have been taken yet. Be the first to set a high score!")