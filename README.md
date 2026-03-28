
An intelligent, multi-role recruitment platform powered by Gemini 2.5 Flash and LangGraph. This agent automates the sourcing, screening, and assessment of candidates with a specific focus on the Indian tech market context.

Core Features (Week 5 Updates)
1. Agentic Intelligence
Gemini 2.5 Flash Integration: Uses high-speed LLM inference with strict JSON schemas to extract structured data from unstructured resumes.

Tier-1 Logic: Automatically identifies and tags candidates from premier Indian institutes (IIT, NIT, BITS, IIIT).

Automated Assessment: Triggers HackerEarth API invitations automatically for high-scoring Tier-1 candidates.

2. Enterprise Security & Roles
Multi-Role Authentication: * External: Auth0 / Google OAuth 2.0 integration for partner recruiters.

Internal: Secure manual login for HR Managers and Admins.

RBAC (Role-Based Access Control): * Managers can run pipelines and view candidates.

Admins gain exclusive access to Market Analytics and the Database Reset utility.

3. Market-Specific Analytics
Salary Insight: Extracts and visualizes Expected Salary (LPA) trends.

Relocation Tracking: Identifies candidates willing to move to hub locations (e.g., Ahmedabad/Bangalore).

Human-in-the-Loop: Supports Manual Overrides for Salary and Relocation via the UI to ensure 100% data integrity.

Technical Stack
LLM Engine: Google Gemini 2.5 Flash (GenAI SDK)

Orchestration: LangGraph (State-Based Workflows)

Frontend: Streamlit (2026 Edition - width="stretch" compatible)

Database: SQLite3

Auth: Auth0 & Custom Session State RBAC

Visuals: Plotly Express

Parsing: PyMuPDF (PDF) & Python-Docx

Project Structure
app.py: Main Streamlit UI & Role-Based Logic

processor.py: LangGraph Workflow & Gemini Extraction

database.py: SQLite Schema & Candidate Persistence

requirements.txt: Project Dependencies

Admin & Manager Credentials
Admin: admin@hr.com | Password: admin789

Manager: manager@hr.com | Password: manager423
