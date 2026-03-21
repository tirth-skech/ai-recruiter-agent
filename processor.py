import fitz
import docx
import json
import io
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
import google.generativeai as genai

# --- 1. Define Agent State ---
class AgentState(TypedDict):
    jd_text: str
    files: list
    results: List[dict]
    current_file_idx: int

# --- 2. Tool-based Nodes ---
def sourcing_node(state: AgentState):
    """Tool 1: Sourcing/Parsing Logic"""
    idx = state['current_file_idx']
    f = state['files'][idx]
    
    # Extract text (using your existing logic)
    ext = f.name.split('.')[-1].lower()
    text = ""
    if ext == 'pdf':
        doc = fitz.open(stream=f.read(), filetype="pdf")
        text = chr(12).join([page.get_text() for page in doc])
    elif ext == 'docx':
        doc = docx.Document(io.BytesIO(f.read()))
        text = "\n".join([para.text for para in doc.paragraphs])
    
    return {"results": [{"raw_text": text, "filename": f.name}]}

def screening_assessment_node(state: AgentState):
    """Tool 2 & 3: AI Screening & Bias-Aware Assessment"""
    raw_data = state['results'][-1]
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""
    JD: {state['jd_text']}
    RESUME: {raw_data['raw_text']}
    
    TASK: 
    1. Score 0-100.
    2. Diversity Check: Ensure evaluation is based on skills, not names/origins.
    3. Assessment: List 3 technical interview questions based on gaps.
    
    Return JSON: {{"name": "str", "score": int, "summary": "str", "questions": [], "diversity_flag": bool}}
    """
    response = model.generate_content(prompt)
    data = json.loads(response.text.replace('```json', '').replace('```', ''))
    return {"results": [data]}

# --- 3. Build the Graph ---
def get_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("sourcing", sourcing_node)
    workflow.add_node("screening", screening_assessment_node)
    
    workflow.set_entry_point("sourcing")
    workflow.add_edge("sourcing", "screening")
    workflow.add_edge("screening", END)
    
    return workflow.compile()

def run_complex_agent(api_key, jd_text, files):
    genai.configure(api_key=api_key)
    app = get_workflow()
    final_results = []
    
    for i in range(len(files)):
        inputs = {"jd_text": jd_text, "files": files, "current_file_idx": i, "results": []}
        config = {"configurable": {"thread_id": str(i)}}
        output = app.invoke(inputs, config)
        final_results.append(output['results'][-1])
        
    return final_results
