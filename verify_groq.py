"""Offline Groq contract, evidence, and fixed-rule checks; never calls Groq."""
import io
import json
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from groq_bridge import GROQ_FIELDS, extract, supported, eligible_parent_year
from server import Handler
from rules import extract as local_extract
from server import validate

raw='নাম: রহিম\nDate of birth: 02/06/1996\nলিঙ্গ: ছেলে\nপিতার নাম: করিম\nমাতার নাম: সালমা\nসন্তান নং ০২'
assert len(GROQ_FIELDS)==12
assert supported(raw,'person.birthDate','02/06/1996','Date of birth: 02/06/1996')
assert supported('নাম: রহিম\n01/01/1990','person.birthDate','01/01/1990','01/01/1990')
assert supported(raw,'person.gender','MALE','লিঙ্গ: ছেলে')
assert supported(raw,'father.nameBn','করিম','পিতার নাম: করিম')
assert not supported(raw,'person.nameBn','করিম','পিতার নাম: করিম')
assert not supported(raw,'person.birthDate','01/01/1990','Date of birth: 02/06/1996')
assert not supported(raw,'father.nameBn','মিথ্যা','পিতার নাম: করিম')
assert not supported(raw,'person.gender','FEMALE','লিঙ্গ: ছেলে')
assert not supported(raw,'mother.nameBn','করিম','পিতার নাম: করিম')
assert not supported('মাতার নাম: সালমা\nজন্ম তারিখ: 02/06/1996','person.birthDate','02/06/1996','জন্ম তারিখ: 02/06/1996')
assert not supported('মাতার নাম: সালমা\nNID: 123\nফোন: 456\nজন্ম তারিখ: 02/06/1996','person.birthDate','02/06/1996','জন্ম তারিখ: 02/06/1996')
name_raw='নাম: SADIA\nপিতার :ঃ মো: শরিফুল\nEnglish: MD SHORIFUL\nমাতার নাম: মোছা: শারমিন খাতুন'
name_rules,_=local_extract(name_raw)
name_data,_=validate(name_raw,name_rules)
assert name_data['father']['nameBn']=='মোঃ শরিফুল',name_data['father']
assert name_data['father']['nameEn']=='MD SHORIFUL'
assert name_data['mother']['nameBn']=='মোছাঃ শারমিন খাতুন'
assert 'র :ঃ' not in name_data['father']['nameBn']
parent_raw='নাম: শিশুর নাম\nজন্ম তারিখ: ০১/০২/২০১৩\nপিতার নাম: করিম\nপিতার জন্ম নিবন্ধন: ১২৩৪৫৬৭৮৯০১২৩৪৫৬৭\nপিতার জন্ম তারিখ: 05/06/1980\nমাতার নাম: সালমা\nমাতার জন্ম নিবন্ধন: 98765432109876543\nমাতার জন্ম তারিখ: 07/08/1985'
assert eligible_parent_year(parent_raw,'01/02/2013')
assert not eligible_parent_year(parent_raw,'01/02/2012')
assert supported(parent_raw,'father.brn','12345678901234567','পিতার জন্ম নিবন্ধন: ১২৩৪৫৬৭৮৯০১২৩৪৫৬৭')
assert supported(parent_raw,'mother.birthDate','07/08/1985','মাতার জন্ম তারিখ: 07/08/1985')
assert not supported(parent_raw,'father.brn','98765432109876543','মাতার জন্ম নিবন্ধন: 98765432109876543')
assert not supported('পিতার NID: 12345678901234567','father.brn','12345678901234567','পিতার NID: 12345678901234567')
section_raw=('নাম বাংলায়ঃ মোঃ তাওহীদ হোসাইন\nজন্মতারিখঃ 06/02/2022\nপিতার তথ্য\n'
             'নাম বাংলায়ঃ মোঃ জাহাঙ্গীর আলম\nনাম ইংরেজিতেঃ Md Jahangir Alam\n'
             'জন্মনিবন্ধন নম্বরঃ 19858812731117384\nজন্মতারিখঃ 01/01/1985\n'
             'মাতার তথ্য\nনাম বাংলায়ঃ মোসাঃ ফাতেমা\nনাম ইংরেজিতেঃ Mst Fatema\n'
             'জন্মনিবন্ধন নম্বরঃ 19893313266085607\nজন্মতারিখঃ 01/01/1989')
assert supported(section_raw,'father.brn','19858812731117384','জন্মনিবন্ধন নম্বরঃ 19858812731117384')
assert supported(section_raw,'father.birthDate','01/01/1985','জন্মতারিখঃ 01/01/1985')
assert supported(section_raw,'mother.brn','19893313266085607','জন্মনিবন্ধন নম্বরঃ 19893313266085607')
assert supported(section_raw,'mother.birthDate','01/01/1989','জন্মতারিখঃ 01/01/1989')
assert not supported(section_raw,'father.brn','19893313266085607','জন্মনিবন্ধন নম্বরঃ 19893313266085607')

class FakeResponse(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

seen=[]
def fake_request(request,timeout):
    seen.append((request.full_url,request.get_header('Authorization'),json.loads(request.data)))
    content={'fields':{'father.nameBn':{'value':'করিম','source':'পিতার নাম: করিম'},
                       'person.nameBn':{'value':'করিম','source':'পিতার নাম: করিম'},
                       'person.birthDate':{'value':'01/01/1990','source':'Date of birth: 02/06/1996'},
                       'person.childOrder':{'value':'99','source':'সন্তান নং ০২'},
                       'father.nationality':{'value':'99','source':'পিতার নাম: করিম'}}}
    return FakeResponse(json.dumps({'choices':[{'message':{'content':json.dumps(content)}}]}).encode())
accepted,rejected=extract(raw,['father.nameBn','person.nameBn','person.birthDate'],'test-key',fake_request)
assert accepted=={'father.nameBn':'করিম'} and set(rejected)=={'person.nameBn','person.birthDate'}
assert seen[0][0]=='https://api.groq.com/openai/v1/chat/completions' and seen[0][1]=='Bearer test-key'
assert seen[0][2]['response_format']['type']=='json_schema'
assert 'childOrder' not in json.dumps(seen[0][2]['response_format'])
assert 'nationality' not in json.dumps(seen[0][2]['response_format'])
assert 'person.birthDate' in seen[0][2]['response_format']['json_schema']['schema']['properties']['fields']['properties']
assert 'father.birthDate' not in json.dumps(seen[0][2]['response_format'])
assert 'mother.birthDate' not in json.dumps(seen[0][2]['response_format'])

@contextmanager
def local_server():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield 'http://127.0.0.1:'+str(server.server_address[1])+'/api/parse'
    finally:server.shutdown();server.server_close();thread.join(timeout=2)

with local_server() as url:
    request=lambda body:Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    local=json.load(urlopen(request({'raw':section_raw})))
    assert local['data']['father']['brn']=='19858812731117384'
    assert local['data']['father']['birthDate']=='01/01/1985'
    assert local['data']['mother']['brn']=='19893313266085607'
    assert local['data']['mother']['birthDate']=='01/01/1989'
    with patch('server.groq_extract',return_value=({'person.nameEn':'Rahim Fake','person.birthDate':'01/01/1990'},[])) as mock:
        result=json.load(urlopen(request({'raw':raw,'provider':'groq','apiKey':'example-not-real'})))
    assert mock.called
    assert all(path in GROQ_FIELDS for path in mock.call_args.args[1])
    assert result['data']['person']['childOrder']=='2'
    assert result['data']['father']['nationality']=='1' and result['data']['mother']['nationality']=='1'
    assert result['data']['person']['firstNameEn']==''
    assert result['data']['person']['birthDate']=='02/06/1996'
    assert result['method']=='rules+groq'
    assert result['version'].startswith('v51-')
    try:urlopen(request({'raw':raw,'provider':'groq'}))
    except HTTPError as error:assert error.code==400
    else:raise AssertionError('missing key was accepted')
    with patch('server.groq_extract',return_value=({'person.childOrder':'99','father.nationality':'99'},[])):
        fixed=json.load(urlopen(request({'raw':'নাম: রহিম','provider':'groq','apiKey':'example-not-real'})))
    assert fixed['data']['person']['childOrder']=='4'
    assert fixed['data']['father']['nationality']=='1'
    only_date='নাম: রহিম Rahim\nলিঙ্গ: পুরুষ\nপিতার নাম: করিম Karim\nমাতার নাম: সালমা Salma\nজন্ম তারিখ: অস্পষ্ট'
    with patch('server.groq_extract',return_value=({},[])) as date_mock:
        date_result=json.load(urlopen(request({'raw':only_date,'provider':'groq','apiKey':'example-not-real'})))
    assert date_mock.call_args.args[1]==['person.birthDate']
    assert date_result['method']=='rules+groq'
    assert not date_result['data']['person']['birthDate']
    variant='নাম: রহিম\nজন্মের তারিখ: 01/01/1990'
    assert supported(variant,'person.birthDate','01/01/1990','জন্মের তারিখ: 01/01/1990')
    with patch('server.groq_extract',return_value=({'person.birthDate':'01/01/1990'},[])) as variant_mock:
        filled=json.load(urlopen(request({'raw':variant,'provider':'groq','apiKey':'example-not-real'})))
    assert 'person.birthDate' in variant_mock.call_args.args[1]
    assert filled['data']['person']['birthDate']=='01/01/1990'
    assert filled['data']['person']['childOrder']=='4'
    assert filled['data']['father']['nationality']==filled['data']['mother']['nationality']=='1'
    with patch('server.groq_extract',return_value=({'father.brn':'12345678901234567','father.birthDate':'05/06/1980','mother.brn':'98765432109876543','mother.birthDate':'07/08/1985'},[])) as parent_mock:
        newer=json.load(urlopen(request({'raw':parent_raw,'provider':'groq','apiKey':'example-not-real'})))
    if parent_mock.called:
        assert not set(('father.brn','father.birthDate','mother.brn','mother.birthDate')).intersection(parent_mock.call_args.args[1])
    assert newer['data']['father']['brn']=='12345678901234567'
    assert newer['data']['mother']['birthDate']=='07/08/1985'
    older=parent_raw.replace('২০১৩','২০১২')
    with patch('server.groq_extract',return_value=({},[])) as older_mock:
        earlier=json.load(urlopen(request({'raw':older,'provider':'groq','apiKey':'example-not-real'})))
    assert not set(('father.brn','father.birthDate','mother.brn','mother.birthDate')).intersection(older_mock.call_args.args[1])
    assert earlier['data']['father']['brn']==earlier['data']['mother']['birthDate']==''
print('Groq offline verification passed: schema, evidence, parent defaults, child order, missing key')
