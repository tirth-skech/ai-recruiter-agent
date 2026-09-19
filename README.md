# 🎯 Enterprise AI Recruiter & Skill-Gap Agent

An agentic, multi-role recruitment and skill-gap intelligence platform built for modern HR workflows and Indian technical job seekers. Powered by **Gemini 2.5 Flash**, **Streamlit**, and real-time open APIs, the platform automates candidate resume ingestion, queries live remote tech opportunities, calculates skill gaps, and dynamically routes learners to targeted upskilling pathways.

Developed by **Logicverse Dynamic Team** from **Vishwakarma Government Engineering College (VGEC), Chandkheda**.

---

## 🌟 Key Features

* **📄 Automated Resume Ingestion & Parsing:** Parses candidate PDF/DOCX resumes using PyMuPDF and `google-genai` (Gemini 2.5 Flash) into structured JSON profile schemas with verified academic records.
* **🌐 Live Remotive API Integration:** Queries live remote technical job postings in real time without requiring complex web-scraping keys or Google CSE credentials.
* **🎯 Precision Job Match & Direct Apply:** Directs candidates directly to exact, single-listing job pages while extracting required technical skills on the fly using Gemini Flash Lite.
* **🎓 Dynamic Skill-Gap Learning Pathways:** Automatically identifies candidate skill deficiencies and generates direct upskilling search links for **Coursera**, **YouTube**, and **NPTEL / SWAYAM**.
* **🧠 Reasoning Transparency Engine:** Visualizes agentic handoffs and mathematical decision flows (`Skill_Gaps = Required_Skills - Candidate_Skills`) using Graphviz directed graphs.
* **🔒 Gatekept Authentication & Governance:** Feature-gated portal offering candidate sign-in alongside secure internal HR staff login with full system audit logging.

---

## 🛠️ Tech Stack

* **Frontend / Framework:** [Streamlit](https://streamlit.io/)
* **AI Model Engine:** Google Gemini API (`google-genai` SDK — `gemini-2.5-flash`, `gemini-2.5-flash-lite`)
* **Document Processing:** `PyMuPDF` (`fitz`), `python-docx`, `beautifulsoup4`
* **Visualization & Graphs:** `graphviz`, `pandas`
* **API & Data Requests:** `requests`, `urllib.parse`
* **Database & Governance:** SQLite3 (`database.py`)

---

## 📁 Repository Structure

```text
├── app.py              # Main Streamlit application entry point & UI agents
├── database.py         # SQLite initialization and compliance audit log utilities
├── requirements.txt    # Production Python dependencies
└── README.md           # Project documentation

🚀 Getting Started1. Clone the RepositoryBashgit clone [https://github.com/your-username/ai-recruiter-agent.git](https://github.com/your-username/ai-recruiter-agent.git)
cd ai-recruiter-agent
2. Set Up Virtual EnvironmentBashpython3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
3. Install DependenciesBashpip install -r requirements.txt
4. Configure SecretsCreate a .streamlit/secrets.toml file in the root directory and insert your Google Gemini API key:Ini, TOMLGEMINI_API_KEY = "your_google_gemini_api_key_here"
5. Launch the ApplicationBashstreamlit run app.py
🔒 Default System Credentials (Internal HR Staff)For testing and demonstration of staff role access and compliance logging:Staff RoleCorporate EmailDefault PasswordAccess LevelAdminadmin@hr.comadmin789Full Access + Audit Log GovernanceManagermanager@hr.commanager423Full Access + Audit Log Governance📜 Compliance & Audit LoggingEvery key agent action—including authentication attempts, candidate resume parsing, and live API queries—is logged with timestamped payloads in an internal database accessible via the Audit Logs tab (restricted to internal Admin/Manager staff).
