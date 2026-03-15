# ai-recruiter-agent
# 🛡️ AI Recruitment Portal 

A professional-grade, role-based Recruitment Management System (RMS) powered by **Google Gemini 2.5 Flash**. This system automates candidate screening using advanced PDF parsing and AI-driven criteria matching.

---

## 🔑 Access Control & Credentials

To test the hierarchical access levels, use the following login details:

### 1. Recruiter Access
* **Method:** Select "Recruiter (Google Auth)"
* **Email:** Use any valid email (e.g., `test@gmail.com`)
* **Access:** Can upload resumes and run AI screening.

### 2. Hiring Manager Access
* **Method:** Select "Staff Login"
* **Email:** `manager@hr.com`
* **Password:** `manager423`
* **Access:** Can run screenings + view the **Manager Dashboard** tab.

### 3. Admin Access
* **Method:** Select "Staff Login"
* **Email:** `admin@hr.com`
* **Password:** `admin789`
* **Access:** Full access to **Recruiter**, **Manager**, and **Admin Control** (Database Reset).

---

## 🚀 Key Features

* **Hierarchical Tabs:** UI elements appear/disappear based on the logged-in user's role.
* **AI Model Discovery:** Automatically detects and connects to **Gemini 2.5 Flash** (v1 or v1beta).
* **Resilient PDF Parsing:** Uses `PyMuPDF` (fitz) to repair and read PDFs that have corrupted `/Root` objects.
* **Rate-Limit Protection:** Built-in 5-second delays to prevent "429 Too Many Requests" errors on Free Tier keys.

---

## 🛠️ Setup Instructions

1.  **Install Dependencies:**
    ```bash
    pip install streamlit google-generativeai pandas pymupdf
    ```

2.  **Run the Main Application:**
    ```bash
    streamlit run app.py
    ```

---

## 📂 Project Structure

* `app.py`: **Main Entry Point.** Handles navigation and UI tabs.
* `processor.py`: Handles Gemini AI logic and PDF text extraction.
* `database.py`: Manages SQLite3 database storage and retrieval.
* `requirements.txt`: List of required Python packages.

---

## 🛡️ Error Handling (Track B Compliance)
* **404 Errors:** Handled via dynamic model listing.
* **429 Errors:** Handled via task delays and exponential backoff.
* **File Errors:** Handled via stream-based PDF repair.
