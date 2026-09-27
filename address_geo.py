"""Offline address completion using the supplied BDRIS_MASTER_GEO data."""
import json
import re
import unicodedata
from pathlib import Path

GEO_PATH = Path(__file__).with_name('BDRIS_MASTER_GEO.json')
GEO = json.loads(GEO_PATH.read_text(encoding='utf-8'))
DISTRICTS = [(division, district) for division in GEO['divisions'] for district in division['districts']]
GEO_NAMES = {norm for _,d in DISTRICTS for norm in (d.get('nameBn'),d.get('nameEn')) if norm}
GEO_NAMES.update(n for _,d in DISTRICTS for u in d['upazilas'] for n in (u.get('nameBn'),u.get('nameEn')) if n)
GEO_NAMES.update(n for _,d in DISTRICTS for u in d['upazilas'] for un in u['unions'] for n in (un.get('nameBn'),un.get('nameEn')) if n)
FIELD_LABELS = {
    'division': r'বিভাগ|division', 'district': r'জেলা|district',
    'upazila': r'উপজেলা|থানা|upazila|thana',
    'union': r'ইউনিয়ন|ইউনিয়ন|পৌরসভা|union|pourashava',
    'ward': r'ওয়ার্ড(?:\s*নং)?|ওয়ার্ড(?:\s*নং)?|ward(?:\s*no)?',
    'postOfficeBn': r'পোস্ট\s*অফিস|ডাক\s*(?:ঘর|গর|গোর)|ডাগ\s*ঘর|পোঃ?',
    'postOfficeEn': r'post\s*office|post\s*off(?:ice)?|\bp\.?o\.?\b',
    'villageBn': r'গ্রাম|গেরাম|মহল্লা', 'villageEn': r'village|\bvill\b',
    'postCode': r'পোস্ট\s*কোড|ডাক\s*কোড|post\s*code|postal\s*code',
}
LABEL = re.compile(r'^\s*('+'|'.join('(?:'+p+')' for p in FIELD_LABELS.values())+r')\s*[:：ঃ=\-–—]?\s*(.*?)\s*$', re.I)
ROLE = re.compile(r'জন্ম\s*স্থান|জন্মস্থান|birth\s*place|place\s*of\s*birth|স্থায়ী\s*ঠিকানা|স্থায়ী\s*ঠিকানা|permanent\s*address|বর্তমান\s*ঠিকানা|present\s*address', re.I)
BN = re.compile(r'[\u0980-\u09ff][\u0980-\u09ff\s.\-]*')
EN = re.compile(r'[A-Za-z][A-Za-z\s.\-]*')
DIGITS = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')

def norm(value):
    text=unicodedata.normalize('NFC',str(value or '')).translate(DIGITS).casefold()
    text=text.replace('কপোরেশন','কর্পোরেশন').replace('করপোরেশন','কর্পোরেশন')
    return re.sub(r'[^\w\u0980-\u09ff]+', '', text)

def geo_name_line(value):
    return norm(value) in GEO_NAMES

def same(text, item):
    t = norm(text)
    return bool(t and t in {norm(item.get('nameBn')), norm(item.get('nameEn'))})

def pick(items, value):
    if not value: return None
    found = [item for item in items if same(value, item)]
    return found[0] if len(found) == 1 else None

def split_languages(value):
    b = BN.search(value); e = EN.search(value)
    return (b.group().strip() if b else '', e.group().strip() if e else '')

def read_blocks(raw):
    blocks = {'birthPlace': [], 'permanentAddress': [], 'presentAddress': []}
    current = 'birthPlace'
    for line in raw.splitlines():
        s = line.strip(' \t*•')
        if not s: continue
        marker = ROLE.search(s)
        if marker:
            name = marker.group().casefold()
            current = ('permanentAddress' if 'স্থায়ী' in name or 'স্থায়ী' in name or 'permanent' in name else
                       'presentAddress' if 'বর্তমান' in name or 'present' in name else 'birthPlace')
        # A person or parent field ends an address section.
        if re.match(r'^(?:পিতার\s*নাম|মাতার\s*নাম|father|mother)\s*[:ঃ：=]',s,re.I):
            current = None
        if current is None and (marker or LABEL.match(s) or geo_name_line(s)):
            if marker: pass
            else: current='birthPlace'
        if current: blocks[current].append(s)
    return blocks

def explicit_values(lines):
    values = {}
    for line in lines:
        m = LABEL.match(line)
        if not m: continue
        label, value = m.groups()
        value = value.strip(' \t,;:ঃ-')
        if not value: continue
        field = next((k for k,p in FIELD_LABELS.items() if re.fullmatch(p,label,re.I)),None)
        if not field: continue
        if field in ('postOfficeBn','postOfficeEn','villageBn','villageEn'):
            english = re.search(r'[A-Za-z]',value)
            before,after=(value[:english.start()].strip(),value[english.start():].strip()) if english else (value,'')
            bn = before if re.search(r'[\u0980-\u09ff]',before) else ''
            en = after if english else (before if re.search(r'[A-Za-z]',before) else '')
            stem = 'postOffice' if field.startswith('postOffice') else 'village'
            if bn: values.setdefault(stem+'Bn',bn)
            if en: values.setdefault(stem+'En',en)
            if stem=='postOffice':
                code=re.search(r'(?<![0-9০-৯])([0-9০-৯]{4})(?![0-9০-৯])',value)
                if code:values.setdefault('postCode',code.group(1).translate(DIGITS))
        elif field in ('division','district','upazila','union'):
            bn,en=split_languages(value)
            values.setdefault(field,bn or en or value)
        else: values.setdefault(field,value.translate(DIGITS) if field=='postCode' else value)
    # Standalone geo names in a WhatsApp address block can omit all labels.
    bare=[line.strip() for line in lines if not LABEL.match(line) and not ROLE.search(line) and geo_name_line(line)]
    if not values.get('district'):
        districts=[d for _,d in DISTRICTS for line in bare if same(line,d)]
        if len({d['id'] for d in districts})==1:values['district']=next(line for line in bare if same(line,districts[0]))
    district=next((d for _,d in DISTRICTS if same(values.get('district'),d)),None)
    if district:
        if not values.get('upazila'):
            found=[u for u in district['upazilas'] for line in bare if same(line,u)]
            if len({u['id'] for u in found})==1:values['upazila']=next(line for line in bare if same(line,found[0]))
        if not values.get('union'):
            found=[un for u in district['upazilas'] for un in u['unions'] for line in bare if same(line,un)]
            if len({un['id'] for un in found})==1:values['union']=next(line for line in bare if same(line,found[0]))
    return values

def complete_one(lines):
    values = explicit_values(lines)
    report, warnings = {}, []
    if not values: return {}, report, warnings
    labeled=explicit_values([line for line in lines if LABEL.match(line)])
    for field,value in values.items():
        report[field] = {'source':'input' if field in labeled else 'input-order','detail':value}
    if any(item['source']=='input-order' for item in report.values()):
        warnings.append('লেবেল ছাড়া ঠিকানার নাম তালিকার সঙ্গে মিলেছে; ক্রম যাচাই করুন')
    district_matches = [(div,d) for div,d in DISTRICTS if same(values.get('district'),d)]
    if len(district_matches) == 1:
        div, district = district_matches[0]
    elif values.get('district'):
        original=values.pop('district')
        report.pop('district',None)
        warnings.append(f'দেওয়া জেলা "{original}" ৬৪ জেলার ডেটায় মেলেনি; জেলা/উপজেলা/ইউনিয়ন/ওয়ার্ড খালি রাখা হয়েছে')
        for field in ('upazila','union','ward'):values.pop(field,None);report.pop(field,None)
        return values,report,warnings
    else:
        # With no district, resolve only a unique upazila/union across the country.
        candidates = [(div,d,u) for div,d in DISTRICTS for u in d['upazilas'] if same(values.get('upazila'),u) or any(same(values.get('union'),un) for un in u['unions'])]
        if len(candidates)!=1:
            warnings.append('জেলা নেই এবং উপজেলা/ইউনিয়ন এককভাবে মেলেনি')
            return values,report,warnings
        div,district,_ = candidates[0]
    def fill(field,value,kind,detail):
        if not values.get(field) and value:
            values[field] = value
            report[field] = {'source':kind,'detail':detail}
    for field,official in (('district',district['nameBn']),('division',div['nameBn'])):
        supplied=values.get(field)
        if supplied and norm(supplied)!=norm(official):
            warnings.append(f'দেওয়া {field} "{supplied}" Geo Data অনুযায়ী "{official}" করা হয়েছে')
            values[field]=official;report[field]={'source':'geo','detail':f'ইনপুট: {supplied}'}
        else: fill(field,official,'geo','জেলার তথ্য')
    fill('country','1','default','দেশের ডিফল্ট')
    # The supplied geo tree has no village or post-office catalog; leave
    # missing values empty rather than adding an unrelated locality.
    upazilas=district['upazilas']
    upazila=pick(upazilas,values.get('upazila'))
    if values.get('upazila') and not upazila:
        original=values.pop('upazila')
        warnings.append(f'দেওয়া উপজেলা "{original}" জেলার ডেটায় মেলেনি; উপজেলা/ইউনিয়ন/ওয়ার্ড খালি রাখা হয়েছে')
        report.pop('upazila',None)
        values.pop('union',None);report.pop('union',None)
        values.pop('ward',None);report.pop('ward',None)
        return values,report,warnings
    if not upazila and values.get('union'):
        candidates=[u for u in upazilas if any(same(values['union'],un) for un in u['unions'])]
        if len(candidates)==1:upazila=candidates[0]
        else:
            original=values.pop('union')
            warnings.append(f'দেওয়া ইউনিয়ন "{original}" জেলায় এককভাবে মেলেনি; ইউনিয়ন/ওয়ার্ড খালি রাখা হয়েছে')
            report.pop('union',None)
            values.pop('ward',None);report.pop('ward',None)
            return values,report,warnings
    if not upazila and upazilas:upazila=upazilas[0]
    if not upazila:
        warnings.append('জেলায় উপজেলা পাওয়া যায়নি');return values,report,warnings
    fill('upazila',upazila['nameBn'],'geo','জেলার প্রথম উপজেলা' if not values.get('union') else 'দেওয়া ইউনিয়নের উপজেলা')
    if values.get('upazila') and values['upazila']!=upazila['nameBn']:
        supplied=values['upazila'];values['upazila']=upazila['nameBn']
        report['upazila']={'source':'geo','detail':f'মেলা ইনপুট: {supplied}'}
        warnings.append(f'দেওয়া উপজেলা "{supplied}" Geo Data অনুযায়ী "{upazila["nameBn"]}" করা হয়েছে')
    unions=upazila.get('unions') or []
    union=pick(unions,values.get('union'))
    if values.get('union') and not union:
        original=values.pop('union')
        warnings.append(f'দেওয়া ইউনিয়ন "{original}" উপজেলার ডেটায় মেলেনি; ইউনিয়ন/ওয়ার্ড খালি রাখা হয়েছে')
        report.pop('union',None)
        values.pop('ward',None);report.pop('ward',None)
        return values,report,warnings
    if not union and unions: union=unions[0]
    if union:fill('union',union['nameBn'].strip(),'geo','উপজেলার প্রথম ইউনিয়ন')
    else:warnings.append('উপজেলায় ইউনিয়ন পাওয়া যায়নি')
    if union and values.get('union') and values['union']!=union['nameBn'].strip():
        supplied=values['union'];values['union']=union['nameBn'].strip()
        report['union']={'source':'geo','detail':f'মেলা ইনপুট: {supplied}'}
    if union and values.get('ward'):
        wards=union.get('wards') or []
        supplied=norm(values['ward'])
        valid=any(supplied==norm(w.get('wardNumber')) or supplied==norm(w.get('nameBn')) or
                  (re.search(r'[০-৯0-9]+',w.get('nameBn','')) and supplied==norm(re.search(r'[০-৯0-9]+',w['nameBn']).group())) for w in wards)
        if not valid:
            warnings.append('দেওয়া ওয়ার্ড ইউনিয়নের ডেটার সঙ্গে মেলেনি; ওয়ার্ড খালি রাখা হয়েছে')
            values.pop('ward',None)
            report.pop('ward',None)
            return values,report,warnings
    if union and not values.get('ward'):
        wards=union.get('wards') or []
        if wards:
            value = str(wards[0].get('wardNumber') or '')
            if not value:
                m=re.search(r'[০-৯0-9]+',wards[0].get('nameBn',''))
                value=m.group().translate(DIGITS) if m else ''
            fill('ward',value,'geo','ইউনিয়নের প্রথম ওয়ার্ড')
        else:warnings.append('ইউনিয়নের ওয়ার্ড ডেটা নেই; ওয়ার্ড খালি রাখা হয়েছে')
    return values,report,warnings

def complete_addresses(raw, data):
    reports,warnings = {},[]
    for role,lines in read_blocks(raw).items():
        values,report,notes = complete_one(lines)
        if not values:continue
        for field,default in {'country':'1'}.items():
            if not values.get(field):
                values[field]=default
                report[field]={'source':'default','detail':'ব্যবহারকারীর নির্ধারিত ডিফল্ট'}
        data[role].update(values)
        reports[role] = report
        warnings.extend(role+': '+note for note in notes)
    return reports,warnings
