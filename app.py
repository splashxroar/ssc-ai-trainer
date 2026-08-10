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
                    st.error(f"Failed to generate test. Try again.")

        if start_standard:
            generate_ai_test(selected_subject)
        elif start_weakest and weakest_topic:
            generate_ai_test(weakest_topic)

    if 'current_test' in st.session_state:
        st.write("---")
        diff_label = st.session_state.get('current_difficulty', 'Unknown')
        
        timer_html = f"""
        <div style="background-color: #1e1e2f; color: #ff4b4b; padding: 10px; border-radius: 5px; text-align: center; font-family: monospace; font-size: 22px; font-weight: bold; border: 1px solid #ff4b4b; margin-bottom: 10px; box-shadow: 0 0 10px rgba(255, 75, 75, 0.2);">
            <span id="clock">⏳ Loading Timer...</span>
        </div>
        <script>
            var countDownDate = new Date().getTime() + ({test_time_limit} * 60 * 1000);
            var x = setInterval(function() {{
                var now = new Date().getTime();
                var distance = countDownDate - now;
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                document.getElementById("clock").innerHTML = "⏱️ Time Left: " + minutes + "m " + seconds + "s";
                if (distance < 0) {{
                    clearInterval(x);
                    document.getElementById("clock").innerHTML = "🚨 TIME IS UP! SUBMIT NOW!";
                }}
            }}, 1000);
        </script>
        """
        components.html(timer_html, height=65)

        col_main, col_palette = st.columns([3, 1], gap="large")
        
        test_questions = st.session_state['current_test']
        current_idx = st.session_state['q_index']
        q_data = test_questions[current_idx]
        
        with col_main:
            st.markdown(f"<h3 style='color: #ff4b4b;'>Question {current_idx + 1} of {len(test_questions)}</h3>", unsafe_allow_html=True)
            st.write(f"**{q_data['question']}**")
            
            options = q_data['options']
            default_idx = options.index(st.session_state['answers'][current_idx]) if st.session_state['answers'][current_idx] in options else None
            selected_option = st.radio("Choose your answer:", options, index=default_idx, key=f"radio_{current_idx}")
            
            if selected_option:
                st.session_state['answers'][current_idx] = selected_option
                
            st.write("---")
            nav_col1, nav_col2, nav_col3 = st.columns(3)
            with nav_col1:
                if st.button("⬅️ Previous", use_container_width=True) and current_idx > 0:
                    st.session_state['q_index'] -= 1
                    st.rerun()
            with nav_col2:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state['answers'][current_idx] = None
                    st.rerun()
            with nav_col3:
                if st.button("Save & Next ➡️", use_container_width=True) and current_idx < len(test_questions) - 1:
                    st.session_state['q_index'] += 1
                    st.rerun()
                    
        with col_palette:
            st.markdown("### 🗺️ Palette")
            st.write("🟩 Answered | ⬜ Blank")
            
            grid_cols = st.columns(5)
            for i in range(len(test_questions)):
                col_i = i % 5
                status_emoji = "🟩" if st.session_state['answers'][i] else "⬜"
                if grid_cols[col_i].button(f"{status_emoji} {i+1}", key=f"navbtn_{i}"):
                    st.session_state['q_index'] = i
                    st.rerun()
                    
            st.write("---")
            if st.button("🚨 SUBMIT EXAM", use_container_width=True):
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
                        "explanation": q.get('explanation', 'No explanation.')
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
        st.header("📋 Post-Match Review")
        st.subheader(f"Score: {st.session_state['last_score']} / {st.session_state['last_total']} (Time: {st.session_state['time_spent']} mins)")
        
        for i, data in enumerate(st.session_state['review_data']):
            with st.expander(f"Q{i+1}: {data['status']}"):
                st.write(f"**Question:** {data['question']}")
                st.write(f"**Your Answer:** {data['your_answer']}")
                st.write(f"**Correct Answer:** {data['correct_answer']}")
                st.info(f"💡 **Explanation:** {data['explanation']}")

        if st.button("Close Review & Go Back to Arena", use_container_width=True):
            del st.session_state['review_data']
            st.rerun()

with tab2:
    st.subheader("🏆 Global Leaderboard")
    history_response = supabase.table("test_history").select("*").order("created_at", desc=True).limit(50).execute()
    
    if history_response.data:
        df = pd.DataFrame(history_response.data)
        df['Accuracy'] = (df['score'] / df['total'] * 100).round(1).astype(str) + '%'
        
        st.write("### 🥇 Top Scores")
        leaderboard = df.sort_values(by='score', ascending=False).head(10)
        st.dataframe(leaderboard[['username', 'subject', 'score', 'total', 'Accuracy']], use_container_width=True, hide_index=True)
    else:
        st.info("No tests have been taken yet.")

with tab3:
    st.subheader(f"📺 {current_user}'s Match VODs (Past Tests)")
    past_tests = supabase.table("test_history").select("*").eq("username", current_user).order("created_at", desc=True).execute()
    
    if past_tests.data:
        for test in past_tests.data:
            date_str = str(test['created_at'])[:10]
            score_ratio = f"{test['score']}/{test['total']}"
            
            with st.expander(f"📅 {date_str} | {test['subject']} | Score: {score_ratio}"):
                if test.get('review_data'):
                    for i, q_data in enumerate(test['review_data']):
                        st.markdown(f"**Q{i+1}: {q_data['question']}** ({q_data['status']})")
                        st.write(f"**Your Answer:** {q_data['your_answer']} | **Correct:** {q_data['correct_answer']}")
                        st.success(f"💡 {q_data.get('explanation', 'No explanation.')}")
                        st.divider()
    else:
        st.info("You haven't taken any tests to review yet.")