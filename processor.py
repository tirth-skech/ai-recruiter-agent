import fitz
import docx
import json
import io
import google.generativeai as genai
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

# Ensure no trailing commas in the class definition or unclosed brackets
class AgentState(TypedDict):
    jd_text: str
    files: list
    results: List[dict]
    current_file_idx: int

def sourcing_node(state: AgentState):
    idx = state['current_file_idx']
    f = state['files'][idx]
    ext = f.name.split('.')[-1].lower()
    file_bytes = f.getvalue() 
    
    text = ""
    if ext == 'pdf':
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = chr(12).join([page.get_text() for page in doc])
    elif ext == 'docx':
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
    
    return {"results": [{"raw_text": text, "filename": f.name}]}

def screening_assessment_node(state: AgentState):
    raw_data = state['results'][-1]
    
    # Use the stable string for Gemini 2.5 Flash
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    JD: {state['jd_text']}
    RESUME: {raw_data['raw_text']}
    
    TASK: Return ONLY valid JSON:
    {{
        "name": "Candidate Name", 
        "score": 85, 
        "summary": "Match details", 
        "questions": ["Q1", "Q2"], 
        "diversity_flag": true
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean potential markdown from response
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_json)
        return {"results": [data]}
    except Exception as e:
        return {
            "results": [{
                "name": f"Error: {raw_data.get('filename', 'Unknown')}", 
                "score": 0, 
                "summary": str(e), 
                "questions": [], 
                "diversity_flag": False
            }]
        }

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
        inputs = {
            "jd_text": jd_text, 
            "files": files, 
            "current_file_idx": i, 
            "results": []
        }
        output = app.invoke(inputs)
        final_results.append(output['results'][-1])
        
    return final_results
