"""District-first address candidates and compact, authoritative Geo option trees."""
import re
import unicodedata
from address_geo import DISTRICTS, DIGITS, GEO, LABEL, explicit_values, norm, pick, same
from locality_romanization import romanize_locality
from locality_bengalization import bengalize_locality, BN_DIGITS

ADDRESS_CUE = re.compile(r'ঠিকানা|address|জন্ম\s*স্থান|birth\s*place|place\s*of\s*birth|জেলা|district|zilla|উপজেলা|upazila|thana|ইউনিয়ন|ইউনিয়ন|union|পৌরসভা|গ্রাম|village|\bvill\b|ডাকঘর|ডাক\s*ঘর|post\s*office|পোস্ট|ওয়ার্ড|ward|\broad\b|রাস্তা', re.I)
PERSON_CUE = re.compile(r'^(?:নাম|পিতার\s*নাম|মাতার\s*নাম|father|mother|name|dob|জন্ম\s*তারিখ|লিঙ্গ)\s*[:：ঃ=\-]', re.I)
ADDRESS_HEADING = re.compile(r'ঠিকানা|address|জন্মস্থান|birth\s*place', re.I)

def phrase_in(text, name):
    """Find a whole Geo phrase, not a substring inside a person's word."""
    if not name:return False
    text=unicodedata.normalize('NFC',str(text))
    name=unicodedata.normalize('NFC',str(name))
    boundary=r'[A-Za-z\u0980-\u09ff]'
    words=[re.escape(x) for x in str(name).strip().split()]
    if not words:return False
    return bool(re.search(r'(?<!'+boundary+r')'+r'\s+'.join(words)+r'(?!'+boundary+r')',text,re.I))

def district_on_line(line):
    line=re.sub(r'^[^A-Za-z\u0980-\u09ff0-9]+','',line).strip()
    if PERSON_CUE.match(line):return []
    if re.match(r'^\s*(?:বিভাগ|division)\s*[:：ঃ=\-]',line,re.I):return []
    parts=[part.strip() for part in re.split(r'[,，،;|]',line) if part.strip()]
    strong=bool(ADDRESS_CUE.search(line) or len(parts)>1)
    local_label=bool(re.match(r'^(?:উপজেলা|upazila|upazilla|thana|ইউনিয়ন|ইউনিয়ন|union|পৌরসভা|গ্রাম|village|vill\b|ডাকঘর|ডাক\s*ঘর|post\s*office|পোস্ট|ওয়ার্ড|ward)\s*[:：ঃ=\-]',line,re.I))
    matches=[]
    for div,d in DISTRICTS:
        names=(d['nameBn'],d['nameEn'])
        standalone=any(same(part,d) or (
            bool(re.match(r'^(?:জেলা|districts?|zilla|dis)\s*[:：ঃ=\-]\s*(.*)$',part,re.I)) and
            same(re.match(r'^(?:জেলা|districts?|zilla|dis)\s*[:：ঃ=\-]\s*(.*)$',part,re.I).group(1),d))
            for part in parts)
        if not standalone and len(parts)>1:
            # A final district-postcode token in a multi-part address.
            standalone=any(re.fullmatch(re.escape(name)+r'\s*[-–]\s*[০-৯0-9]{4}',parts[-1],re.I)
                           for name in names if name)
        if standalone:
            matches.append((div,d));continue
        # 'উপজেলা: কিশোরগঞ্জ সদর' and 'ডাকঘর: পঞ্চগড়-৫০০০'
        # contain district names but are not district assertions.
        if local_label:continue
        if strong and any(phrase_in(line,name) for name in names):
            matches.append((div,d));continue
        if any(phrase_in(line,name) for name in names) and any(
            phrase_in(line,up.get('nameBn')) or phrase_in(line,up.get('nameEn'))
            for up in d.get('upazilas') or []):
            matches.append((div,d))
    return matches

DEFAULT_LOCALITY = {'postOfficeBn':'চন্দ্র নগর','postOfficeEn':'Chondon Nogor','villageBn':'সাতকাপন','villageEn':'Satkapon'}

LOCALITY_LABELS = {
    'postOffice': re.compile(r'^(?:ডাক\s*(?:ঘর|গর|গোর)|ডাগ\s*ঘর|পোস্ট\s*(?:অফিস|অফিস্)|পোঃ?|post\s*office|post\s*off(?:ice)?|p\.?\s*o\.?)\s*(?:\(?\s*(?:বাংলা(?:য়|য়)?|ইংরেজি|bangla|english)\s*\)?)?\s*[:：ঃ=\-–—]\s*',re.I),
    'village': re.compile(r'^(?:গ্রাম\s*/\s*(?:মহল্লা|পাড়া)|গ্রাম|গেরাম|মহল্লা|village|vill\.?)\s*(?:\(?\s*(?:বাংলা(?:য়|য়)?|ইংরেজি|bangla|english)\s*\)?)?\s*[:：ঃ=\-–—]\s*',re.I),
}

def clean_locality_field(stem,value):
    """Remove only clear field labels, never unlabelled place-name words."""
    result=str(value or '').strip()
    for _ in range(3):
        newer=LOCALITY_LABELS[stem].sub('',result).strip()
        if newer==result:break
        result=newer
    return result

def complete_locality_languages(address,sources):
    """Preserve written spellings; keep Latin and Bengali in their own fields."""
    for stem in ('postOffice','village'):
        bn,en=stem+'Bn',stem+'En'
        for key in (bn,en):
            if address.get(key):
                cleaned=clean_locality_field(stem,address[key])
                if cleaned:address[key]=cleaned
                else:address.pop(key,None);sources.pop(key,None)
        if sources.get(en,{}).get('source')=='transliteration' and address.get(bn):
            # Rebuild translated text after stripping a Bengali field label.
            address[en]=romanize_locality(address[bn])
        bn_value=str(address.get(bn) or '')
        en_value=str(address.get(en) or '')
        if re.search(r'[A-Za-z]',bn_value) and not re.search(r'[\u0980-\u09ff]',bn_value):
            if not en_value:
                address[en]=bn_value.translate(DIGITS)
                sources[en]=sources.get(bn,{'source':'input'})
            address.pop(bn,None);sources.pop(bn,None)
        if re.search(r'[\u0980-\u09ff]',en_value) and not re.search(r'[A-Za-z]',en_value):
            if not address.get(bn):
                address[bn]=en_value.translate(BN_DIGITS)
                sources[bn]=sources.get(en,{'source':'input'})
            address.pop(en,None);sources.pop(en,None)
        if address.get(bn):address[bn]=address[bn].translate(BN_DIGITS)
        if address.get(en):address[en]=address[en].translate(DIGITS)
        if address.get(bn) and not address.get(en):
            spelling=romanize_locality(address[bn])
            if spelling:
                address[en]=spelling;sources[en]={'source':'transliteration','from':bn}
        if address.get(en) and not address.get(bn):
            spelling=bengalize_locality(address[en])
            if spelling:
                address[bn]=spelling;sources[bn]={'source':'transliteration','from':en}
        if address.get(en):
            english=unicodedata.normalize('NFKD',str(address[en])).replace('–','-').replace('—','-')
            address[en]=english.encode('ascii','ignore').decode('ascii').strip()

def address_role(text):
    first=text.splitlines()[0] if text else ''
    if re.search(r'স্থায়ী|স্থায়ী|permanent',first,re.I):return 'permanent'
    if re.search(r'বর্তমান|present',first,re.I):return 'present'
    if re.search(r'জন্ম\s*স্থান|birth\s*place|place\s*of\s*birth',first,re.I):return 'birth'
    return ''

def ward_value(ward):
    val=str(ward.get('wardNumber') or '').translate(DIGITS)
    if val:return val
    match=re.search(r'[০-৯0-9]+', ward.get('nameBn') or ward.get('nameEn') or '')
    return match.group().translate(DIGITS) if match else ''

def district_anchors(lines):
    anchors=[]
    for index,line in enumerate(lines):
        unique={d['id']:(div,d) for div,d in district_on_line(line)}
        if len(unique)==1:anchors.append((index,*next(iter(unique.values()))))
    return anchors

def select_branch(district, explicit):
    upazilas=district.get('upazilas') or []
    warnings=[]
    supplied_u=explicit.get('upazila')
    supplied_un=explicit.get('union')
    u=pick(upazilas,supplied_u) if supplied_u else None
    if supplied_u and not u:
        pass
    if not u and supplied_un:
        matching=[up for up in upazilas if any(same(supplied_un,un) for un in up.get('unions') or [])]
        if len(matching)==1:u=matching[0]
    # District-only input: choose a branch with a real ward record when one exists.
    if not u:
        u=next((up for up in upazilas if any(un.get('wards') for un in up.get('unions') or [])),None)
        u=u or next((up for up in upazilas if up.get('unions')),None)
    if not u:return None,None,None,warnings+['এই জেলায় Geo Data-তে কোনো উপজেলা/ইউনিয়ন নেই']
    unions=u.get('unions') or []
    un=pick(unions,supplied_un) if supplied_un else None
    if supplied_un and not un:
        pass
    if not un:
        un=next((item for item in unions if item.get('wards')),None) or next(iter(unions),None)
    if not un:return u,None,None,warnings+['এই উপজেলায় Geo Data-তে কোনো ইউনিয়ন নেই']
    wards=un.get('wards') or []
    raw_ward=str(explicit.get('ward') or '').translate(DIGITS).strip()
    digits=re.search(r'\d+',raw_ward)
    given=str(int(digits.group())) if digits else raw_ward
    ward=next((w for w in wards if ward_value(w)==given),None) if given else None
    # Unmatched supplied ward falls back to a ward under the selected union.
    ward=ward or next((w for w in wards if ward_value(w)),None)
    if not ward:warnings.append('এই ইউনিয়নের Geo Data-তে ওয়ার্ড নেই; অনুমান করে ওয়ার্ড বসানো হয়নি')
    return u,un,ward,warnings

def normalize_fragment(value):
    text=re.sub(r'^[^A-Za-z\u0980-\u09ff0-9]+','',value).strip()
    text=re.sub(r'^গ্ৰাম', 'গ্রাম', text)
    text=re.sub(r'^(?:স্থায়ী|স্থায়ী|বর্তমান|জন্মস্থানের)?\s*ঠিকানা\s*(?:বাংলা|ইংরেজি|English|Bangla)?\s*[:ঃ：\-]\s*(?=(?:গ্রাম|village|vill\b|ডাকঘর|post\s*office|পোস্ট|জেলা|district|উপজেলা|upazila)\b)', '', text,flags=re.I)
    text=re.sub(r'^গ্রাম\s*[/()]\s*(?:রাস্তা|বাংলা)\s*[)]?', 'গ্রাম', text)
    text=re.sub(r'^Village\s*\(English\)', 'Village', text,flags=re.I)
    text=re.sub(r'^গ্রাম\s*[;；]\s*', 'গ্রাম: ', text)
    text=re.sub(r'^ডাক\s*ঘর\s*(?:\(?পোস্ট\s*কোড\)?\s*সহ|কোড\s*সহ)', 'ডাকঘর', text)
    text=re.sub(r'^Post\s*Office\s*with\s*Code', 'Post Office', text,flags=re.I)
    text=re.sub(r'^(?:P\s*[/\.]\s*O\.?|PO\b|Postoffice\b)', 'Post Office', text,flags=re.I)
    text=re.sub(r'^পোস্ট\s*কোর্ড', 'পোস্ট কোড', text)
    return text.strip()

HOUSE_LABEL=re.compile(r'^(?:বাসা(?:/হোল্ডিং)?(?:\s*নং)?|বাড়ি|বাড়ি|হোল্ডিং(?:\s*নং)?|house(?:/holding)?(?:\s*no)?|holding(?:\s*no)?|c/o)\s*[:ঃ：=\-]\s*(.+)$',re.I)

def locality_fragments(segment, district):
    fragments=[]
    for line in segment:
        text=normalize_fragment(line)
        # Unwrap address headings around a field label on the same line.
        text=re.sub(r'^(?:স্থায়ী|স্থায়ী|বর্তমান|জন্মস্থানের)?\s*ঠিকানা\s*(?:বাংলা|English|ইংরেজি)?\s*[:ঃ：=\-]\s*(?=গ্রাম|village|vill\b|ডাকঘর|post\s*office|পোস্ট|উপজেলা|জেলা)', '', text,flags=re.I)
        parts=[normalize_fragment(part) for part in re.split(r'[,，،;|]',text) if part.strip()]
        if parts and re.match(r'^(?:গ্রাম|village|vill\b|বাসা|বাড়ি|বাড়ি|house|holding)\s*[:ঃ：=\-]',parts[0],re.I):
            # Commas inside an actual village/house name belong to its value.
            stop=1
            while stop<len(parts):
                part=parts[stop]
                if (LABEL.match(part) or HOUSE_LABEL.match(part) or
                    re.search(r'[0-9০-৯]{4}',part) or
                    re.search(r'[০-৯0-9]+\s*(?:নং|no\.?)?\s*(?:ওয়ার্ড|ওয়াড|ward|word)',part,re.I) or
                    same(part,district) or any(same(part,up) or any(same(part,un) for un in up.get('unions') or [])
                                              for up in district.get('upazilas') or [])):
                    break
                parts[0]+=', '+part
                stop+=1
            parts=parts[:1]+parts[stop:]
        for part_index,part in enumerate(parts):
            fragments.append(part)
            if part_index==1 and re.search(r'(?<![0-9০-৯])[0-9০-৯]{4}(?![0-9০-৯])',part):
                first=parts[0]
                if re.match(r'^\s*(?:village|vill\b|গ্রাম|মহল্লা)\s*[:：ঃ=\-]',first,re.I) and not LABEL.match(part):
                    field='Post Office' if re.search(r'[A-Za-z]',part) else 'ডাকঘর'
                    fragments[-1]=field+': '+part
    return fragments

def ordered_locality(segment, inputs):
    """Postal/village values in declared order after an address ward."""
    ward_at=next((i for i,line in enumerate(segment) if re.search(r'(?:ওয়ার্ড|ওয়াড|ওয়াড|ward|word)\s*(?:নং|no\.?)?\s*[:ঃ：=\-]?\s*[০-৯0-9]',line,re.I)),None)
    if ward_at is None:return
    pieces=[]
    for line in segment[ward_at+1:]:
        text=normalize_fragment(line)
        if PERSON_CUE.match(text) or re.search(r'পিতার\s*তথ্য|মাতার\s*তথ্য|father.*information|mother.*information',text,re.I):break
        if not text or ADDRESS_HEADING.search(text) or LABEL.match(text) or HOUSE_LABEL.match(text):continue
        if ',' in text or ':' in text or len(text)>70:continue
        if re.fullmatch(r'[\u0980-\u09ff\s.\-০-৯0-9]+',text) or re.fullmatch(r'[A-Za-z\s.\-0-9]+',text):
            pieces.append(text.strip(' .'))
        if len(pieces)>=4:break
    bn=lambda x:bool(re.search(r'[\u0980-\u09ff]',x))
    en=lambda x:bool(re.search(r'[A-Za-z]',x))
    if len(pieces)==4 and bn(pieces[0]) and en(pieces[1]) and bn(pieces[2]) and en(pieces[3]):
        for field,value in zip(('postOfficeBn','postOfficeEn','villageBn','villageEn'),pieces):inputs.setdefault(field,value)
    elif len(pieces)==2 and bn(pieces[0]) and bn(pieces[1]):
        inputs.setdefault('postOfficeBn',pieces[0]);inputs.setdefault('villageBn',pieces[1])
    else:return
    post=inputs.get('postOfficeBn') or inputs.get('postOfficeEn') or ''
    code=re.search(r'(?<![০-৯0-9])([০-৯0-9]{4})(?![০-৯0-9])',post)
    if code:inputs.setdefault('postCode',code.group(1).translate(DIGITS))

def candidates(raw):
    lines=[line.strip() for line in raw.splitlines() if line.strip()]
    anchors=district_anchors(lines)
    found=[]
    for i,(line_index,div,district) in enumerate(anchors[:16]):
        prior=anchors[i-1][0]+1 if i else 0
        next_index=anchors[i+1][0] if i+1<len(anchors) else len(lines)
        # If a new explicit address heading occurs, associate preceding village/postal lines with this district.
        headings=[j for j in range(prior,line_index+1) if ADDRESS_HEADING.search(lines[j])]
        start=headings[-1] if headings else (line_index if i else 0)
        if len(headings)>=2 and address_role(lines[headings[-2]]) and address_role(lines[headings[-2]])==address_role(lines[headings[-1]]) and headings[-1]-headings[-2]<=14:
            start=headings[-2]
        segment=lines[start:next_index]
        fragments=locality_fragments(segment,district)
        inputs=explicit_values(fragments)
        # In an unlabeled bilingual address, the first comma-separated value
        # before a verified union/upazila/district is the written locality.
        # Keep each language's original spelling instead of using defaults.
        for source_line in segment:
            chunks=[normalize_fragment(x) for x in re.split(r'[,，،]',source_line) if x.strip()]
            if len(chunks)<3 or not chunks[0] or re.search(r'\d|[:ঃ]|\b(?:village|post|district|upazila)\b',chunks[0],re.I):continue
            if not any(same(x,district) for x in chunks[1:]):continue
            first=chunks[0].strip(' .।')
            if re.fullmatch(r'[\u0980-\u09ff\s]+',first):inputs.setdefault('villageBn',first)
            elif re.fullmatch(r'[A-Za-z\s]+',first):inputs.setdefault('villageEn',first)
        ordered_locality(segment,inputs)
        for line in segment:
            normalized=normalize_fragment(line)
            # Additional field labels can appear after a care-of or ward prefix.
            for m in re.finditer(r'(?<![A-Za-z])(?:Vill(?:age)?|P\.?\s*O\.?|Post\s*Office)\s*[:ঃ=\-]\s*([^,;|]+)',normalized,re.I):
                text=m.group(0)
                if re.match(r'Vill',text,re.I):
                    extra=explicit_values(['Village: '+m.group(1).strip()])
                else:
                    extra=explicit_values(['Post Office: '+m.group(1).strip()])
                for key,value in extra.items():inputs.setdefault(key,value)
            wm=re.search(r'(?<![০-৯0-9])([০-৯0-9]{1,2})\s*(?:নং|no\.?)?\s*(?:ওয়ার্ড|ওয়াড|ward|word)',normalized,re.I)
            if wm:inputs.setdefault('ward',wm.group(1))
            hm=HOUSE_LABEL.match(normalized)
            if hm:
                value=hm.group(1).strip()
                # A one-line address often begins "বাড়ি: , গ্রাম: ...".
                # A later labeled field belongs to that field, never to the house.
                value=re.split(r'[,，،;|]\s*(?=(?:গ্রাম|মহল্লা|ডাক\s*ঘর|পোস্ট\s*অফিস|post\s*office|vill(?:age)?|ওয়ার্ড|ward|পৌরসভা|ইউনিয়ন|উপজেলা|জেলা)\s*[:ঃ：=\-])',value,maxsplit=1,flags=re.I)[0].strip(' \t,，،;|')
                if value and not re.fullmatch(r'\(?\s*(?:যদি\s*থাকে|if\s*any|n/?a|none)\s*\)?',value,re.I) and not re.match(r'^(?:vill|village|গ্রাম)\s*[:ঃ：=\-]',value,re.I):
                    lang='houseRoadBn' if re.search(r'[\u0980-\u09ff]',value) else 'houseRoadEn'
                    inputs.setdefault(lang,value)
        # An unlabeled English translation immediately following a Bengali
        # postal/village line belongs to that same locality.
        for j,line in enumerate(fragments[:-1]):
            next_line=fragments[j+1].strip()
            if not re.fullmatch(r'[A-Za-z][A-Za-z\s.\-]*',next_line):continue
            if re.match(r'^\s*(?:ডাক\s*ঘর|ডাকঘর|পোস্ট\s*অফিস|পোঃ?)\s*[:：ঃ=\-]?\s*.+',line):
                inputs.setdefault('postOfficeEn',next_line)
            elif re.match(r'^\s*(?:গ্রাম|মহল্লা)\s*[:：ঃ=\-]?\s*.+',line):
                inputs.setdefault('villageEn',next_line)
        if not inputs.get('postCode'):
            # Only postal evidence may supply a post code. An earlier bare
            # applicant DOB belongs to the person, never to this address.
            postal_lines=[line for line in segment if re.search(r'ডাক\s*ঘর|পোস্ট\s*কোড|post\s*office|post\s*code|\bP\.?O\.?\b',line,re.I)]
            codes={m.translate(DIGITS) for line in postal_lines for m in re.findall(r'(?<![০-৯0-9])[০-৯0-9]{4}(?![০-৯0-9])',line)}
            if len(codes)==1:inputs['postCode']=next(iter(codes))
        inputs['district']=district['nameBn']
        if not inputs.get('upazila'):
            matched={up['id']:up for up in district['upazilas'] for part in fragments
                if not same(part,district) and not re.match(r'^\s*(?:জেলা|district|বিভাগ|division)',part,re.I) and
                (same(part,up) or (ADDRESS_CUE.search(part) or len(part.split())>1) and
                 (phrase_in(part,up.get('nameBn')) or phrase_in(part,up.get('nameEn'))))}
            if len(matched)==1:inputs['upazila']=next(iter(matched.values()))['nameBn']
        if not inputs.get('union') and inputs.get('upazila'):
            matching_up=pick(district['upazilas'],inputs['upazila'])
            if matching_up:
                unions={un['id']:un for un in matching_up.get('unions') or [] for part in fragments if same(part,un)}
                if len(unions)==1:inputs['union']=next(iter(unions.values()))['nameBn']
        u,un,ward,warnings=select_branch(district,inputs)
        address={'country':'1','division':div['nameBn'],'district':district['nameBn']}
        if u:address['upazila']=u['nameBn'].strip()
        if un:address['union']=un['nameBn'].strip()
        if ward:address['ward']=ward_value(ward)
        for field in ('postOfficeBn','postOfficeEn','postCode','villageBn','villageEn','houseRoadBn','houseRoadEn'):
            if inputs.get(field):address[field]=inputs[field].strip(' .')
        sources={k:{'source':'input' if k in inputs and k not in ('division',) else 'geo'} for k in address}
        complete_locality_languages(address,sources)
        for field, default in DEFAULT_LOCALITY.items():
            if field not in address:
                address[field]=default
                sources[field]={'source':'default'}
        found.append({'id':f'{district["id"]}-{line_index}', 'districtId':district['id'],
                      'label':f'{district["nameBn"]} — {address.get("upazila", "উপজেলা নেই")}',
                      'address':address,'sources':sources,'warnings':[],'input': '\n'.join(segment)})
    merged=[]
    for candidate in found:
        if merged:
            prev=merged[-1]
            a,b=prev['address'],candidate['address']
            complementary=(prev['sources'].get('villageBn',{}).get('source')=='input' and
                           candidate['sources'].get('villageEn',{}).get('source')=='input') or (prev['sources'].get('villageEn',{}).get('source')=='input' and
                           candidate['sources'].get('villageBn',{}).get('source')=='input')
            conflicting=any(prev['sources'].get(k,{}).get('source')=='input' and
                            candidate['sources'].get(k,{}).get('source')=='input' and a.get(k)!=b.get(k)
                            for k in ('upazila','union','ward','villageBn','villageEn','postOfficeBn','postOfficeEn','postCode'))
            old_role,new_role=address_role(prev['input']),address_role(candidate['input'])
            distinct_roles=bool(old_role and new_role and old_role!=new_role)
            both_explicit_up=prev['sources'].get('upazila',{}).get('source')=='input' and candidate['sources'].get('upazila',{}).get('source')=='input'
            if prev['districtId']==candidate['districtId'] and not conflicting and not distinct_roles and (a.get('upazila')==b.get('upazila') or not both_explicit_up):
                if candidate['sources'].get('upazila',{}).get('source')=='input' and prev['sources'].get('upazila',{}).get('source')!='input':
                    for field in ('upazila','union','ward'):
                        if field in b:
                            a[field]=b[field]
                            prev['sources'][field]=candidate['sources'][field]
                for field,source in candidate['sources'].items():
                    if source['source']=='input':
                        a[field]=b[field]
                        prev['sources'][field]=source
                # A later source-language value must supersede an earlier generated spelling.
                for stem in ('postOffice', 'village'):
                    bn, en = stem+'Bn', stem+'En'
                    if prev['sources'].get(bn, {}).get('source') == 'input' and prev['sources'].get(en, {}).get('source') != 'input':
                        spelling = romanize_locality(a[bn])
                        if spelling:
                            a[en] = spelling
                            prev['sources'][en] = {'source':'transliteration','from':bn}
                complete_locality_languages(a,prev['sources'])
                prev['input']+='\n'+candidate['input']
                continue
        merged.append(candidate)
    return merged

def tree(district_id):
    matched=next(((div,d) for div,d in DISTRICTS if str(d['id'])==str(district_id)),None)
    if not matched:return None
    div,d=matched
    return {'district':d['nameBn'],'division':div['nameBn'],'districtId':d['id'],
            'upazilas':[{'id':up['id'],'name':up['nameBn'].strip(),
               'unions':[{'id':un['id'],'name':un['nameBn'].strip(),
                          'wards':[{'id':w['id'],'number':ward_value(w),'name':w['nameBn']}
                                   for w in un.get('wards') or [] if ward_value(w)]}
                         for un in up.get('unions') or []]}
               for up in d.get('upazilas') or []]}
