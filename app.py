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
st.set_page_config(page_title="RADIANT: SSC Arena", layout="wide", initial_sidebar_state="expanded")

# --- 🎨 GEMINI UI INJECTION ---
st.markdown("""
<style>
    /* Gemini-style Dark Theme Background */
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Clean Headers */
    h1, h2, h3 {
        color: #ffffff !important;
    }

    /* Hide Streamlit Clutter */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sleek Sidebar (Gemini deep grey) */
    [data-testid="stSidebar"] {
        background-color: #1e1f22;
        border-right: 1px solid #444746;
    }
    
    /* Safely target Sidebar Text without breaking dropdowns */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p {
        color: #e3e3e3 !important;
    }
    
    /* Smooth Gemini-style Buttons */
    .stButton>button {
        border-radius: 24px;
        border: 1px solid #8ab4f8;
        background-color: transparent;
        color: #8ab4f8 !important;
        font-weight: 500;
        padding: 4px 20px;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: rgba(138, 180, 248, 0.08);
        border-color: #aecbfa;
        color: #aecbfa !important;
        box-shadow: none;
        transform: translateY(-1px);
    }
    
    /* Disabled Buttons */
    .stButton>button:disabled {
        border: 1px solid #444746;
        color: #80868b !important;
        background-color: transparent;
        transform: none;
    }
    
    /* Fix Input Boxes (Dropdowns and Text Inputs) */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div {
        background-color: #282a2d !important;
        border: 1px solid #444746 !important;
        border-radius: 8px !important;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #9aa0a6 !important; 
        font-size: 16px;
        font-weight: 500;
        padding-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #e3e3e3 !important;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #8ab4f8;
        color: #8ab4f8 !important; 
    }
</style>
""", unsafe_allow_html=True)

# --- SECURE LOGIN SCREEN ---
if 'username' not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #8ab4f8;'>🔐 SECURE MAINFRAME</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Enter your Player Tag and 4-Digit PIN to connect to the server.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_input = st.text_input("Player Tag").strip()
        pin_input = st.text_input("4-Digit PIN", type="password").strip()
        
        if st.button("Connect to Server", use_container_width=True):
            if user_input and pin_input:
                response = supabase.table("players").select("*").eq("username", user_input).execute()
                if response.data:
                    if response.data[0]['pin'] == pin_input:
                        st.session_state['username'] = user_input
                        st.rerun()
                    else:
                        st.error("❌ Access Denied. Invalid PIN.")
                else:
                    supabase.table("players").insert({"username": user_input, "pin": pin_input}).execute()
                    st.success("New agent registered!")
                    st.session_state['username'] = user_input
                    st.rerun()
            else:
                st.warning("Missing credentials.")
    st.stop()

# --- MAIN APP ---
current_user = st.session_state['username']
st.sidebar.markdown(f"### 🕹️ Agent: <span style='color:#8ab4f8;'>{current_user}</span>", unsafe_allow_html=True)
if st.sidebar.button("Disconnect"):
    del st.session_state['username']
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Match Settings")
selected_subject = st.sidebar.selectbox("Queue Select", ["GK (Polity, History, etc.)", "Math (Quant)", "English Comprehension", "General Intelligence (Reasoning)"])
difficulty = st.sidebar.selectbox("Difficulty Tier", ["Easy", "Moderate", "Hard"])
test_time_limit = st.sidebar.slider("Match Timer (Minutes)", 10, 60, 30)

st.title(f"⚡ RADIANT: SSC Combat Arena")

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
        st.warning("🔄 Reconnected to active match!")

tab1, tab2, tab3 = st.tabs(["🎮 Ranked Match", "🏅 Global Top 500", "📼 VOD Reviews"])

with tab1:
    response = supabase.table("error_log").select("topic").eq("username", current_user).execute()
    weakest_topic = None

    if response.data:
        topics = [row['topic'] for row in response.data]
        topic_counts = Counter(topics)
        weakest_topic = topic_counts.most_common(1)[0][0]
        st.error(f"💀 **AI Analytics:** You are bottom-fragging in **{weakest_topic}**. Queue this up to fix your accuracy.")

    if 'current_test' not in st.session_state and 'review_data' not in st.session_state:
        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            start_standard = st.button(f"🎯 Queue Standard Match", use_container_width=True)
        with col2:
            start_weakest = st.button("🔥 Queue Weakness Drill", disabled=not weakest_topic, use_container_width=True)

        def generate_ai_test(focus_topic):
            with st.spinner(f"Generating a {difficulty} match for {focus_topic}..."):
                prompt = f"Generate a 25-question multiple-choice test for SSC CGL level. Subject: {focus_topic}. Difficulty Level: {difficulty}. Return ONLY valid JSON format as a list of dictionaries with exactly these keys: 'question', 'options' (list of 4 strings), 'answer' (the exact correct option string), and 'explanation' (a detailed 2-sentence explanation)."
                try:
                    ai_response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                    raw_text = ai_response.text.replace("```json", "").replace("```", "").strip()
                    test_data = json.loads(raw_text)
                    
                    supabase.table("active_sessions").upsert({
                        "username": current_user,
                        "test_data": test_data,
                        "start_time": time.time(),
                        "focus_topic": focus_topic,
                        "difficulty": difficulty
                    }).execute()

                    st.session_state['current_test'] = test_data
                    st.session_state['start_time'] = time.time()
                    st.session_state['current_focus'] = focus_topic
                    st.session_state['current_difficulty'] = difficulty
                    
                    st.session_state['q_index'] = 0
                    st.session_state['answers'] = {i: None for i in range(len(test_data))}
                    st.rerun() 
                except Exception as e:
                    st.error(f"Matchmaking failed. Try again.")

        if start_standard:
            generate_ai_test(selected_subject)
        elif start_weakest and weakest_topic:
            generate_ai_test(weakest_topic)

    if 'current_test' in st.session_state:
        st.write("---")
        diff_label = st.session_state.get('current_difficulty', 'Unknown')
        
        timer_html = f"""
        <div style="background-color: #1e1f22; color: #8ab4f8; padding: 10px; border-radius: 8px; text-align: center; font-family: monospace; font-size: 24px; font-weight: bold; border: 1px solid #444746; margin-bottom: 15px; box-shadow: 0 0 10px rgba(138, 180, 248, 0.1);">
            <span id="clock">⏳ Syncing Timer...</span>
        </div>
        <script>
            var countDownDate = new Date().getTime() + ({test_time_limit} * 60 * 1000);
            var x = setInterval(function() {{
                var now = new Date().getTime();
                var distance = countDownDate - now;
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                
                if(seconds < 10) {{ seconds = "0" + seconds; }}
                
                document.getElementById("clock").innerHTML = "⏱️ Time Remaining: " + minutes + ":" + seconds;
                if (distance < 0) {{
                    clearInterval(x);
                    document.getElementById("clock").innerHTML = "🚨 MATCH OVER! SUBMIT NOW!";
                }}
            }}, 1000);
        </script>
        """
        components.html(timer_html, height=75)

        col_main, col_palette = st.columns([3, 1], gap="large")
        
        test_questions = st.session_state['current_test']
        current_idx = st.session_state['q_index']
        q_data = test_questions[current_idx]
        
        with col_main:
            st.markdown(f"<h3 style='color: #8ab4f8;'>Target {current_idx + 1} / {len(test_questions)}</h3>", unsafe_allow_html=True)
            st.write(f"**{q_data['question']}**")
            
            options = q_data['options']
            default_idx = options.index(st.session_state['answers'][current_idx]) if st.session_state['answers'][current_idx] in options else None
            selected_option = st.radio("Lock in your answer:", options, index=default_idx, key=f"radio_{current_idx}")
            
            if selected_option:
                st.session_state['answers'][current_idx] = selected_option
                
            st.write("---")
            nav_col1, nav_col2, nav_col3 = st.columns(3)
            with nav_col1:
                if st.button("⬅️ Previous Target", use_container_width=True) and current_idx > 0:
                    st.session_state['q_index'] -= 1
                    st.rerun()
            with nav_col2:
                if st.button("🗑️ Clear Selection", use_container_width=True):
                    st.session_state['answers'][current_idx] = None
                    st.rerun()
            with nav_col3:
                if st.button("Save & Next ➡️", use_container_width=True) and current_idx < len(test_questions) - 1:
                    st.session_state['q_index'] += 1
                    st.rerun()
                    
        with col_palette:
            st.markdown("### 🗺️ HUD Grid")
            st.write("🔵 Locked | ⚪ Blank")
            
            grid_cols = st.columns(5)
            for i in range(len(test_questions)):
                col_i = i % 5
                status_emoji = "🔵" if st.session_state['answers'][i] else "⚪"
                if grid_cols[col_i].button(f"{status_emoji} {i+1}", key=f"navbtn_{i}"):
                    st.session_state['q_index'] = i
                    st.rerun()
                    
            st.write("---")
            if st.button("🛑 END MATCH & SUBMIT", use_container_width=True):
                score = 0
                time_spent = round((time.time() - st.session_state['start_time']) / 60, 2)
                review_data = []

                for i, q in enumerate(test_questions):
                    ans = st.session_state['answers'][i]
                    status = "Unattempted ⚪"
                    
                    if ans == q['answer']:
                        score += 1
                        status = "Correct ✅"
                    elif ans is not None:
                        status = "Wrong ❌"
                        supabase.table("error_log").insert({
                            "username": current_user,
                            "topic": st.session_state['current_focus'],
                            "question": q['question'],
                            "correct_answer": q['answer']
                        }).execute()
                    
                    review_data.append({
                        "question": q['question'],
                        "your_answer": ans if ans else "Left Blank",
                        "correct_answer": q['answer'],
                        "status": status,
                        "explanation": q.get('explanation', 'Data corrupted. No explanation generated.')
                    })
                
                total_q = len(test_questions)
                
                supabase.table("test_history").insert({
                    "username": current_user,
                    "subject": st.session_state['current_focus'],
                    "score": score,
                    "total": total_q,
                    "review_data": review_data
                }).execute()
                
                supabase.table("active_sessions").delete().eq("username", current_user).execute()
                
                st.session_state['review_data'] = review_data
                st.session_state['last_score'] = score
                st.session_state['last_total'] = total_q
                st.session_state['time_spent'] = time_spent
                
                del st.session_state['current_test']
                del st.session_state['q_index']
                del st.session_state['answers']
                st.rerun()

    if 'review_data' in st.session_state:
        st.write("---")
        st.header("📊 Post-Match Combat Report")
        st.subheader(f"Final Score: {st.session_state['last_score']} / {st.session_state['last_total']} (Time: {st.session_state['time_spent']} mins)")
        
        for i, data in enumerate(st.session_state['review_data']):
            with st.expander(f"Target {i+1}: {data['status']}"):
                st.write(f"**Question:** {data['question']}")
                st.write(f"**Your Answer:** {data['your_answer']}")
                st.write(f"**Correct Answer:** {data['correct_answer']}")
                st.info(f"💡 **Intel:** {data['explanation']}")

        if st.button("Return to Lobby", use_container_width=True):
            del st.session_state['review_data']
            st.rerun()

with tab2:
    st.subheader("🏆 Radiant Rankings")
    history_response = supabase.table("test_history").select("*").order("created_at", desc=True).limit(50).execute()
    
    if history_response.data:
        df = pd.DataFrame(history_response.data)
        df['Accuracy'] = (df['score'] / df['total'] * 100).round(1).astype(str) + '%'
        
        st.write("### 🥇 Top Agents")
        leaderboard = df.sort_values(by='score', ascending=False).head(10)
        st.dataframe(leaderboard[['username', 'subject', 'score', 'total', 'Accuracy']], use_container_width=True, hide_index=True)
    else:
        st.info("Leaderboard is empty. Secure the first win.")

with tab3:
    st.subheader(f"📼 {current_user}'s Personal VODs")
    past_tests = supabase.table("test_history").select("*").eq("username", current_user).order("created_at", desc=True).execute()
    
    if past_tests.data:
        for test in past_tests.data:
            date_str = str(test['created_at'])[:10]
            score_ratio = f"{test['score']}/{test['total']}"
            
            with st.expander(f"📅 {date_str} | {test['subject']} | Score: {score_ratio}"):
                if test.get('review_data'):
                    for i, q_data in enumerate(test['review_data']):
                        st.markdown(f"**Target {i+1}: {q_data['question']}** ({q_data['status']})")
                        st.write(f"**Your Answer:** {q_data['your_answer']} | **Correct:** {q_data['correct_answer']}")
                        st.success(f"💡 {q_data.get('explanation', 'Data corrupted.')}")
                        st.divider()
    else:
        st.info("No match history found. Get in the arena.")