import fitz
import docx
import json
import io
import google.generativeai as genai
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    jd_text: str
    files: list
    results: List[dict]
    current_file_idx: int

def sourcing_node(state: AgentState):
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
    """Tool: AI Screening & Matching"""
    raw_data = state['results'][-1]
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"JD: {state['jd_text']}\nResume: {raw_data['raw_text']}\n" \
             "Return JSON with: name, score (0-100), summary, diversity_flag (bool)."
    
    response = model.generate_content(prompt)
    clean_json = response.text.strip().replace('```json', '').replace('```', '')
    data = json.loads(clean_json)
    return {"results": [data]}

def invitation_tool_node(state: AgentState):
    """Tool: Automated Invitation Drafter"""
    candidate_data = state['results'][-1]
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # We explicitly instruct the AI to draft from your specific agent email
    prompt = f"""
    Draft a professional interview invitation email for {candidate_data['name']}.
    Sender: ai26agent@gmail.com
    Context: They scored {candidate_data['score']}/100 in our AI screening.
    Include: A friendly tone and a request for a follow-up call.
    Return ONLY the email body text.
    """
    
    response = model.generate_content(prompt)
    candidate_data['invitation_draft'] = response.text
    return {"results": [candidate_data]}

def get_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("sourcing", sourcing_node)
    workflow.add_node("screening", screening_node)
    workflow.add_node("invitation", invitation_tool_node) # New Node
    
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
        output = app.invoke({"jd_text": jd_text, "files": files, "current_file_idx": i, "results": []})
        final_results.append(output['results'][-1])
    return final_results
