import streamlit as st
import os
import json
import time
import base64
import random
import string
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

st.set_page_config(page_title="SSC Mock Assessment Portal", layout="wide", initial_sidebar_state="expanded")

# --- 🎨 PROFESSIONAL MINIMALIST UI INJECTION ---
st.markdown("""
<style>
    .stApp { background-color: #0f1115; color: #e2e8f0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    h1, h2, h3, h4, h5 { color: #f8fafc !important; font-weight: 500; letter-spacing: -0.5px; }
    #MainMenu, footer {visibility: hidden;}
    header {background-color: transparent !important;} 
    
    [data-testid="stSidebar"] { background-color: #1a1d24; border-right: 1px solid #2d3748; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    
    .stButton>button {
        border-radius: 6px; border: 1px solid #3b82f6; background-color: #3b82f6;
        color: #ffffff !important; font-weight: 500; padding: 6px 24px; transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #2563eb; border-color: #2563eb; color: #ffffff !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transform: translateY(-1px);
    }
    .stButton>button:disabled { border: 1px solid #475569; color: #94a3b8 !important; background-color: #334155; transform: none; box-shadow: none; }
    
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea {
        background-color: #1e293b !important; border: 1px solid #475569 !important; border-radius: 6px !important; color: #f1f5f9 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 32px; border-bottom: 1px solid #2d3748; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #94a3b8 !important; font-size: 15px; font-weight: 500; padding-bottom: 12px; border-radius: 0; }
    .stTabs [data-baseweb="tab"]:hover { color: #f8fafc !important; }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid #3b82f6; color: #3b82f6 !important; }
    
    .typing-box { background-color: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 8px; font-family: 'Courier New', Courier, monospace; font-size: 16px; line-height: 1.6; color: #e2e8f0; margin-bottom: 20px; }
    .streamlit-expanderHeader { background-color: #1e293b !important; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

TYPING_PASSAGES = [
    "The Constitution of India is the supreme law of India. The document lays down the framework that demarcates fundamental political code, structure, procedures, powers, and duties of government institutions and sets out fundamental rights, directive principles, and the duties of citizens.",
    "The Industrial Revolution marked a period of development in the latter half of the 18th century that transformed largely rural, agrarian societies in Europe and America into industrialized, urban ones.",
    "Monetary policy refers to the actions undertaken by a nation's central bank to control money supply and achieve sustainable economic growth. In India, the Reserve Bank of India utilizes tools like the Repo Rate."
]

# --- LOGIN SCREEN ---
if 'username' not in st.session_state:
    st.markdown("<h2 style='text-align: center; color: #3b82f6; margin-top: 50px;'>System Authentication</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8;'>Please enter your Candidate ID and PIN to access the assessment portal.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_input = st.text_input("Candidate ID").strip()
        pin_input = st.text_input("4-Digit PIN", type="password").strip()
        
        if st.button("Authenticate", use_container_width=True):
            if user_input and pin_input:
                response = supabase.table("players").select("*").eq("username", user_input).execute()
                if response.data:
                    if response.data[0]['pin'] == pin_input:
                        st.session_state['username'] = user_input
                        st.rerun()
                    else:
                        st.error("Authentication failed. Invalid PIN.")
                else:
                    supabase.table("players").insert({"username": user_input, "pin": pin_input, "last_seen": time.time()}).execute()
                    st.session_state['username'] = user_input
                    st.rerun()
            else:
                st.warning("Credentials required.")
    st.stop()

# --- MAIN APP ---
current_user = st.session_state['username']
supabase.table("players").update({"last_seen": time.time()}).eq("username", current_user).execute()
player_data = supabase.table("players").select("*").eq("username", current_user).execute().data[0]
avatar_base64 = player_data.get("avatar")

if avatar_base64:
    st.sidebar.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{avatar_base64}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 2px solid #3b82f6; margin-bottom: 15px;"></div>', unsafe_allow_html=True)
else:
    st.sidebar.markdown(f'<div style="text-align: center;"><div style="width: 100px; height: 100px; border-radius: 50%; background-color: #1e293b; border: 1px solid #475569; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 15px; margin-left: auto; margin-right: auto;"><span style="color: #94a3b8; font-size: 32px;">User</span></div></div>', unsafe_allow_html=True)

st.sidebar.markdown(f"<h4 style='text-align: center;'>Candidate: {current_user}</h4>", unsafe_allow_html=True)
if st.sidebar.button("Sign Out", use_container_width=True):
    del st.session_state['username']
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Assessment Configuration")
selected_subject = st.sidebar.selectbox("Subject Selection", ["GK (Polity, History, etc.)", "Math (Quant)", "English Comprehension", "General Intelligence (Reasoning)"])

specific_chapter = None
if selected_subject == "Math (Quant)": specific_chapter = st.sidebar.selectbox("Module", ["Mixed (All Chapters)", "Number System", "Percentage", "Ratio & Proportion", "Time & Work", "Time, Speed & Distance", "Algebra", "Geometry", "Trigonometry", "Mensuration", "Data Interpretation"])
elif selected_subject == "GK (Polity, History, etc.)": specific_chapter = st.sidebar.selectbox("Module", ["Mixed (All Chapters)", "History", "Polity", "Geography", "Economics", "Physics", "Chemistry", "Biology", "Current Affairs", "Static GK"])
elif selected_subject == "English Comprehension": specific_chapter = st.sidebar.selectbox("Module", ["Mixed (All Chapters)", "Reading Comprehension", "Cloze Test", "Synonyms & Antonyms", "Idioms & Phrases", "Spotting Errors", "Active/Passive Voice", "Direct/Indirect Speech"])
elif selected_subject == "General Intelligence (Reasoning)": specific_chapter = st.sidebar.selectbox("Module", ["Mixed (All Chapters)", "Coding-Decoding", "Blood Relations", "Syllogism", "Number Series", "Venn Diagrams", "Non-Verbal Reasoning", "Matrix"])

num_questions = st.sidebar.selectbox("Question Count", [10, 15, 25, 50])
difficulty = st.sidebar.selectbox("Difficulty Level", ["Easy", "Moderate", "Hard"])
test_time_limit = st.sidebar.slider("Time Limit (Minutes)", 10, 120, 30)

st.title("SSC Mock Assessment Portal")

# AUTO-SAVE RECOVERY
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
        st.session_state['q_times'] = {i: 0.0 for i in range(len(st.session_state['current_test']))}
        st.session_state['last_tick'] = time.time()
        st.info("Previous assessment session recovered.")

tab1, tab2, tab3, tab4 = st.tabs(["Assessment", "Typing Test", "Leaderboard", "Agent Profile & Logs"])

# --- TAB 1: ASSESSMENT ---
with tab1:
    if 'current_test' not in st.session_state and 'review_data' not in st.session_state:
        response = supabase.table("error_log").select("topic").eq("username", current_user).execute()
        weakest_topic = None
        if response.data:
            topics = [row['topic'] for row in response.data]
            topic_counts = Counter(topics)
            weakest_topic = topic_counts.most_common(1)[0][0]
            st.warning(f"System Analytics: Recommended focus area is {weakest_topic} based on historical error rates.")

        col1, col2 = st.columns(2)
        with col1: start_standard = st.button(f"Initialize Assessment ({num_questions} Questions)", use_container_width=True)
        with col2: start_weakest = st.button(f"Initialize Remedial Assessment", disabled=not weakest_topic, use_container_width=True)
        
        st.divider()
        st.markdown("#### Peer Assessment Synchronization")
        duel_col1, duel_col2 = st.columns(2)
        with duel_col1:
            if st.button("Generate Synchronization Code", use_container_width=True): st.session_state['hosting_duel'] = True
        with duel_col2:
            join_code = st.text_input("Enter 4-Character Code:", max_chars=4, label_visibility="collapsed", placeholder="Enter 4-Character Code").upper()
            if st.button("Synchronize Session", use_container_width=True):
                if join_code:
                    with st.spinner("Synchronizing..."):
                        lobby_data = supabase.table("custom_lobbies").select("*").eq("room_code", join_code).execute()
                        if lobby_data.data:
                            room = lobby_data.data[0]
                            supabase.table("active_sessions").upsert({"username": current_user, "test_data": room['test_data'], "start_time": time.time(), "focus_topic": room['focus_topic'], "difficulty": room['difficulty']}).execute()
                            st.session_state['current_test'] = room['test_data']
                            st.session_state['start_time'] = time.time()
                            st.session_state['current_focus'] = room['focus_topic']
                            st.session_state['current_difficulty'] = room['difficulty']
                            st.session_state['q_index'] = 0
                            st.session_state['answers'] = {i: None for i in range(len(room['test_data']))}
                            st.session_state['q_times'] = {i: 0.0 for i in range(len(room['test_data']))}
                            st.session_state['last_tick'] = time.time()
                            st.rerun()
                        else: st.error("Invalid synchronization code.")

        def generate_ai_test(focus_topic, is_duel=False):
            actual_topic = f"{focus_topic} - strictly focusing on {specific_chapter}" if specific_chapter != "Mixed (All Chapters)" else focus_topic
            
            # THE ADVANCED MEMORY BANK: Force AI to swap numbers on recent questions
            past_history = supabase.table("test_history").select("review_data").order("created_at", desc=True).limit(2).execute()
            avoid_text = ""
            if past_history.data:
                avoid_list = [q['question'] for test in past_history.data for q in test.get('review_data', [])]
                if avoid_list: 
                    avoid_text = f" CRITICAL RULE: DO NOT repeat these exact questions verbatim. You CAN use the exact same logic patterns and question formats, but you MUST change the numbers, names, and data points so the final answers are different: {' | '.join(avoid_list[:20])}"

            with st.spinner(f"Compiling {num_questions} unique questions for {actual_topic}..."):
                prompt = f"Generate a {num_questions}-question multiple-choice test for SSC CGL level. Subject: {actual_topic}. Difficulty Level: {difficulty}. {avoid_text} Return ONLY valid JSON format as a list of dictionaries with keys: 'question', 'options' (list of 4 strings), 'answer' (exact string), and 'explanation'. Seed: {time.time()}."
                try:
                    ai_response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                    raw_text = ai_response.text.replace("```json", "").replace("```", "").strip()
                    test_data = json.loads(raw_text)
                    
                    if is_duel:
                        room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                        supabase.table("custom_lobbies").insert({"room_code": room_code, "test_data": test_data, "focus_topic": actual_topic, "difficulty": difficulty}).execute()
                        st.session_state['room_code_created'] = room_code
                        st.success(f"Synchronization Code generated: {room_code}")
                    else:
                        supabase.table("active_sessions").upsert({"username": current_user, "test_data": test_data, "start_time": time.time(), "focus_topic": actual_topic, "difficulty": difficulty}).execute()
                        st.session_state['current_test'] = test_data
                        st.session_state['start_time'] = time.time()
                        st.session_state['current_focus'] = actual_topic
                        st.session_state['current_difficulty'] = difficulty
                        st.session_state['q_index'] = 0
                        st.session_state['answers'] = {i: None for i in range(len(test_data))}
                        st.session_state['q_times'] = {i: 0.0 for i in range(len(test_data))}
                        st.session_state['last_tick'] = time.time()
                        st.rerun() 
                except Exception as e: st.error("Compilation failed. The AI timed out creating unique questions. Try again.")
                    
        if start_standard: generate_ai_test(selected_subject, is_duel=False)
        if start_weakest and weakest_topic: generate_ai_test(weakest_topic, is_duel=False)
        if st.session_state.get('hosting_duel'): 
            generate_ai_test(selected_subject, is_duel=True)
            st.session_state['hosting_duel'] = False

    if 'current_test' in st.session_state:
        # TIMING CALCULATOR ENGINE
        now = time.time()
        if 'last_tick' not in st.session_state: st.session_state['last_tick'] = now
        if 'q_times' not in st.session_state: st.session_state['q_times'] = {i: 0.0 for i in range(len(st.session_state['current_test']))}
        
        elapsed = now - st.session_state['last_tick']
        st.session_state['q_times'][st.session_state['q_index']] += elapsed
        st.session_state['last_tick'] = now

        st.write("---")
        timer_html = f"""
        <div style="background-color: #1e293b; color: #f8fafc; padding: 12px; border-radius: 6px; text-align: center; font-family: 'Inter', sans-serif; font-size: 20px; font-weight: 500; border: 1px solid #334155; margin-bottom: 20px;">
            <span id="clock">Initializing Timekeeper...</span>
        </div>
        <script>
            var countDownDate = new Date().getTime() + ({test_time_limit} * 60 * 1000);
            var x = setInterval(function() {{
                var now = new Date().getTime();
                var distance = countDownDate - now;
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                if(seconds < 10) {{ seconds = "0" + seconds; }}
                document.getElementById("clock").innerHTML = "Time Remaining: " + minutes + ":" + seconds;
                if (distance < 0) {{ clearInterval(x); document.getElementById("clock").innerHTML = "ASSESSMENT CONCLUDED"; }}
            }}, 1000);
        </script>
        """
        components.html(timer_html, height=75)

        col_main, col_palette = st.columns([3, 1], gap="large")
        test_questions = st.session_state['current_test']
        current_idx = st.session_state['q_index']
        q_data = test_questions[current_idx]
        
        with col_main:
            st.markdown(f"<h4 style='color: #94a3b8;'>Question {current_idx + 1} of {len(test_questions)} <span style='font-size: 14px; float: right;'>⏱️ {round(st.session_state['q_times'][current_idx], 1)}s</span></h4>", unsafe_allow_html=True)
            st.write(f"**{q_data['question']}**")
            options = q_data['options']
            default_idx = options.index(st.session_state['answers'][current_idx]) if st.session_state['answers'][current_idx] in options else None
            selected_option = st.radio("Select option:", options, index=default_idx, key=f"radio_{current_idx}", label_visibility="collapsed")
            if selected_option: st.session_state['answers'][current_idx] = selected_option
                
            st.write("---")
            nav_col1, nav_col2, nav_col3 = st.columns(3)
            with nav_col1:
                if st.button("Previous", use_container_width=True) and current_idx > 0: st.session_state['q_index'] -= 1; st.rerun()
            with nav_col2:
                if st.button("Clear Selection", use_container_width=True): st.session_state['answers'][current_idx] = None; st.rerun()
            with nav_col3:
                if st.button("Save & Next", use_container_width=True) and current_idx < len(test_questions) - 1: st.session_state['q_index'] += 1; st.rerun()
                    
        with col_palette:
            st.markdown("#### Navigation Palette")
            st.write("🟦 Answered | ⬜ Unanswered")
            grid_cols = st.columns(5)
            for i in range(len(test_questions)):
                col_i = i % 5
                status_emoji = "🟦" if st.session_state['answers'][i] else "⬜"
                if grid_cols[col_i].button(f"{status_emoji} {i+1}", key=f"navbtn_{i}"): st.session_state['q_index'] = i; st.rerun()
                    
            st.write("---")
            if st.button("Submit Assessment", use_container_width=True):
                score = 0
                time_spent = round((time.time() - st.session_state['start_time']) / 60, 2)
                review_data = []
                for i, q in enumerate(test_questions):
                    ans = st.session_state['answers'][i]
                    status = "Unattempted"
                    if ans == q['answer']:
                        score += 1
                        status = "Correct"
                    elif ans is not None:
                        status = "Incorrect"
                        supabase.table("error_log").insert({"username": current_user, "topic": st.session_state['current_focus'], "question": q['question'], "correct_answer": q['answer']}).execute()
                    
                    q_time = round(st.session_state['q_times'].get(i, 0.0), 1)
                    review_data.append({"question": q['question'], "your_answer": ans if ans else "Omitted", "correct_answer": q['answer'], "status": status, "time_taken": q_time, "explanation": q.get('explanation', 'Explanation unavailable.')})
                
                total_q = len(test_questions)
                supabase.table("test_history").insert({"username": current_user, "subject": st.session_state['current_focus'], "score": score, "total": total_q, "time_spent": time_spent, "review_data": review_data}).execute()
                supabase.table("active_sessions").delete().eq("username", current_user).execute()
                
                st.session_state['review_data'] = review_data
                st.session_state['last_score'] = score
                st.session_state['last_total'] = total_q
                st.session_state['time_spent'] = time_spent
                del st.session_state['current_test'], st.session_state['q_index'], st.session_state['answers'], st.session_state['q_times'], st.session_state['last_tick']
                st.rerun()

    if 'review_data' in st.session_state:
        st.write("---")
        st.header("Assessment Report")
        st.write(f"**Final Score:** {st.session_state['last_score']} / {st.session_state['last_total']} | **Duration:** {st.session_state['time_spent']} minutes")
        for i, data in enumerate(st.session_state['review_data']):
            with st.expander(f"Question {i+1}: {data['status']} (⏱️ {data.get('time_taken', 0)}s)"):
                st.write(f"**Question:** {data['question']}")
                st.write(f"**Selected Answer:** {data['your_answer']} | **Correct Answer:** {data['correct_answer']}")
                st.info(f"**Explanation:** {data['explanation']}")
        if st.button("Return to Dashboard", use_container_width=True):
            del st.session_state['review_data']
            st.rerun()

# --- TAB 2: TYPING SPEED ---
with tab2:
    st.subheader("Typing Speed Assessment")
    st.write("Evaluate WPM and Accuracy based on standard SSC guidelines (5 keystrokes = 1 word).")
    if 'typing_prompt' not in st.session_state: st.session_state['typing_prompt'] = random.choice(TYPING_PASSAGES)
    st.markdown(f'<div class="typing-box">{st.session_state["typing_prompt"]}</div>', unsafe_allow_html=True)
    
    col_start, col_new = st.columns(2)
    with col_start:
        if st.button("Initialize Typing Module", use_container_width=True): st.session_state['typing_start_time'] = time.time(); st.session_state['typing_active'] = True; st.rerun()
    with col_new:
        if st.button("Cycle Text Passage", use_container_width=True): st.session_state['typing_prompt'] = random.choice(TYPING_PASSAGES); st.rerun()

    if st.session_state.get('typing_active'):
        typed_input = st.text_area("Input text...", height=150, label_visibility="collapsed")
        if st.button("Conclude & Submit", use_container_width=True):
            time_spent_sec = max(time.time() - st.session_state.get('typing_start_time', time.time()), 1)
            prompt_text, typed_text = st.session_state['typing_prompt'], typed_input.strip()
            wpm = round((len(typed_text) / 5) / (time_spent_sec / 60), 1)
            accuracy = round((sum(1 for a, b in zip(prompt_text, typed_text) if a == b) / max(len(prompt_text), 1)) * 100, 1)
            supabase.table("typing_leaderboard").insert({"username": current_user, "wpm": wpm, "accuracy": accuracy, "time_spent": round(time_spent_sec, 1)}).execute()
            st.success(f"Metrics Recorded — Speed: {wpm} WPM | Accuracy: {accuracy}% | Duration: {round(time_spent_sec, 1)}s")
            st.session_state['typing_active'] = False; st.rerun()

    st.write("#### Typing Evaluation Records")
    typing_scores = supabase.table("typing_leaderboard").select("*").order("wpm", desc=True).limit(10).execute()
    if typing_scores.data: st.dataframe(pd.DataFrame(typing_scores.data)[['username', 'wpm', 'accuracy', 'time_spent']], use_container_width=True, hide_index=True)

# --- TAB 3: LEADERBOARDS ---
with tab3:
    history_response = supabase.table("test_history").select("*").limit(5000).execute()
    if history_response.data:
        df = pd.DataFrame(history_response.data)
        df['time_spent'] = df.get('time_spent', 0.0).fillna(0)
        
        st.write("#### Official Leaderboard (25+ Question Assessments)")
        df_ranked = df[df['total'] >= 25].copy()
        if not df_ranked.empty:
            df_ranked['Accuracy'] = (df_ranked['score'] / df_ranked['total'] * 100).round(1).astype(str) + '%'
            df_ranked['Avg Time/Q (sec)'] = ((df_ranked['time_spent'] * 60) / df_ranked['total']).round(1)
            
            lb_tabs = st.tabs(["Quantitative", "General Awareness", "Reasoning", "English", "Composite"])
            def render_lb(filtered_df):
                if not filtered_df.empty: st.dataframe(filtered_df.sort_values(by=['score', 'Avg Time/Q (sec)'], ascending=[False, True]).head(20)[['username', 'subject', 'score', 'total', 'Accuracy', 'Avg Time/Q (sec)']], use_container_width=True, hide_index=True)
                else: st.info("Insufficient data.")
            with lb_tabs[0]: render_lb(df_ranked[df_ranked['subject'].str.contains("Math", na=False)])
            with lb_tabs[1]: render_lb(df_ranked[df_ranked['subject'].str.contains("GK", na=False)])
            with lb_tabs[2]: render_lb(df_ranked[df_ranked['subject'].str.contains("Reasoning", na=False)])
            with lb_tabs[3]: render_lb(df_ranked[df_ranked['subject'].str.contains("English", na=False)])
            with lb_tabs[4]: render_lb(df_ranked)
        else: st.write("Standardized criteria not met. Log 25+ question assessments to populate.")
    else: st.info("System records are currently empty.")

# --- TAB 4: PROFILE & HISTORY ---
with tab4:
    st.subheader("Global Player Database & Archives")
    all_players = supabase.table("players").select("username").execute()
    player_list = [p['username'] for p in all_players.data]
    inspect_target = st.selectbox("Select Candidate to Inspect Profile & Match History", player_list, index=player_list.index(current_user) if current_user in player_list else 0)
    
    target_data = supabase.table("players").select("*").eq("username", inspect_target).execute().data[0]
    col_id1, col_id2 = st.columns([1, 4])
    with col_id1:
        target_avatar = target_data.get("avatar")
        if target_avatar: st.markdown(f'<img src="data:image/png;base64,{target_avatar}" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 2px solid #3b82f6;">', unsafe_allow_html=True)
        else: st.write("👤 No ID Photo")
    with col_id2:
        st.write(f"**Candidate:** {inspect_target}")
        st.write(f"**Bio:** {target_data.get('bio', 'No background provided.')}")
        
    st.divider()
    st.write(f"#### {inspect_target}'s Attempted Question Archive")
    past_tests = supabase.table("test_history").select("*").eq("username", inspect_target).order("created_at", desc=True).execute()
    if past_tests.data:
        for test in past_tests.data:
            time_display = f" | {round(test.get('time_spent', 0), 2)} mins total" if test.get('time_spent', 0) else ""
            with st.expander(f"{str(test['created_at'])[:10]} | {test['subject']} | Score: {test['score']}/{test['total']}{time_display}"):
                if test.get('review_data'):
                    for i, q in enumerate(test['review_data']):
                        q_time = q.get('time_taken', 0)
                        st.write(f"**Q{i+1} (⏱️ {q_time}s):** {q['question']}")
                        st.write(f"Selected: {q['your_answer']} | Correct: {q['correct_answer']}")
                        st.divider()
    else:
        st.write(f"No historical assessment data found for {inspect_target}.")
        
    if inspect_target == current_user:
        st.divider()
        st.subheader("Edit Personal ID Card")
        col_pic, col_bio = st.columns([1, 2])
        with col_pic:
            uploaded_file = st.file_uploader("Update Photograph (PNG/JPG)", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
            if uploaded_file is not None:
                if st.button("Save Photograph", use_container_width=True):
                    supabase.table("players").update({"avatar": base64.b64encode(uploaded_file.getvalue()).decode()}).eq("username", current_user).execute()
                    st.success("File uploaded successfully."); st.rerun()
        with col_bio:
            new_bio = st.text_area("Update Bio Information...", value=player_data.get("bio", ""), height=120, max_chars=300)
            if st.button("Save Details", use_container_width=True):
                supabase.table("players").update({"bio": new_bio}).eq("username", current_user).execute()
                st.success("Record updated."); st.rerun()