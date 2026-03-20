import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, save_candidate
from processor import run_agent_workflow

# --- 1. MANDATORY PAGE SETUP ---
st.set_page_config(
    page_title="Goldwin AI Recruiter Pro", 
    layout="wide", 
    page_icon="🛡️"
)

# --- 2. SESSION STATE INITIALIZATION ---
if "manual_auth" not in st.session_state:
    st.session_state.update({
        "manual_auth": False,
        "user_role": None,
        "user_email": None
    })

# --- 3. AUTHENTICATION LOGIC ---
def get_auth_status():
    """Checks both Auth0 and Manual Staff login states."""
    # Check for Auth0 (Social Login)
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {
            "is_auth": True, 
            "email": st.user.get("email"), 
            "role": "Recruiter"
        }
    
    # Check for Manual Staff Login
    if st.session_state.manual_auth:
        return {
            "is_auth": True, 
            "email": st.session_state.user_email, 
            "role": st.session_state.user_role
        }
        
    return {"is_auth": False}

# --- 4. LOGIN INTERFACE ---
def show_login_screen():
    st.title("🛡️ Enterprise Recruitment Gateway")
    st.info("Week 4: Agentic AI Pipeline (Track B)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.subheader("External Recruiter")
            st.write("Secure authentication via Google/Auth0")
            # Check if Auth0 secrets exist before showing button
            if "auth" in st.secrets:
                if st.button("Login with Auth0", type="primary"):
                    st.login("auth0")
            else:
                st.warning("Auth0 Secrets missing in Cloud Dashboard.")
                
    with col2:
        with st.container(border=True):
            st.subheader("Corporate Staff")
            with st.form("staff_login"):
                u = st.text_input("Corporate Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In"):
                    # Credentials for your internship demo
                    if u == "admin@hr.com" and p == "admin789":
                        st.session_state.update({"manual_auth": True, "user_role": "Admin", "user_email": u})
                        st.rerun()
                    elif u == "manager@hr.com" and p == "manager423":
                        st.session_state.update({"manual_auth": True, "user_role": "Manager", "user_email": u})
                        st.rerun()
                    else:
                        st.error("Invalid corporate credentials.")

# --- 5. MAIN APPLICATION ---
def main():
    auth = get_auth_status()
    
    if not auth["is_auth"]:
        show_login_screen()
    else:
        # Initialize Database connection
        conn = init_db()
        
        # Sidebar Profile & Logout
        st.sidebar.title(f"👤 {auth['role']}")
        st.sidebar.write(f"📧 {auth['email']}")
        
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            if hasattr(st, "user") and st.user.get("is_logged_in"):
                st.logout()
            st.session_state.clear()
            st.rerun()

        # Tabs based on Role-Based Access Control (RBAC)
        tabs = ["🚀 Agent Pipeline", "📊 Analytics Dashboard"]
        if auth["role"] == "Admin":
            tabs.append("⚙️ System Admin")
            
        active_tabs = st.tabs(tabs)

        # TAB 1: Agentic Workflow
        with active_tabs[0]:
            st.header("Agentic AI Recruitment")
            
            # Use Gemini Key from Secrets
            if "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
                jd = st.text_area("Step 1: Job Description", height=150, placeholder="Paste JD requirements here...")
                files = st.file_uploader("Step 2: Upload Resumes", accept_multiple_files=True, type=['pdf', 'docx'])
                
                if st.button("▶️ Run LangGraph Pipeline", type="primary"):
                    if jd and files:
                        run_agent_workflow(api_key, jd, files, auth["email"], conn, save_candidate)
                    else:
                        st.warning("Please upload resumes and a JD to begin.")
            else:
                st.error("Missing GEMINI_API_KEY in Streamlit Secrets.")

        # TAB 2: Analytics
        with active_tabs[1]:
            st.header("Candidate Insights")
            df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
            
            if not df.empty:
                # Top Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Candidates", len(df))
                m2.metric("Avg Match Score", f"{int(df['score'].mean())}%")
                m3.metric("D&I Index", f"{int(df['diversity_index'].mean())}/10")

                # Visualization
                fig = px.scatter(
                    df, x="score", y="diversity_index", 
                    color="status", size="score",
                    hover_data=['candidate_name'],
                    title="Track B: Candidate Comparison Matrix"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Pipeline Log")
                st.dataframe(df.sort_values(by='timestamp', ascending=False), use_container_width=True)
            else:
                st.info("No data found. Start by processing resumes in the Agent tab.")

        # TAB 3: Admin only
        if auth["role"] == "Admin":
            with active_tabs[2]:
                st.header("System Settings")
                if st.button("🗑️ Reset Recruitment Database"):
                    conn.execute("DELETE FROM recruitment_pipeline")
                    conn.commit()
                    st.success("Database cleared successfully.")

if __name__ == "__main__":
    main()
