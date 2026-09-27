"""Source anchored, section aware extraction for WhatsApp birth registration text."""
import re
from datetime import datetime
from address_geo import geo_name_line

BENGALI = re.compile(r'[\u0980-\u09ff]')
ENGLISH = re.compile(r'[A-Za-z]')
DIGITS = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
DATE_RE = re.compile(r'(?<!\d)([০-৯0-9]{1,2})\s*[-/.]\s*([০-৯0-9]{1,2})\s*[-/.]\s*([০-৯0-9]{4})(?!\d)')
MISSING_SEPARATOR_DATE = re.compile(r'(?<!\d)([০-৯0-9]{1,2})\s*[/.-]\s*([০-৯0-9]{2})([০-৯0-9]{4})(?!\d)')
MONTHS = {'জানুয়ারি':1,'জানুয়ারি':1,'ফেব্রুয়ারি':2,'ফেব্রুয়ারি':2,'মার্চ':3,'এপ্রিল':4,'মে':5,'জুন':6,'জুলাই':7,'আগস্ট':8,'সেপ্টেম্বর':9,'অক্টোবর':10,'নভেম্বর':11,'ডিসেম্বর':12,'january':1,'jan':1,'february':2,'feb':2,'march':3,'mar':3,'april':4,'apr':4,'apri':4,'may':5,'june':6,'jun':6,'july':7,'jul':7,'august':8,'aug':8,'september':9,'sep':9,'october':10,'oct':10,'november':11,'nov':11,'december':12,'dec':12}
PARENT_MARK = re.compile(r'পিতার\s*তথ্য|পিতার\s*নাম|পিতা\s*[:ঃ]|বাবার\s*নাম|father(?:[\x27’]s)?\s*(?:information|name)?\s*[:：ঃ-]|মাতার\s*তথ্য|মাতার\s*নাম|মাতা\s*[:ঃ]|মায়ের\s*নাম|mother(?:[\x27’]s)?\s*(?:information|name)?\s*[:：ঃ-]',re.I)
ADDRESS_MARK = re.compile(r'ঠিকানা|জন্ম\s*স্থান|জন্মস্থান|গ্রাম|ডাকঘর|পোস্ট|post\s*office|village|division|district|উপজেলা|ইউনিয়ন|ইউনিয়ন|ওয়ার্ড|ওয়াড|বিভাগ|জেলা|birth\s*place|address',re.I)
META_MARK = re.compile(r'NID|BRN|আইডি|কার্ড|নম্বর|নাম্বার|mobile|মোবাইল|জাতীয়তা|জাতীয়তা|nationality|সন্তান|gender|লিঙ্গ|date|জন্ম\s*তারিখ',re.I)
NAME_LABEL = re.compile(r'\bname\b|নাম|ইংরেজি|ইংরেজী|ইংরেজ|বাংলা|বাংলায়|বাংলায়|english',re.I)
FATHER = re.compile(r'পিতা|বাবা|father',re.I)
MOTHER = re.compile(r'মাতা|মায়ের|মায়ের|(?<![\u0980-\u09ff])মা(?![\u0980-\u09ff])|mother',re.I)
SEPARATORS = re.compile(r'^\s*[:：ঃ=\-–—.\s]+')


def clean(value):
    value=re.sub(r'\s+', ' ', str(value or '')).strip(' \t\n\r\u200b\ufeff')
    return re.sub(r'^(?:(?:value|val|ভ্যালু|ভেলু)(?:\s*[:ঃ：=\-]\s*|\s+))+(?=\S)', '', value, flags=re.I)


def split_bilingual(value):
    value = clean(value)
    if not value: return '', ''
    # Preserve original spelling; only strip wrappers and a final sentence mark.
    bn = re.search(r'[\u0980-\u09ff][\u0980-\u09ff\s:ঃ.\x27’\-]*', value)
    en = re.search(r'[A-Za-z][A-Za-z\s.\x27’\-]*', value)
    return (clean(bn.group()).strip(' .\x27’()') if bn else '',
            clean(en.group()).strip(' .\x27’()') if en else '')


def label_value(line):
    line = re.sub(r'^[★♦💠●▪•*\s]+', '', line).strip()
    line = re.sub(r'^(?:(?:value|val|ভ্যালু|ভেলু)(?:\s*[:ঃ：=\-]\s*|\s+))+(?=\S)', '', line, flags=re.I)
    bare_with_value = re.match(r'^((?:(?:পিতার|মাতার|বাবার)\s*)?নাম\s*(?:বাংলা|বাংলায়|বাংলায়|ইংরেজি|ইংরেজী|english|bangla))\s+(.+)$',line,re.I)
    if bare_with_value:return clean(bare_with_value.group(1)),clean(bare_with_value.group(2))
    compact=re.match(r'^(নাম\s*\((?:বাংলায়|বাংলায়|বাংলা|ইংরেজি|ইংরেজী|English|Bangla)\))\s*[:：ঃ=-]?\s*(.+)$',line,re.I)
    if compact:return clean(compact.group(1)),clean(compact.group(2))
    # Explicit short parent labels, including 'Father:-', 'পিতা:' and 'মাতা-'.
    parent=re.match(r"^((?:পিতার|মাতার|বাবার)(?:\s*নাম)?|(?:পিতা|মাতা|বাবা|মা|father|mother)(?:s)?)\s*[:：ঃ,=\-–—]+\s*(.*)$",line,re.I)
    if parent:return clean(parent.group(1)),clean(parent.group(2))
    # Split at label punctuation, including decorated '--:' labels.
    match = re.match(r'^(.{1,85}?)(?:\s*[:：ঃ=,]+|\s*[-–—]+\s*[:：ঃ=]*)(.*)$', line)
    if match and NAME_LABEL.search(match.group(1)):
        label=clean(match.group(1)); value=clean(SEPARATORS.sub('',match.group(2)))
        if re.search(r'^নাম\s*$',label,re.I) and re.match(r'^(?:বাংলা|বাংলায়|বাংলায়|ইংরেজ|ইংরেজী|ইংরেজি)\s*[:：ঃ]',value,re.I):
            inner=re.match(r'^(.+?)\s*[:：ঃ]+\s*(.*)$',value)
            label+=' '+inner.group(1);value=clean(inner.group(2))
        return label,value
    # Bare section headings and labels without punctuation.
    if NAME_LABEL.search(line) and len(line)<65: return line,''
    return '', ''


def is_name_label(label):
    if not NAME_LABEL.search(label) and not re.fullmatch(r'(?:পিতার|মাতার|বাবার|পিতা|মাতা|বাবা|মা|father|mother)s?',label,re.I):return False
    if re.search(r'চেঞ্জ|সংশোধন|পরিবর্তন|change|correct',label,re.I):return False
    if ADDRESS_MARK.search(label) or META_MARK.search(label) or re.search(r'পিতার\s*জন্ম|মাতার\s*জন্ম',label,re.I):return False
    return True


def language_hint(label):
    if re.search(r'বাংলা|বাংলায়|বাংলায়',label,re.I):return 'bn'
    if re.search(r'ইংরেজ|english|\bname\b',label,re.I):return 'en'
    return ''

def sequential_names(lines):
    """Read strictly ordered, unlabeled person/father/mother value groups."""
    groups=[];dates=[]
    for index,source in enumerate(lines):
        line=clean(source.strip('★♦💠●▪•* '))
        if not line:continue
        if DATE_RE.fullmatch(line):
            hit=DATE_RE.fullmatch(line)
            day,month,year=[int(x.translate(DIGITS)) for x in hit.groups()]
            try:datetime(year,month,day);dates.append((index,f'{day:02d}/{month:02d}/{year:04d}'))
            except ValueError:pass
            continue
        if geo_name_line(line) or ADDRESS_MARK.search(line) or META_MARK.search(line) or PARENT_MARK.search(line):continue
        if re.search(r'\d|https?://|@|\b(?:otp|nid|brn|office|application)\b',line,re.I):continue
        label,_=label_value(line)
        if label:continue
        bn,en=split_bilingual(line)
        if not bn and not en:continue
        if len(line)>95 or (bn and len(bn.split())>6) or (en and len(en.split())>6):continue
        if groups and all(not lines[j].strip() for j in range(groups[-1]['last']+1,index)) and ((bn and not groups[-1]['bn'] and groups[-1]['en']) or
            (en and not groups[-1]['en'] and groups[-1]['bn'])):
            if bn:groups[-1]['bn']=bn
            if en:groups[-1]['en']=en
            groups[-1]['last']=index
        else:groups.append({'bn':bn,'en':en,'first':index,'last':index})
    if not groups or groups[0]['first']>5 or (len(groups)<2 and not dates):return [],''
    if len(groups)>3: return [],''
    person_date=next((date for index,date in dates if groups[0]['last']<index and
                     (len(groups)<2 or index<groups[1]['first'])), '')
    return groups,person_date


def extract(raw):
    raw=re.sub(r'[\u200b\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]','',raw)
    names={r:{'bn':'','en':''} for r in ('person','father','mother')}
    evidence={r:{'bn':False,'en':False} for r in names}
    dates=[];genders=[]
    role='person'; lines=raw.splitlines()
    for i,source in enumerate(lines):
        line=source.strip()
        if not line:continue
        line=re.sub(r'^[★♦💠●▪•*\s]+','',line).strip()
        # A bare parent heading is a section boundary, not an unlabeled name.
        if re.fullmatch(r'(?:পিতা|বাবা|father)',line,re.I):role='father';continue
        if re.fullmatch(r'(?:মাতা|মা|mother)',line,re.I):role='mother';continue
        # A heading changes the role until another section starts.
        if re.search(r'পিতার\s*তথ্য|father(?:[\x27’]s)?\s*information',line,re.I):role='father';continue
        if re.search(r'মাতার\s*তথ্য|mother(?:[\x27’]s)?\s*information',line,re.I):role='mother';continue
        if re.search(r'নতুন\s*নিবন্ধনের\s*তথ্য|ব্যক্তিগত\s*তথ্য|নিজের\s*তথ্য|personal\s*information',line,re.I):role='person';continue
        label,value=label_value(line)
        active='father' if FATHER.search(label) else 'mother' if MOTHER.search(label) else role
        # Parent name on one line changes context, preventing a following English line from being assigned to person.
        # After an address block, another generic `Name:` often starts an English
        # restatement of the applicant, not another mother-name field.
        if active!='person' and label and re.fullmatch(r'name',label,re.I) and not names['person']['en'] and ADDRESS_MARK.search('\n'.join(lines[max(0,i-5):i])):
            active='person'; role='person'
        if label and is_name_label(label) and active!='person':role=active
        if label and is_name_label(label):
            if not value and i+1<len(lines):
                nextline=lines[i+1].strip()
                if nextline and not label_value(nextline)[0] and not ADDRESS_MARK.search(nextline) and not META_MARK.search(nextline):value=nextline
            bn,en=split_bilingual(value)
            hint=language_hint(label)
            if bn and not names[active]['bn']:
                names[active]['bn']=bn;evidence[active]['bn']=True
            if en and not names[active]['en']:
                names[active]['en']=en;evidence[active]['en']=True
            # Generic next line after parent's Bengali name may hold the English spelling.
            if active!='person' and not names[active]['en'] and i+1<len(lines):
                nextline=clean(lines[i+1]); nbn,nen=split_bilingual(nextline)
                if nen and not nbn and not label_value(nextline)[0] and not ADDRESS_MARK.search(nextline) and not META_MARK.search(nextline):
                    names[active]['en']=nen;evidence[active]['en']=True
        elif (not label and not DATE_RE.search(line) and not META_MARK.search(line)
              and not ADDRESS_MARK.search(line) and not geo_name_line(line)
              and not re.search(r'\d|https?://|@|[,،।]',line)
              and len(line)<=90 and (role!='person' or i<5)):
            # A bilingual name may be written on two plain lines. Only assign
            # it within its explicit parent section or at the start of text.
            bn,en=split_bilingual(line)
            if bn and not en and len(bn.split())<=6 and not names[role]['bn']:
                names[role]['bn']=bn;evidence[role]['bn']=True
            if en and not bn and len(en.split())<=6 and not names[role]['en']:
                names[role]['en']=en;evidence[role]['en']=True
        elif not label and role in names and not META_MARK.search(line) and not ADDRESS_MARK.search(line):
            # Unlabeled English line is accepted only directly after a labeled name.
            if i and is_name_label(label_value(lines[i-1].strip())[0]):
                bn,en=split_bilingual(line)
                if en and not bn and not names[role]['en']:names[role]['en']=en
        # A standalone date immediately after the applicant's labeled name and
        # its optional English continuation is the applicant's DOB. Never use
        # a date inside a father/mother section or a line with another label.
        standalone_date = bool(DATE_RE.fullmatch(line))
        previous = next((lines[j].strip() for j in range(i-1,-1,-1) if lines[j].strip()), '')
        applicant_name_nearby = bool(
            names['person']['bn'] or names['person']['en']) and bool(previous) and not (
                ADDRESS_MARK.search(previous) or META_MARK.search(previous) or PARENT_MARK.search(previous)) and any(
                is_name_label(label_value(lines[j].strip())[0]) and
                not PARENT_MARK.search(lines[j])
                for j in range(max(0,i-3),i))
        if standalone_date and role=='person' and i<8 and (names['person']['bn'] or names['person']['en']):
            applicant_name_nearby=True
        if (re.search(r'জন্ম\s*তারিখ|(?:^|\s)জন্ম\s*[:ঃ]|date\s*of\s*birth|\bdob\b|\bbirth\s*[:ঃ]|^(?:বয়স|বয়স|age)\s*[:ঃ：-]\s*[০-৯0-9]{1,2}\s*[-/.]',line,re.I)
                or (standalone_date and role=='person' and applicant_name_nearby)):
            if active=='person' and not FATHER.search(line) and not MOTHER.search(line):
                date_line=line
                if not DATE_RE.search(date_line) and i+1<len(lines) and not label_value(lines[i+1].strip())[0]:date_line+=' '+lines[i+1].strip()
                hit=DATE_RE.search(date_line)
                malformed=MISSING_SEPARATOR_DATE.search(date_line) if not hit else None
                parts=[int(s.translate(DIGITS)) for s in (hit or malformed).groups()] if (hit or malformed) else None
                if not parts:
                    word_date=re.search(r'([০-৯0-9]{1,2})\s*([A-Za-z\u0980-\u09ff]+)\s+([০-৯0-9]{4})',line)
                    if word_date and word_date.group(2).casefold() in MONTHS:
                        parts=[int(word_date.group(1).translate(DIGITS)),MONTHS[word_date.group(2).casefold()],int(word_date.group(3).translate(DIGITS))]
                if parts:
                    d,m,y=parts
                    try:datetime(y,m,d);dates.append(f'{d:02d}/{m:02d}/{y:04d}')
                    except ValueError:pass
        if re.search(r'লিঙ্গ|লিং|gender|\bsex\b',line,re.I) and not (FATHER.search(line) or MOTHER.search(line)):
            gender_line=line
            if not re.search(r'মহিলা|মেয়ে|মেয়ে|নারী|পুরুষ|ছেলে|\b(?:female|male)\b',line,re.I) and i+1<len(lines) and len(lines[i+1].strip())<20:
                gender_line+=' '+lines[i+1]
            female=re.search(r'মহিলা|মেয়ে|মেয়ে|নারী|\bfemale\b',gender_line,re.I)
            male=re.search(r'পুরুষ|ছেলে|\bmale\b',gender_line,re.I)
            if bool(female)!=bool(male):genders.append('FEMALE' if female else 'MALE')
    # Two unlabeled name lines followed closely by a DOB are common in office messages.
    # Only use source strings; do not infer the other language from a name.
    if not names['person']['bn'] or not names['person']['en']:
        head=[clean(x) for x in lines[:5] if clean(x)]
        if any(re.search(r'\bdob\b|জন্ম\s*তারিখ',x,re.I) for x in head):
            candidates=[]
            for x in head:
                if DATE_RE.search(x) or META_MARK.search(x) or ADDRESS_MARK.search(x) or label_value(x)[0]:continue
                if len(x)>90 or re.search(r'\d|আবেদন|office|application',x,re.I):continue
                candidates.append(x)
            for x in candidates[:2]:
                bn,en=split_bilingual(x)
                if bn and not en and not names['person']['bn']:names['person']['bn']=bn
                if en and not bn and not names['person']['en']:names['person']['en']=en
    if not any(names[r][lang] for r in names for lang in ('bn','en')):
        groups,person_date=sequential_names(lines)
        for role,group in zip(('person','father','mother'),groups):
            for lang in ('bn','en'):
                if group[lang]:names[role][lang]=group[lang]
        if person_date and not dates:dates.append(person_date)
    elif (names['person']['bn'] or names['person']['en']) and not any(
            names[r][lang] for r in ('father','mother') for lang in ('bn','en')):
        groups,person_date=sequential_names(lines)
        unmatched=[group for group in groups if not any(
            group[lang] and group[lang]==names['person'][lang] for lang in ('bn','en'))]
        if len(unmatched)==2:
            for role,group in zip(('father','mother'),unmatched):
                for lang in ('bn','en'):
                    if group[lang]:names[role][lang]=group[lang]
        if person_date and not dates:dates.append(person_date)
    result={'person':{'nameBn':names['person']['bn'],'nameEn':names['person']['en'],'birthDate':dates[0] if len(set(dates))==1 else '', 'gender':genders[0] if len(set(genders))==1 else ''},
            'father':{'nameBn':names['father']['bn'],'nameEn':names['father']['en']},'mother':{'nameBn':names['mother']['bn'],'nameEn':names['mother']['en']}}
    # The model should run when there are signals of names we failed to assign.
    missing=[]
    for r in names:
        for lang in ('bn','en'):
            if result[r]['name'+lang.title()]:continue
            expected=(r=='person' or bool(re.search(r'পিতা|বাবা|father' if r=='father' else r'মাতা|mother',raw,re.I)))
            if expected:missing.append(r+'.name'+lang.title())
    if not result['person']['birthDate'] and re.search(r'জন্ম\s*তারিখ|জন্ম\s*[:ঃ]|date\s*of\s*birth|\bdob\b|\bbirth\s*[:ঃ]',raw,re.I):missing.append('person.birthDate')
    if not result['person']['gender'] and re.search(r'লিঙ্গ|gender|মহিলা|পুরুষ|\bfemale\b|\bmale\b',raw,re.I):missing.append('person.gender')
    return result,missing
