import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate_v8
from processor import preview_resumes, PredictiveAnalytics
import urllib.parse

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Goldwin Enterprise AI | Week 8",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION (Logic Maintained) ---
def get_auth_status():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "user": st.user.get("email"), "role": "Recruiter"}
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    if st.session_state.get("manager_login"):
        return {"ok": True, "user": st.session_state.manager_email, "role": "Manager"}
    return {"ok": False}

auth = get_auth_status()

if not auth["ok"]:
    st.title("Recruitment Gateway")
    st.info("Indian Market Context | Week 8 Enterprise")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Recruiter Login")
            if st.button("Sign-UP", type="primary", use_container_width=True):
                try: 
                    st.login("auth0")
                except: 
                    st.error("Auth0 Configuration Missing in Secrets.")
                
    with col2:
        with st.form("staff_login"):
            st.subheader("Internal Staff")
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"admin_login": True, "admin_email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"manager_login": True, "manager_email": u})
                    st.rerun()
                else: 
                    st.error("Invalid Credentials")
    st.stop()

# --- 3. ENTERPRISE SIDEBAR (Week 8 Security) ---
conn = init_db()

with st.sidebar:
    st.title(f"👤 {auth['role']}")
    st.caption(f"Active: {auth['user']}")
    
    user_api_key = st.text_input(
        "Gemini API Key", 
        type="password", 
        value=st.secrets.get("GEMINI_API_KEY", ""),
        help="Paste key to override default."
    )

    st.divider()
    st.subheader("🛡️ Governance & GDPR")
    gdpr_privacy = st.toggle("GDPR Data Masking", value=True)
    st.caption("Performance: SQL Indexing Active")

    if st.button("🚪 Logout", use_container_width=True):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

# --- 4. ENTERPRISE TABS ---
tabs = ["🚀 Sourcing", "📋 Pipeline", "🌈 Diversity & Analytics", "📜 API Docs"]
active_tabs = st.tabs(tabs)

with active_tabs[0]: # Sourcing Tab
    st.header("🚀 Smart Sourcing with Manual Overrides")
    jd = st.text_area("Job Description")
    files = st.file_uploader("Upload Resumes", accept_multiple_files=True, key="sourcing_upload")

    if files and jd:
        # STEP 1: PREVIEW
        if st.button("Step 1: Extract & Preview"):
            with st.spinner("AI is reading resumes..."):
                # calls your processor function
                results = preview_resumes(user_api_key, jd, files)
                st.session_state.preview_data = results

    # --- THE OVERRIDE STEP ---
    if "preview_data" in st.session_state:
        st.subheader("📋 Review & Override (Per Candidate)")
        final_list = []
        
        for i, candidate in enumerate(st.session_state.preview_data):
            with st.expander(f"Review: {candidate['name']} ({candidate['filename']})", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    o_name = st.text_input("Name", value=candidate['name'], key=f"n_{i}")
                with col2:
                    o_email = st.text_input("Email Override", value=candidate['email'], key=f"e_{i}")
                with col3:
                    o_salary = st.number_input("Salary (LPA)", value=float(candidate.get('salary_exp', 0)), key=f"s_{i}")
                
                candidate.update({"name": o_name, "email": o_email, "salary_exp": o_salary})
                final_list.append(candidate)

        # STEP 2: SAVE
        if st.button("Step 2: Save All to Pipeline", type="primary"):
            for person in final_list:
                p_score = PredictiveAnalytics.calculate_retention_score(person)
                save_candidate_v8(conn, person, 1, p_score)
            
            st.success("All candidates saved with manual overrides!")
            del st.session_state.preview_data
            st.rerun()
# --- PIPELINE TAB (Mailing Section) ---
with active_tabs[1]:
    st.header("📋 Candidate Pipeline")
    df_pipe = pd.read_sql("SELECT * FROM candidates", conn)
    
    if not df_pipe.empty:
        st.dataframe(df_pipe, use_container_width=True)
        
        st.divider()
        st.subheader("📧 Recruitment Mail Dashboard")
        
        target_email = st.selectbox("Select Candidate", df_pipe['email'].unique())
        
        if target_email:
            row = df_pipe[df_pipe['email'] == target_email].iloc[0]
            c_name = row['name']
            
            # Formatted Mail Data for easy copying
            mail_content = f"""FROM: Goldwin Recruitment Team <hr@goldwin.com>
TO: {c_name} <{target_email}>
SUBJECT: Interview Invitation - Goldwin Systems Specialist Role

MESSAGE:
Hi {c_name},

We have reviewed your profile and were impressed with your technical skills. We would like to schedule a discussion regarding your application.

Please share your availability for a call.

Best regards,
Goldwin Recruitment Team
"""
            # Displaying in a code block makes it 1-click copyable in Streamlit
            st.code(mail_content, language="markdown")
            
            # Keeping the direct button as a backup
            safe_subject = urllib.parse.quote(f"Interview Invitation - {c_name}")
            safe_body = urllib.parse.quote(f"Hi {c_name}, we would like to move forward...")
            mail_link = f"mailto:{target_email}?subject={safe_subject}&body={safe_body}"
            
            st.markdown(f'<a href="{mail_link}" target="_blank" style="background-color:#28a745; color:white; padding:8px 16px; text-decoration:none; border-radius:5px;">🚀 Open Default Mail App</a>', unsafe_allow_html=True)
with active_tabs[2]:
    st.header("🌈 Diversity & Market Analytics")
    df_fresh = pd.read_sql("SELECT * FROM candidates", conn)
    if not df_fresh.empty:
        c1, c2 = st.columns(2)
        with c1:
            # This will now work because gender is extracted in processor.py
            fig = px.pie(df_fresh, names='gender', title="Gender Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(df_fresh, x='edu_tier', color='ethnicity', title="Talent Source Hubs")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Analytics will populate after processing resumes.")

with active_tabs[3]:
    st.header("Technical Documentation")
    st.markdown("""
    ### Microservices Architecture
    - **Auth Service**: Role-based access (Recruiter, Manager, Admin).
    - **Candidate Service**: SQL Backend with Performance Indexing.
    - **AI Engine**: Gemini 2.5 Flash Agentic Workflow via LangGraph.
    - **Privacy**: GDPR-compliant masking toggles enabled.
    """)

# --- 5. ADMIN DANGER ZONE (Fixed Indentation) ---
if auth["role"] == "Admin":
    st.divider()
    st.subheader("⚠️ Danger Zone")
    st.write("Authorized Personnel Only.")

    # Start of Reset Logic
    if st.button("🔥 Initialize Database Reset", type="secondary"):
        st.session_state.confirm_reset = True
        
# --- ADMIN RESET GATE (Bottom of app.py) ---
if st.session_state.get("confirm_reset"):
    with st.container(border=True):
        st.warning("⚠️ Final Confirmation Required")
        confirm_p = st.text_input("Enter Admin Password", type="password", key="reset_gate")
        
        col_a, col_b = st.columns(2)
        
        if col_a.button("Confirm Permanent Delete", type="primary", use_container_width=True):
            if confirm_p == "admin789":
                db_file = "recruitment_v8_enterprise.db"
                try:
                    # IMPORTANT: Close connection before deleting
                    if 'conn' in globals():
                        conn.close()
                    
                    if os.path.exists(db_file):
                        os.remove(db_file)
                        st.success("Database wiped successfully. Please restart the app.")
                        st.session_state.confirm_reset = False
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}. The file might be in use.")
            else:
                st.error("Incorrect Password.")
        
        if col_b.button("Cancel", use_container_width=True):
            st.session_state.confirm_reset = False
            st.rerun()
    st.divider()
    st.caption("Logickverse Enterprise v8.0 | Agentic AI Internship")
