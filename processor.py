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
    agent_email: str

# --- 2. Workflow Nodes ---

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

def screening_node(state: AgentState):
    """Tool: AI Screening & Diversity Check"""
    raw_data = state['results'][-1]
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    JD: {state['jd_text']}
    RESUME: {raw_data['raw_text']}
    TASK: Return ONLY valid JSON:
    {{
        "name": "Candidate Name",
        "score": 85,
        "summary": "2-sentence analysis",
        "diversity_flag": true
    }}
    """
    response = model.generate_content(prompt)
    clean_json = response.text.strip().replace('```json', '').replace('```', '')
    data = json.loads(clean_json)
    return {"results": [data]}

def invitation_node(state: AgentState):
    """Tool: Invitation Drafting"""
    data = state['results'][-1]
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    Draft an interview invite for {data['name']}.
    From: {state['agent_email']} (ai26agent@gmail.com)
    Candidate Score: {data['score']}/100.
    """
    response = model.generate_content(prompt)
    data['invite_text'] = response.text
    return {"results": [data]}

# --- 3. Build Graph ---

def get_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("sourcing", sourcing_node)
    workflow.add_node("screening", screening_node)
    workflow.add_node("invitation", invitation_node)
    
    workflow.set_entry_point("sourcing")
    workflow.add_edge("sourcing", "screening")
    workflow.add_edge("screening", "invitation")
    workflow.add_edge("invitation", END)
    return workflow.compile()

def run_complex_agent(api_key, jd_text, files):
    genai.configure(api_key=api_key)
    app = get_workflow()
    final_results = []
    
    for i in range(len(files)):
        inputs = {
            "jd_text": jd_text, 
            "files": files, 
            "current_file_idx": i, 
            "results": [],
            "agent_email": "ai26agent@gmail.com"
        }
        output = app.invoke(inputs)
        final_results.append(output['results'][-1])
        time.sleep(1)
    return final_results
