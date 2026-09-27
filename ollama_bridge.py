"""Locally validate Ollama suggestions against the same source rules as cloud APIs."""
import json
from groq_bridge import GROQ_FIELDS, payload, supported

def prompt(raw,pending,locked):
    instructions=payload(raw,pending)['messages'][0]['content']
    return (instructions+' Return ONLY a JSON object with a fields property, where each '
            'requested path has a value and source string. Source must be one exact line from '
            'the original input. Empty values need empty sources. Existing fields are locked: '
            +json.dumps(locked,ensure_ascii=False))

def accepted_fields(raw,pending,response):
    if not isinstance(response,dict):raise ValueError('Ollama-এর JSON object পাওয়া যায়নি')
    items=response.get('fields',{})
    if not isinstance(items,dict):items={}
    accepted,rejected={},[]
    for path in pending:
        if path not in GROQ_FIELDS:continue
        proposal=items.get(path)
        role,field=path.split('.',1)
        if not isinstance(proposal,dict):
            role_data=response.get(role)
            proposal=role_data.get(field) if isinstance(role_data,dict) else None
        if isinstance(proposal,dict):value,source=proposal.get('value'),proposal.get('source')
        else:value,source=proposal,None
        if not isinstance(value,str) or not value.strip():continue
        # Older local models may return the nested value without its source.
        # Infer evidence only if exactly one line supports this exact value and role.
        if not isinstance(source,str) or not source.strip():
            matches=[line.strip() for line in raw.splitlines() if supported(raw,path,value,line.strip())]
            source=matches[0] if len(matches)==1 else ''
        if supported(raw,path,value,source):accepted[path]=value.strip()
        else:rejected.append(path)
    return accepted,rejected
