"""Optional Gemini API provider; shares strict source evidence checks with Groq."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from groq_bridge import payload as groq_payload, supported

MODEL='gemini-2.5-flash'
ENDPOINT='https://generativelanguage.googleapis.com/v1beta/models/'+MODEL+':generateContent'

def payload(raw,missing):
    contract=groq_payload(raw,missing)
    schema=contract['response_format']['json_schema']['schema']
    return {'contents':[{'role':'user','parts':[{'text':contract['messages'][0]['content']+'\nOriginal text:\n'+raw}]}],
            'generationConfig':{'responseFormat':{'text':{'mimeType':'application/json','schema':schema}}}}

def extract(raw,missing,key,transport=urlopen):
    if not isinstance(key,str) or not key.strip() or any(c in key for c in '\r\n'):
        raise ValueError('Gemini API key দিন')
    request=Request(ENDPOINT,data=json.dumps(payload(raw,missing),ensure_ascii=False).encode('utf-8'),
                    headers={'x-goog-api-key':key.strip(),'Content-Type':'application/json'},method='POST')
    try:
        with transport(request,timeout=75) as response:result=json.load(response)
    except HTTPError as error:
        raise ValueError('Gemini API HTTP '+str(error.code)+'; key, quota ও model যাচাই করুন') from None
    except (URLError,TimeoutError,OSError) as error:
        raise ValueError('Gemini API সংযোগ ব্যর্থ: '+type(error).__name__) from None
    try:
        parts=result['candidates'][0]['content']['parts']
        answer=json.loads(''.join(part.get('text','') for part in parts))
        fields=answer['fields']
        if not isinstance(fields,dict):raise ValueError()
    except (KeyError,IndexError,TypeError,json.JSONDecodeError,ValueError):
        raise ValueError('Gemini-এর JSON উত্তর গ্রহণ করা যায়নি') from None
    accepted,rejected={},[]
    for path in missing:
        proposal=fields.get(path)
        if not isinstance(proposal,dict):continue
        value,source=proposal.get('value'),proposal.get('source')
        if not value:continue
        if supported(raw,path,value,source):accepted[path]=value.strip()
        else:rejected.append(path)
    return accepted,rejected
