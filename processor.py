import google.generativeai as genai
import json, io, fitz, docx
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
    ext = f.name.split('.')[-1].lower()
    file_bytes = f.getvalue()
    
    text = ""
    if ext == 'pdf':
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join([page.get_text() for page in doc])
    elif ext == 'docx':
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
    return {"results": [{"raw_text": text}]}

def screening_node(state: AgentState):
    raw_text = state['results'][-1]['raw_text']
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"JD: {state['jd_text']}\nResume: {raw_text}\nReturn JSON: {{'name': 'str', 'score': int, 'summary': 'str'}}"
    response = model.generate_content(prompt)
    data = json.loads(response.text.replace('```json', '').replace('```', ''))
    
    # Draft the invitation from your agent email
    invite_prompt = f"Draft an interview invite for {data['name']} from ai26agent@gmail.com. Score: {data['score']}."
    invite_res = model.generate_content(invite_prompt)
    data['invite_text'] = invite_res.text
    return {"results": [data]}

def run_complex_agent(api_key, jd_text, files):
    genai.configure(api_key=api_key)
    workflow = StateGraph(AgentState)
    workflow.add_node("sourcing", sourcing_node)
    workflow.add_node("screening", screening_node)
    workflow.set_entry_point("sourcing")
    workflow.add_edge("sourcing", "screening")
    workflow.add_edge("screening", END)
    app = workflow.compile()
    
    final_results = []
    for i in range(len(files)):
        output = app.invoke({"jd_text": jd_text, "files": files, "current_file_idx": i, "results": []})
        final_results.append(output['results'][-1])
    return final_results
