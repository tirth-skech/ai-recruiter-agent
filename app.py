import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, save_candidate
from processor import run_agent_workflow

# --- 1. PAGE CONFIG & SESSION STATE ---
st.set_page_config(page_title="Goldwin AI Recruiter Pro", layout="wide", page_icon="🛡️")

if "auth_status" not in st.session_state:
    st.session_state.update({
        "auth_status": False,
        "user_role": None,
        "user_email": None
    })

# --- 2. SAFE AUTHENTICATION CHECK ---
def check_authentication():
    # Check if Auth0 just returned a successful login
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        st.session_state.auth_status = True
        st.session_state.user_role = "Recruiter"
        st.session_state.user_email = st.user.get("email")
        return True
    
    # Check if manual session is already active
    if st.session_state.auth_status:
        return True
        
    return False

# --- 3. LOGIN INTERFACE ---
def login_screen():
    st.title("🛡️ Enterprise Recruitment Portal")
    st.markdown("### Welcome to the Week 4 Agentic Pipeline")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.subheader("External Recruiter")
            st.write("Authenticate via Google or Social Login.")
            try:
                if st.button("Login with Auth0", type="primary"):
                    st.login("auth0")
            except Exception as e:
                st.error("Auth0 is not configured in Streamlit Secrets.")
                
    with col2:
        with st.container(border=True):
            st.subheader("Corporate Staff")
            with st.form("staff_login"):
                u = st.text_input("Corporate Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In"):
                    if u == "admin@hr.com" and p == "admin789":
                        st.session_state.update({"auth_status": True, "user_role": "Admin", "user_email": u})
                        st.rerun()
                    elif u == "manager@hr.com" and p == "manager423":
                        st.session_state.update({"auth_status": True, "user_role": "Manager", "user_email": u})
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

# --- 4. MAIN APPLICATION LOGIC ---
if not check_authentication():
    login_screen()
else:
    # Initialize DB and Sidebar
    conn = init_db()
    
    st.sidebar.title(f"Role: {st.session_state.user_role}")
    st.sidebar.write(f"Logged: {st.session_state.user_email}")
    
    if st.sidebar.button("🚪 Logout"):
        if hasattr(st, "user") and st.user.get("is_logged_in"):
            st.logout()
        st.session_state.clear()
        st.rerun()

    # --- TABS FOR TRACK B REQUIREMENTS ---
    tab1, tab2 = st.tabs(["🚀 Agent Pipeline", "📊 Performance Analytics"])

    with tab1:
        st.header("Agentic AI Workflow")
        # Pulling Gemini Key safely from Streamlit Secrets
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            jd = st.text_area("Step 1: Paste Job Description", height=150)
            files = st.file_uploader("Step 2: Upload Candidate Resumes", accept_multiple_files=True, type=['pdf', 'docx'])
            
            if st.button("▶️ Start Agentic Pipeline"):
                if jd and files:
                    run_agent_workflow(api_key, jd, files, st.session_state.user_email, conn, save_candidate)
                else:
                    st.warning("Please provide both a Job Description and Resumes.")
        except KeyError:
            st.error("GEMINI_API_KEY missing from Streamlit Secrets!")

    with tab2:
        st.header("Recruitment Insights")
        query = "SELECT * FROM recruitment_pipeline"
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Processed", len(df))
            c2.metric("Avg Match Score", f"{int(df['score'].mean())}%")
            
            # Track B Analytics Visualization
            fig = px.scatter(df, x="score", y="api_latency", color="status", 
                             hover_data=['candidate_name'], title="Efficiency vs Match Score")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Recent Activity")
            st.dataframe(df[['candidate_name', 'score', 'status', 'timestamp']].sort_values(by='timestamp', ascending=False))
        else:
            st.info("No data available. Process some resumes in the Pipeline tab first.")
