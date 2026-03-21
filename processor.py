import fitz
import docx
import json
import io
import time
import google.generativeai as genai
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

# --- 1. Define Agent State ---
class AgentState(TypedDict):
    jd_text: str
    files: list
    results: List[dict]
    current_file_idx: int
    recruiter_email: str

# --- 2. Node Functions (Tools) ---

def sourcing_node(state: AgentState):
    """Tool: Document Parsing"""
    idx = state['current_file_idx']
    f = state['files'][idx]
    file_bytes = f.getvalue()
    ext = f.name.split('.')[-1].lower()
    
    text = ""
    if ext == 'pdf':
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = chr(12).join([page.get_text() for page in doc])
    elif ext == 'docx':
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
    
    return {"results": [{"raw_text": text, "filename": f.name}]}

def screening_assessment_node(state: AgentState):
    """Tool: AI Matcher & ML Matching Logic"""
    raw_data = state['results'][-1]
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    JOB DESCRIPTION: {state['jd_text']}
    RESUME TEXT: {raw_data['raw_text']}
    
    TASK: Perform sophisticated candidate matching. 
    1. Score 0-100 based on technical fit.
    2. Provide a 2-line summary.
    3. Diversity Check: Evaluate solely on skills. Set diversity_flag to true if the candidate 
       brings a unique background or the evaluation is strictly merit-based.
    
    Return ONLY valid JSON:
    {{
        "name": "Candidate Name",
        "score": 85,
        "summary": "Summary of fit",
        "diversity_flag": true
    }}
    """
    response = model.generate_content(prompt)
    res_text = response.text.strip().replace('```json', '').replace('```', '')
    data = json.loads(res_text)
    data['filename'] = raw_data['filename']
    return {"results": [data]}

def invitation_tool_node(state: AgentState):
    """Tool: Automated Interview Scheduling Draft"""
    data = state['results'][-1]
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    Draft a professional interview invitation for {data['name']}.
    From: ai26agent@gmail.com (on behalf of {state['recruiter_email']})
    Candidate Score: {data['score']}/100.
    
    Include a placeholder for scheduling via Google Calendar.
    Return the full email text.
    """
    response = model.generate_content(prompt)
    data['invite_text'] = response.text
    return {"results": [data]}

# --- 3. Graph Construction ---

def get_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("sourcing", sourcing_node)
    workflow.add_node("screening", screening_assessment_node)
    workflow.add_node("invitation", invitation_tool_node)
    
    workflow.set_entry_point("sourcing")
    workflow.add_edge("sourcing", "screening")
    workflow.add_edge("screening", "invitation")
    workflow.add_edge("invitation", END)
    
    return workflow.compile()

def run_complex_agent(api_key, jd_text, files, recruiter_email):
    genai.configure(api_key=api_key)
    app = get_workflow()
    final_results = []
    
    for i in range(len(files)):
        inputs = {
            "jd_text": jd_text, 
            "files": files, 
            "current_file_idx": i, 
            "results": [],
            "recruiter_email": recruiter_email
        }
        output = app.invoke(inputs)
        final_results.append(output['results'][-1])
        time.sleep(1) # Safety for rate limits
        
    return final_results
