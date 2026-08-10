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

st.set_page_config(page_title="SSC/CPO AI Trainer", layout="wide")

# --- SECURE LOGIN SCREEN ---
if 'username' not in st.session_state:
    st.title("🛑 Secure Login")
    st.write("Enter your Tag and a 4-Digit PIN. First time logins will automatically register your account.")
    
    col1, col2 = st.columns(2)
    with col1:
        user_input = st.text_input("Username").strip()
    with col2:
        pin_input = st.text_input("4-Digit PIN", type="password").strip()
        
    if st.button("Enter Arena"):
        if user_input and pin_input:
            # Check database for user
            response = supabase.table("players").select("*").eq("username", user_input).execute()
            if response.data:
                # User exists, check PIN
                if response.data[0]['pin'] == pin_input:
                    st.session_state['username'] = user_input
                    st.rerun()
                else:
                    st.error("❌ Wrong PIN! Stop trying to hack your friend's account.")
            else:
                # New user, create account
                supabase.table("players").insert({"username": user_input, "pin": pin_input}).execute()
                st.success("New account registered!")
                st.session_state['username'] = user_input
                st.rerun()
        else:
            st.warning("Fill in both fields.")
    st.stop()

# --- MAIN APP ---
current_user = st.session_state['username']
st.sidebar.header(f"👤 Player: {current_user}")
if st.sidebar.button("Logout"):
    del st.session_state['username']
    st.rerun()

st.sidebar.header("⚙️ Exam Settings")
selected_subject = st.sidebar.selectbox("Select Subject", ["GK (Polity, History, etc.)", "Math (Quant)", "English Comprehension", "General Intelligence (Reasoning)"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Moderate", "Hard"])
test_time_limit = st.sidebar.slider("Time Limit (Minutes)", 10, 60, 30)

st.title(f"🚀 SSC/CPO Training Camp")

# --- AUTO-SAVE RECOVERY SYSTEM ---
# If a test is not in current memory, check the database to see if they were in the middle of one
if 'current_test' not in st.session_state and 'review_data' not in st.session_state:
    recovery = supabase.table("active_sessions").select("*").eq("username", current_user).execute()
    if recovery.data:
        saved_session = recovery.data[0]
        st.session_state['current_test'] = saved_session['test_data']
        st.session_state['start_time'] = saved_session['start_time']
        st.session_state['current_focus'] = saved_session['focus_topic']
        st.session_state['current_difficulty'] = saved_session['difficulty']
        st.warning("🔄 Recovered your active test! (Note: Radio buttons reset on refresh, but the questions are saved).")

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
            start_standard = st.button(f"📚 Start {selected_subject} Test")
        with col2:
            start_weakest = st.button("🔥 Generate Weakest Topic Test", disabled=not weakest_topic)

        def generate_ai_test(focus_topic):
            with st.spinner(f"Cooking a 25-question {difficulty} test for {focus_topic}..."):
                prompt = f"Generate a 25-question multiple-choice test for SSC CGL level. Subject: {focus_topic}. Difficulty Level: {difficulty}. Return ONLY valid JSON format as a list of dictionaries with exactly these keys: 'question', 'options' (list of 4 strings), 'answer' (the exact correct option string), and 'explanation' (a detailed 2-sentence explanation)."
                try:
                    ai_response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
                    raw_text = ai_response.text.replace("```json", "").replace("```", "").strip()
                    test_data = json.loads(raw_text)
                    
                    # SAVE TO DATABASE SO IT SURVIVES REFRESH
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
                    st.rerun() 
                except Exception as e:
                    st.error(f"Failed to generate test.")

        if start_standard:
            generate_ai_test(selected_subject)
        elif start_weakest and weakest_topic:
            generate_ai_test(weakest_topic)

    if 'current_test' in st.session_state:
        st.write("---")
        # Grab difficulty safely in case of older saved sessions
        diff_label = st.session_state.get('current_difficulty', 'Unknown')
        st.subheader(f"📝 Active Test: {st.session_state['current_focus']} ({diff_label})")
        
        timer_html = f"""
        <div style="background-color: #2b2b2b; color: #ff4b4b; padding: 10px; border-radius: 8px; text-align: center; font-family: sans-serif; font-size: 24px; font-weight: bold; border: 2px solid #ff4b4b;">
            <span id="clock">⏳ Loading Timer...</span>
        </div>
        <script>
            var countDownDate = new Date().getTime() + ({test_time_limit} * 60 * 1000);
            var x = setInterval(function() {{
                var now = new Date().getTime();
                var distance = countDownDate - now;
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                document.getElementById("clock").innerHTML = "⏳ Time Remaining: " + minutes + "m " + seconds + "s";
                if (distance < 0) {{
                    clearInterval(x);
                    document.getElementById("clock").innerHTML = "🚨 TIME IS UP! SUBMIT NOW!";
                }}
            }}, 1000);
        </script>
        """
        components.html(timer_html, height=70)
        
        user_answers = {}
        for i, q in enumerate(st.session_state['current_test']):
            st.markdown(f"**Q{i+1}: {q['question']}**")
            user_answers[i] = st.radio("Select an option:", q['options'], key=f"q_{i}", index=None)
            st.write("")
            
        if st.button("Submit Test & Get Explanations"):
            score = 0
            time_spent = round((time.time() - st.session_state['start_time']) / 60, 2)
            review_data = []

            for i, q in enumerate(st.session_state['current_test']):
                ans = user_answers[i]
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
                    "explanation": q.get('explanation', 'AI forgot to write an explanation.')
                })
            
            total_q = len(st.session_state['current_test'])
            
            supabase.table("test_history").insert({
                "username": current_user,
                "subject": st.session_state['current_focus'],
                "score": score,
                "total": total_q,
                "review_data": review_data
            }).execute()
            
            # WIPE ACTIVE SESSION FROM DB ON SUBMIT
            supabase.table("active_sessions").delete().eq("username", current_user).execute()
            
            st.session_state['review_data'] = review_data
            st.session_state['last_score'] = score
            st.session_state['last_total'] = total_q
            st.session_state['time_spent'] = time_spent
            del st.session_state['current_test']
            st.rerun()

    if 'review_data' in st.session_state:
        st.write("---")
        st.header("📋 Post-Match Review")
        st.subheader(f"Score: {st.session_state['last_score']} / {st.session_state['last_total']} (Time Spent: {st.session_state['time_spent']} mins)")
        
        for i, data in enumerate(st.session_state['review_data']):
            with st.expander(f"Q{i+1}: {data['status']}"):
                st.write(f"**Question:** {data['question']}")
                st.write(f"**Your Answer:** {data['your_answer']}")
                st.write(f"**Correct Answer:** {data['correct_answer']}")
                st.info(f"💡 **Explanation:** {data['explanation']}")

        if st.button("Close Review & Go Back to Arena"):
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