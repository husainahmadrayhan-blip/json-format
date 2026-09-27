"""Check local-model source evidence, locked defaults and HTTP routing."""
import json
from unittest.mock import patch
from urllib.request import Request,urlopen
from verify_groq import local_server
from ollama_bridge import accepted_fields,prompt

raw='নাম: রহিম\nপিতার তথ্য\nEnglish: MD SHORIFUL\nমাতার তথ্য\nনাম বাংলায়: সালমা\nজন্ম তারিখ: 01/01/1990'
pending=['person.nameEn','father.nameEn','person.birthDate']
assert 'father.nameEn' in prompt(raw,pending,{})
accepted,rejected=accepted_fields(raw,pending,{'fields':{
    'person.nameEn':{'value':'MD SHORIFUL','source':'English: MD SHORIFUL'},
    'father.nameEn':{'value':'MD SHORIFUL','source':'English: MD SHORIFUL'},
    'person.birthDate':{'value':'01/01/1990','source':'জন্ম তারিখ: 01/01/1990'},
    'father.nationality':{'value':'99','source':'English: MD SHORIFUL'}}})
assert accepted.get('father.nameEn')=='MD SHORIFUL'
assert 'person.nameEn' in rejected and 'person.birthDate' in rejected
with local_server() as url:
    req=Request(url,data=json.dumps({'raw':raw,'model':'qwen2.5:3b'}).encode(),headers={'Content-Type':'application/json'},method='POST')
    answer={'fields':{'person.nameEn':{'value':'MD SHORIFUL','source':'English: MD SHORIFUL'},
                       'father.nameEn':{'value':'MD SHORIFUL','source':'English: MD SHORIFUL'}}}
    def mocked(path,payload=None,timeout=0):
        if path=='/api/tags':return {'models':[{'name':'qwen2.5:3b'}]}
        assert path=='/api/chat' and 'nationality' not in payload['messages'][0]['content'].split('Requested fields:')[-1].split('Existing fields')[0]
        return {'message':{'content':json.dumps(answer)}}
    with patch('server.ollama',side_effect=mocked):data=json.load(urlopen(req))
    assert data['method']=='rules+ollama'
    assert data['data']['person']['firstNameEn']==''
    assert data['data']['father']['nameEn']=='MD SHORIFUL'
    assert data['data']['person']['childOrder']=='4'
    assert data['data']['father']['nationality']==data['data']['mother']['nationality']=='1'
print('Ollama source and locked-field verification passed')
