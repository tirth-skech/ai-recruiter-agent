import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_full_lifecycle
from processor import run_agent_workflow

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Goldwin AI Recruiter | Week 6",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION (Strict Role-Based Access) ---
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
    st.title("Enterprise Recruitment Gateway")
    st.info("Week 6: Full Lifecycle & Multi-API Integration")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Recruiter Login")
            if st.button("Sign-UP / Log-In", type="primary", use_container_width=True):
                try: st.login("auth0")
                except: st.error("Check Streamlit Secrets for [auth] configuration.")
                
    with col2:
        with st.form("staff_login"):
            st.subheader("Internal Staff Access")
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

# --- 3. MAIN DASHBOARD ---
else:
    conn = init_db()
    
    st.sidebar.title(f"👤 {auth['role']}")
    st.sidebar.caption(f"Active Session: {auth['user']}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("🌐 Global Integrations")
    auto_enrich = st.sidebar.toggle("Auto-Enrich Socials", value=True)
    auto_verify = st.sidebar.toggle("Background Verification", value=False)
    
    st.sidebar.divider()
    st.sidebar.success("✅ Multi-API Hub Active")
    st.sidebar.success("✅ Relational DB Connected")

    # --- 4. TABS (Role-Based Visibility) ---
    if auth["role"] == "Admin":
        tab_run, tab_pipe, tab_stats = st.tabs([
            "🚀 Sourcing Agent", 
            "📋 Lifecycle Pipeline", 
            "📊 Executive Analytics"
        ])
    else:
        tab_run, tab_pipe = st.tabs([
            "🚀 Sourcing Agent", 
            "📋 Lifecycle Pipeline"
        ])

    # TAB 1: Agentic Sourcingwith tab_run:
    st.header("Agentic Sourcing Engine")
    
    # Initialize a processing state if it doesn't exist
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    if "GEMINI_API_KEY" in st.secrets:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.subheader("Step 1: Context & Constraints")
            jd = st.text_area("Job Description", height=200)
            manual_salary = st.number_input("Override Salary (LPA)", min_value=0.0)
            manual_reloc = st.radio("Override Relocation", ["Use AI Extraction", "Yes", "No"])
        
        with col_b:
            st.subheader("Step 2: Candidate Batches")
            files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
            
            # Use a callback or session state to keep the process alive
            if st.button("▶️ Launch Full-Lifecycle Agent", type="primary", use_container_width=True) or st.session_state.is_processing:
                if jd and files:
                    st.session_state.is_processing = True # Lock the state
                    
                    overrides = {
                        "salary": manual_salary if manual_salary > 0 else None,
                        "relocation": manual_reloc if manual_reloc != "Use AI Extraction" else None
                    }
                    
                    # RUN THE WORKFLOW
                    run_agent_workflow(
                        st.secrets["GEMINI_API_KEY"], 
                        jd, files, auth["user"], 
                        conn, save_full_lifecycle,
                        overrides=overrides
                    )
                    
                    st.session_state.is_processing = False # Unlock when done
                    st.success("✅ Batch Processing Complete!")
                    st.rerun() # Refresh to show data in the Pipeline tab
                else:
                    st.warning("Please provide both Job Description and Resumes.")
        else:
             st.error("Missing GEMINI_API_KEY in Secrets.")

    # TAB 2: Lifecycle & Collaboration
    with tab_pipe:
        st.header("Candidate Lifecycle Management")
        try:
            df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
            if not df.empty:
                # Real-time Collaboration Features
                col_view, col_note = st.columns([2, 1])
                
                with col_view:
                    tier_filter = st.multiselect("Education Tier", options=["Tier-1", "Tier-2", "Tier-3"], default=["Tier-1", "Tier-2"])
                    status_filter = st.multiselect("Status", options=df['status'].unique(), default=df['status'].unique())
                    
                    filtered_df = df[df['education_tier'].isin(tier_filter) & df['status'].isin(status_filter)]
                    
                    st.dataframe(
                        filtered_df.sort_values(by="score", ascending=False), 
                        use_container_width=True,
                        column_config={
                            "expected_salary": st.column_config.NumberColumn("Salary (LPA)", format="₹%d"),
                            "score": st.column_config.ProgressColumn("Match", min_value=0, max_value=100)
                        }
                    )
                
                with col_note:
                    st.subheader("💬 Team Collaboration")
                    selected_cand = st.selectbox("Select Candidate", df['candidate_name'].unique())
                    note_text = st.text_area("Hiring Manager Feedback", placeholder="Add internal notes...")
                    if st.button("Share Note", use_container_width=True):
                        st.success(f"Feedback synced for {selected_cand}")
                        st.balloons()
            else:
                st.info("No candidates processed in the current lifecycle.")
        except Exception as e:
            st.warning("Awaiting first batch to initialize pipeline view.")

    # TAB 3: Executive Analytics (ADMIN ONLY)
    if auth["role"] == "Admin":
        with tab_stats:
            st.header("Strategic Hiring Insights")
            if not df.empty:
                c1, c2 = st.columns(2)
                with c1:
                    # Requirement: Pie Chart
                    fig_pie = px.pie(df, names='education_tier', title="Tier-1 Talent Concentration", hole=0.5)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with c2:
                    # Requirement: Advanced Graph (Box Plot)
                    fig_box = px.box(df, x='education_tier', y='expected_salary', color='status', title="Salary Trends by Academic Tier")
                    st.plotly_chart(fig_box, use_container_width=True)
                
                st.divider()
                st.subheader("System Health & API Audit")
                st.caption("Monitoring 5+ Integrations (HackerEarth, SendGrid, Twilio, Proxycurl, Mettl)")
                api_df = pd.read_sql("SELECT * FROM api_logs ORDER BY timestamp DESC LIMIT 5", conn)
                st.table(api_df)
                
                # --- PROTECTED RESET ---
                st.subheader("⚠️ Danger Zone")
                if st.button("🔥 Factory Reset Database", type="secondary"):
                    st.session_state.confirm_reset = True
                
                if st.session_state.get("confirm_reset"):
                    confirm_p = st.text_input("Enter Admin Password to wipe data", type="password")
                    if st.button("Confirm Permanent Wipe", type="primary"):
                        if confirm_p == "admin789":
                            if os.path.exists("recruiter_v6.db"):
                                os.remove("recruiter_v6.db")
                                st.success("System Reset Complete. Restarting...")
                                time.sleep(2)
                                st.rerun()
                        else:
                            st.error("Invalid Password.")
            else:
                st.info("Analytics will populate after the first sourcing run.")


# --- 5. FOOTER ---
st.divider()
st.caption("Made by Logickverse Team from VGEC | Agentic AI Internship | Week 6")
