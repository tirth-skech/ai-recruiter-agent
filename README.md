🎯 AI Recruiter Agent: Production-Ready 
This repository contains a professional-grade, AI-driven recruitment platform designed to manage the full hiring lifecycle. The system utilizes Agentic AI to screen candidates, predict hiring success, and facilitate team collaboration with high-level security protocols.
Multi-Role Authentication: Features a strict gateway for Recruiters, Managers, and Admins with tailored access levels.

Predictive Hiring Analytics: Uses a custom scoring algorithm to forecast candidate retention and success based on education tiers and skill sets.

Full Recruitment Lifecycle Database: A complex relational schema managing Jobs, Candidates, and Interview logs.

Agentic Sourcing Engine: Powered by Gemini 2.0 Flash for high-speed, structured JSON extraction from resumes.

Admin "Danger Zone": A secure, password-protected administrative panel for database resets and production management.

Manual Recruiter Overrides: Allows human-in-the-loop corrections for AI-extracted data like salary and relocation willingness.
├── app.py                # Main Streamlit Dashboard with Auth Logic
├── processor.py          # LangGraph Agentic Workflow & Predictive AI
├── database.py           # Relational SQLite Schema & Lifecycle Logging
├── requirements.txt      # Project Dependencies
└── .streamlit/           # Configuration and Secrets
1. Clone & Install
Bash
git clone https://github.com/your-username/ai-recruiter-agent.git
cd ai-recruiter-agent
pip install -r requirements.txt
2. Configure SecretsCreate a .streamlit/secrets.toml file or set environment variables:Ini, TOMLGEMINI_API_KEY = "your_google_ai_studio_key"
3. Run the ApplicationBashstreamlit run app.py
🔑 Access Credentials (Demo Mode)RoleCorporate EmailPasswordRecruiter(Self Sign-UP)recruit123Managermanager@hr.commanager423Adminadmin@hr.comadmin789🏗️ Tech StackLLM Engine: Google Gemini 2.5 Flash.Agent Framework: LangGraph.Frontend: Streamlit (2026 Responsive UI).Database: SQLite (Relational).Parsing: PyMuPDF & Python-Docx.⚖️ Indian Market ContextThis application is specifically tuned for Indian recruitment, featuring:Education Tiers: Classification of Tier-1, Tier-2, and Tier-3 institutions.Salary Logic: Expected CTC processing in Lakhs Per Annum (LPA).Notice Period: Extraction of standard 30-90 day Indian notice periods.Developed by | Logickverse Team | Agentic AI Internship 
