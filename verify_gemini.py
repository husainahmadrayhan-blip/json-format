"""Offline Gemini REST contract and server routing checks."""
import io
import json
from unittest.mock import patch
from verify_groq import local_server
from urllib.request import Request,urlopen
from gemini_bridge import extract,ENDPOINT

raw='নাম: Rahim\nপিতার তথ্য\nনাম বাংলায়: করিম\nEnglish: MD SHORIFUL\nমাতার তথ্য\nনাম বাংলায়: সালমা'
assert __import__('groq_bridge').supported(raw,'father.nameEn','MD SHORIFUL','English: MD SHORIFUL')
seen=[]
def transport(req,timeout):
    seen.append((req.full_url,req.get_header('X-goog-api-key'),json.loads(req.data)))
    answer={'fields':{'father.nameEn':{'value':'MD SHORIFUL','source':'English: MD SHORIFUL'},
                       'mother.nameBn':{'value':'ভুল','source':'নাম বাংলায়: সালমা'}}}
    return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(answer,ensure_ascii=False)}]}}]},ensure_ascii=False).encode())
accepted,rejected=extract(raw,['father.nameEn','mother.nameBn'],'fake-gemini-key',transport)
assert accepted=={'father.nameEn':'MD SHORIFUL'} and rejected==['mother.nameBn']
assert seen[0][0]==ENDPOINT and seen[0][1]=='fake-gemini-key'
assert seen[0][2]['generationConfig']['responseFormat']['text']['mimeType']=='application/json'
with local_server() as url:
    request=lambda body:Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    with patch('server.gemini_extract',return_value=({'father.nameEn':'MD SHORIFUL'},[])) as mock:
        result=json.load(urlopen(request({'raw':raw,'provider':'gemini','apiKey':'fake-gemini-key'})))
    assert mock.called and 'person.nameBn' in mock.call_args.args[1]
    assert result['method']=='rules+gemini'
    assert result['data']['father']['nameEn']=='MD SHORIFUL'
    assert result['data']['father']['nationality']==result['data']['mother']['nationality']=='1'
    assert result['data']['person']['childOrder']=='4'
print('Gemini offline verification passed')
