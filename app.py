import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate_v8
from processor import preview_resumes, PredictiveAnalytics

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
    files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

    if files and jd:
        if st.button("Step 1: Extract & Preview"):
            with st.spinner("AI is reading resumes..."):
                results = preview_resumes(user_api_key, jd, files)
                st.session_state.preview_data = results
    
    with col_b:
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        if st.button("▶️ Start Production Pipeline", type="primary"):
            if user_api_key and jd and files:
                run_agent_workflow(user_api_key, jd, files, auth["user"], conn, save_candidate_v8 ,overrides=overrides)
            else:
                st.warning("Ensure API Key, JD, and Files are present.")
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
                
                # Update the object with overrides
                candidate.update({"name": o_name, "email": o_email, "salary_exp": o_salary})
                final_list.append(candidate)

        if st.button("Step 2: Save All to Pipeline", type="primary"):
            for person in final_list:
                # Calculate retention using your existing logic
                from processor import PredictiveAnalytics
                p_score = PredictiveAnalytics.calculate_retention_score(person)
                save_candidate_v8(conn, person, 1, p_score)
            
            st.success("All candidates saved with your manual overrides!")
            del st.session_state.preview_data
            st.rerun()
# 1. Trigger the Preview
if st.button("Step 1: Extract & Preview"):
    st.session_state.preview_list = preview_resumes(user_api_key, jd, files)

# 2. Show Override UI
if "preview_list" in st.session_state:
    st.subheader("📋 Verify Candidate Details")
    final_to_save = []
    
    for i, candidate in enumerate(st.session_state.preview_list):
        with st.expander(f"Review: {candidate['name']} (File: {candidate['filename']})", expanded=True):
            c1, c2, c3 = st.columns(3)
            # RECRUITER CAN FIX THE NAME/EMAIL HERE
            u_name = c1.text_input("Name", value=candidate['name'], key=f"name_{i}")
            u_email = c2.text_input("Email", value=candidate['email'], key=f"email_{i}")
            u_salary = c3.number_input("Salary", value=float(candidate.get('salary_exp', 0)), key=f"sal_{i}")
            
            # Apply individual overrides to the object
            candidate.update({"name": u_name, "email": u_email, "salary_exp": u_salary})
            final_to_save.append(candidate)

    # 3. Final Save Button
    if st.button("Step 2: Save to Pipeline", type="primary"):
        for person in final_to_save:
            from processor import PredictiveAnalytics
            p_score = PredictiveAnalytics.calculate_retention_score(person)
            save_candidate_v8(conn, person, 1, p_score)
        
        st.success("Successfully added all candidates!")
        del st.session_state.preview_list
        st.rerun()
with active_tabs[1]: # Pipeline Tab
    st.header("📋 Candidate Pipeline")
    df_pipe = pd.read_sql("SELECT * FROM candidates", conn)
    
    if not df_pipe.empty:
        st.dataframe(df_pipe, use_container_width=True)
        
        st.divider()
        st.subheader("📧 Direct Contact")
        # This selectbox now shows the OVERRIDDEN emails
        target_email = st.selectbox("Select Candidate", df_pipe['email'].unique())
        
        if target_email:
            # Fetch the name associated with that specific email
            row = df_pipe[df_pipe['email'] == target_email].iloc[0]
            c_name = row['name']
            
            # Professional Recruitment Mail Body
            subject = f"Next Steps for {c_name} - Goldwin Systems"
            body = f"Hi {c_name},\n\nWe reviewed your profile and would like to move forward..."
            
            mail_link = f"mailto:{target_email}?subject={subject}&body={body}"
            st.markdown(f'<a href="{mail_link}" target="_blank" style="background-color:#28a745; color:white; padding:12px; border-radius:8px; text-decoration:none;">✉️ Open Mail to {c_name}</a>', unsafe_allow_html=True)
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
    - **AI Engine**: Gemini 2.0 Flash Agentic Workflow via LangGraph.
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
        
   # --- ADMIN RESET GATE ---
        if st.session_state.get("confirm_reset"):
            with st.container(border=True):
                st.warning("⚠️ Final Confirmation Required")
                confirm_p = st.text_input("Enter Admin Password to confirm wipe", type="password", key="reset_gate")
                
                # We define BOTH columns here so they are guaranteed to exist
                col_a, col_b = st.columns(2)
                
                # Logic for the Delete Button
                if col_a.button("Confirm Permanent Delete", type="primary", use_container_width=True):
                    if confirm_p == "admin789": # Your corporate admin password
                        # Ensure this matches your Week 8 DB name
                        db_file = "recruitment_v8_enterprise.db"
                        if os.path.exists(db_file):
                            os.remove(db_file)
                            st.success("Database wiped successfully. Restarting...")
                            st.session_state.confirm_reset = False
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Database file not found.")
                    else:
                        st.error("Incorrect Password. Action Aborted.")
                
                # Logic for the Cancel Button (col_b is now defined!)
                if col_b.button("Cancel", use_container_width=True):
                    st.session_state.confirm_reset = False
                    st.rerun()
    st.divider()
    st.caption("Logickverse Enterprise v8.0 | Agentic AI Internship")
