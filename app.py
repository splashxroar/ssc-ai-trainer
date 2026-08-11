import streamlit as st
import os
import json
import time
import base64
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
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    h1, h2, h3 { color: #ffffff !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;} 
    
    [data-testid="stSidebar"] {
        background-color: #1e1f22;
        border-right: 1px solid #444746;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p {
        color: #e3e3e3 !important;
    }
    
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
    .stButton>button:disabled {
        border: 1px solid #444746;
        color: #80868b !important;
        background-color: transparent;
        transform: none;
    }
    
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea {
        background-color: #282a2d !important;
        border: 1px solid #444746 !important;
        border-radius: 8px !important;
        color: #e3e3e3 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #9aa0a6 !important; 
        font-size: 16px;
        font-weight: 500;
        padding-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #e3e3e3 !important; }
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #8ab4f8;
        color: #8ab4f8 !important; 
    }
    
    /* Chat Box Styling */
    .chat-msg {
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        background-color: #1e1f22;
        border: 1px solid #444746;
    }
    .chat-user { font-weight: bold; color: #8ab4f8; }
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
                    supabase.table("players").insert({"username": user_input, "pin": pin_input, "last_seen": time.time()}).execute()
                    st.success("New agent registered!")
                    st.session_state['username'] = user_input
                    st.rerun()
            else:
                st.warning("Missing credentials.")
    st.stop()

# --- MAIN APP ---
current_user = st.session_state['username']

# UPDATE LAST SEEN STATUS (Runs every time they click anything)
supabase.table("players").update({"last_seen": time.time()}).eq("username", current_user).execute()

# FETCH PLAYER AVATAR & BIO
player_data = supabase.table("players").select("*").eq("username", current_user).execute().data[0]
avatar_base64 = player_data.get("avatar")

# RENDER SIDEBAR AVATAR
if avatar_base64:
    st.sidebar.markdown(f'''
        <div style="text-align: center;">
            <img src="data:image/png;base64,{avatar_base64}" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 2px solid #8ab4f8; margin-bottom: 10px; box-shadow: 0 0 15px rgba(138, 180, 248, 0.2);">
        </div>
    ''', unsafe_allow_html=True)
else:
    st.sidebar.markdown(f'''
        <div style="text-align: center;">
            <div style="width: 120px; height: 120px; border-radius: 50%; background-color: #282a2d; border: 2px dashed #444746; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 10px; margin-left: auto; margin-right: auto;">
                <span style="color: #80868b; font-size: 40px;">👤</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)

st.sidebar.markdown(f"<h3 style='text-align: center;'>🕹️ Agent: <span style='color:#8ab4f8;'>{current_user}</span></h3>", unsafe_allow_html=True)

col_disconnect, = st.sidebar.columns(1)
if col_disconnect.button("Disconnect", use_container_width=True):
    del st.session_state['username']
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Match Settings")

selected_subject = st.sidebar.selectbox("Queue Select", ["GK (Polity, History, etc.)", "Math (Quant)", "English Comprehension", "General Intelligence (Reasoning)"])

specific_chapter = None
if selected_subject == "Math (Quant)":
    specific_chapter = st.sidebar.selectbox("Target Chapter (Math Only)", [
        "Mixed (All Chapters)", "Number System", "Percentage", "Ratio & Proportion",
        "Time & Work", "Time, Speed & Distance", "Algebra", "Geometry", "Trigonometry",
        "Mensuration", "Data Interpretation"
    ])

num_questions = st.sidebar.selectbox("Match Length (Targets)", [25, 15, 10])
difficulty = st.sidebar.selectbox("Difficulty Tier", ["Easy", "Moderate", "Hard"])
test_time_limit = st.sidebar.slider("Match Timer (Minutes)", 10, 60, 30)

st.title(f"⚡ RADIANT: SSC Combat Arena")

# --- AUTO-SAVE RECOVERY ---
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎮 Combat Arena", "🏅 Leaderboards", "📼 VOD Reviews", "👤 Agent Profile", "💬 Comm Center"])

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
            start_standard = st.button(f"🎯 Queue Standard Match ({num_questions} Targets)", use_container_width=True)
        with col2:
            start_weakest = st.button(f"🔥 Queue Weakness Drill ({num_questions} Targets)", disabled=not weakest_topic, use_container_width=True)

        def generate_ai_test(focus_topic):
            actual_topic = focus_topic
            if focus_topic == "Math (Quant)" and specific_chapter and specific_chapter != "Mixed (All Chapters)":
                actual_topic = f"Math (Quant) - strictly focusing on {specific_chapter}"
                
            with st.spinner(f"Generating a {num_questions}-target {difficulty} match for {actual_topic}..."):
                prompt = f"Generate a {num_questions}-question multiple-choice test for SSC CGL level. Subject: {actual_topic}. Difficulty Level: {difficulty}. CRITICAL: Questions must be highly unique and completely randomized. Avoid standard generic templates. Seed: {time.time()}. Return ONLY valid JSON format as a list of dictionaries with exactly these keys: 'question', 'options' (list of 4 strings), 'answer' (the exact correct option string), and 'explanation' (a detailed 2-sentence explanation)."
                try:
                    ai_response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                    raw_text = ai_response.text.replace("```json", "").replace("```", "").strip()
                    test_data = json.loads(raw_text)
                    
                    supabase.table("active_sessions").upsert({
                        "username": current_user,
                        "test_data": test_data,
                        "start_time": time.time(),
                        "focus_topic": actual_topic,
                        "difficulty": difficulty
                    }).execute()

                    st.session_state['current_test'] = test_data
                    st.session_state['start_time'] = time.time()
                    st.session_state['current_focus'] = actual_topic
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
                        "explanation": q.get('explanation', 'Data corrupted.')
                    })
                
                total_q = len(test_questions)
                supabase.table("test_history").insert({
                    "username": current_user,
                    "subject": st.session_state['current_focus'],
                    "score": score,
                    "total": total_q,
                    "time_spent": time_spent,
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
    history_response = supabase.table("test_history").select("*").limit(5000).execute()
    if history_response.data:
        df = pd.DataFrame(history_response.data)
        if 'time_spent' not in df.columns:
            df['time_spent'] = 0.0
        df['time_spent'] = df['time_spent'].fillna(0)
        
        st.write("### 🎖️ Top Grinders (All Matches)")
        grind_stats = df.groupby('username').agg(
            Total_Matches=('score', 'count'), 
            Total_Time_Mins=('time_spent', 'sum')
        ).reset_index()
        grind_stats['Total_Time_Mins'] = grind_stats['Total_Time_Mins'].round(2)
        grind_stats = grind_stats.sort_values(by=['Total_Matches', 'Total_Time_Mins'], ascending=[False, False])
        st.dataframe(grind_stats, use_container_width=True, hide_index=True)
        st.divider()

        st.write("### 🏆 Official Leaderboards (25-Target Ranked Matches ONLY)")
        df_25 = df[df['total'] == 25].copy()
        if not df_25.empty:
            df_25['Accuracy'] = (df_25['score'] / df_25['total'] * 100).round(1).astype(str) + '%'
            df_25['Time (Mins)'] = df_25['time_spent'].round(2)
            lb_tabs = st.tabs(["🧮 Math", "🌍 GK", "🧠 Reasoning", "📖 English", "🔥 Overall"])
            
            def render_lb(filtered_df):
                if not filtered_df.empty:
                    leaderboard = filtered_df.sort_values(by=['score', 'Time (Mins)'], ascending=[False, True]).head(20)
                    st.dataframe(leaderboard[['username', 'subject', 'score', 'total', 'Accuracy', 'Time (Mins)']], use_container_width=True, hide_index=True)
                else:
                    st.info("No records for this category yet.")

            with lb_tabs[0]: render_lb(df_25[df_25['subject'].str.contains("Math", na=False)])
            with lb_tabs[1]: render_lb(df_25[df_25['subject'].str.contains("GK", na=False)])
            with lb_tabs[2]: render_lb(df_25[df_25['subject'].str.contains("Reasoning", na=False)])
            with lb_tabs[3]: render_lb(df_25[df_25['subject'].str.contains("English", na=False)])
            with lb_tabs[4]: render_lb(df_25)
        else:
            st.warning("No full 25-Target matches have been completed yet.")
    else:
        st.info("Leaderboard is empty. Secure the first win.")

with tab3:
    st.subheader(f"📼 {current_user}'s Personal VODs")
    past_tests = supabase.table("test_history").select("*").eq("username", current_user).order("created_at", desc=True).execute()
    if past_tests.data:
        for test in past_tests.data:
            date_str = str(test['created_at'])[:10]
            score_ratio = f"{test['score']}/{test['total']}"
            time_logged = test.get('time_spent', 0)
            time_display = f" | {round(time_logged, 2)} mins" if time_logged else ""
            
            with st.expander(f"📅 {date_str} | {test['subject']} | Score: {score_ratio}{time_display}"):
                if test.get('review_data'):
                    for i, q_data in enumerate(test['review_data']):
                        st.markdown(f"**Target {i+1}: {q_data['question']}** ({q_data['status']})")
                        st.write(f"**Your Answer:** {q_data['your_answer']} | **Correct:** {q_data['correct_answer']}")
                        st.success(f"💡 {q_data.get('explanation', 'Data corrupted.')}")
                        st.divider()
    else:
        st.info("No match history found.")

with tab4:
    st.subheader("👤 Agent ID Card")
    st.write("Customize your loadout screen so the squad knows who they are dealing with.")
    
    col_pic, col_bio = st.columns([1, 2])
    
    with col_pic:
        st.write("**Profile Picture**")
        uploaded_file = st.file_uploader("Select an Image (PNG/JPG)", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        if uploaded_file is not None:
            bytes_data = uploaded_file.getvalue()
            b64_str = base64.b64encode(bytes_data).decode()
            if st.button("💾 Save Picture", use_container_width=True):
                supabase.table("players").update({"avatar": b64_str}).eq("username", current_user).execute()
                st.success("Avatar Saved!")
                st.rerun()

    with col_bio:
        st.write("**Agent Bio**")
        current_bio = player_data.get("bio", "")
        new_bio = st.text_area("Write something about yourself...", value=current_bio if current_bio else "", height=120, max_chars=300)
        if st.button("💾 Save Bio", use_container_width=True):
            supabase.table("players").update({"bio": new_bio}).eq("username", current_user).execute()
            st.success("Bio Updated!")
            st.rerun()

with tab5:
    st.subheader("💬 Comm Center & Global Chat")
    st.write("Connect with the squad. Note: You must interact with the page to load new messages.")
    
    col_chat, col_roster = st.columns([3, 1], gap="large")
    
    with col_roster:
        st.markdown("### 🟢 Online Agents")
        st.write("Active in the last 5 minutes:")
        # Fetch users active in the last 300 seconds
        active_threshold = time.time() - 300 
        online_users = supabase.table("players").select("username").gte("last_seen", active_threshold).execute()
        
        if online_users.data:
            for u in online_users.data:
                st.markdown(f"- 🟢 **{u['username']}**")
        else:
            st.write("No one is online right now.")
            
        st.divider()
        st.markdown("### 🔍 Inspect Agent")
        all_players = supabase.table("players").select("username").execute()
        player_list = [p['username'] for p in all_players.data]
        inspect_target = st.selectbox("Select Agent to view Profile", player_list)
        
        if st.button("View ID Card", use_container_width=True):
            target_data = supabase.table("players").select("*").eq("username", inspect_target).execute().data[0]
            
            # Use an expander to show the ID Card right below
            with st.expander(f"🪪 {inspect_target}'s ID Card", expanded=True):
                target_avatar = target_data.get("avatar")
                if target_avatar:
                    st.markdown(f'<img src="data:image/png;base64,{target_avatar}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 2px solid #8ab4f8;">', unsafe_allow_html=True)
                else:
                    st.write("👤 No profile picture set.")
                
                st.write(f"**Bio:** {target_data.get('bio', 'This agent has not written a bio yet.')}")
                
                # Fetch quick stats
                target_stats = supabase.table("test_history").select("score").eq("username", inspect_target).execute()
                st.write(f"**Matches Played:** {len(target_stats.data)}")

    with col_chat:
        # Chat Input
        new_msg = st.text_input("Send a message to Global Chat...", key="chat_input")
        if st.button("Send Message", type="primary"):
            if new_msg.strip():
                supabase.table("global_chat").insert({
                    "username": current_user,
                    "message": new_msg.strip(),
                    "timestamp": time.time()
                }).execute()
                st.rerun()
                
        st.write("---")
        
        # Load last 30 messages
        chat_logs = supabase.table("global_chat").select("*").order("timestamp", desc=True).limit(30).execute()
        
        if chat_logs.data:
            # Reverse to show oldest at top, newest at bottom of the feed
            for log in reversed(chat_logs.data):
                st.markdown(f"""
                <div class="chat-msg">
                    <span class="chat-user">{log['username']}:</span> {log['message']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("The Comm Center is quiet. Be the first to drop a message.")