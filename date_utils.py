"""Source-only birth date recognition shared by applicant and parent parsers."""
import re
from datetime import datetime

DIGITS = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
MONTHS = {
    'jan':1,'january':1,'জানুয়ারি':1,'জানুয়ারি':1,
    'feb':2,'february':2,'ফেব্রুয়ারি':2,'ফেব্রুয়ারি':2,
    'mar':3,'march':3,'মার্চ':3,'apr':4,'april':4,'এপ্রিল':4,
    'may':5,'মে':5,'jun':6,'june':6,'জুন':6,'jul':7,'july':7,'জুলাই':7,
    'aug':8,'august':8,'আগস্ট':8,'sep':9,'sept':9,'september':9,'সেপ্টেম্বর':9,
    'oct':10,'october':10,'অক্টোবর':10,'nov':11,'november':11,'নভেম্বর':11,
    'dec':12,'december':12,'ডিসেম্বর':12,
}
NUMERIC = re.compile(r'(?<![০-৯0-9])(?:[০-৯0-9]{4}\s*[-/.]\s*[০-৯0-9]{1,2}\s*[-/.]\s*[০-৯0-9]{1,2}|[০-৯0-9]{1,2}\s*[-/.]\s*[০-৯0-9]{1,2}\s*[-/.]\s*[০-৯0-9]{4})(?![০-৯0-9])')
WORDS = re.compile(r'(?<![০-৯0-9])([০-৯0-9]{1,2})\s+([A-Za-z\u0980-\u09ff]+)\s+([০-৯0-9]{4})(?![০-৯0-9])', re.I)

def normalize_date(value):
    raw = str(value or '').translate(DIGITS)
    match = NUMERIC.search(raw)
    if match:
        parts = [int(x) for x in re.split(r'\s*[-/.]\s*', match.group())]
        year,month,day = parts if parts[0]>=1000 else (parts[2],parts[1],parts[0])
    else:
        word = WORDS.search(raw)
        if not word:return ''
        day,month,year = int(word.group(1)), MONTHS.get(word.group(2).casefold()), int(word.group(3))
        if not month:return ''
    try:datetime(year,month,day)
    except ValueError:return ''
    return f'{day:02d}/{month:02d}/{year:04d}'

def date_matches(value):
    raw = str(value or '')
    matches = [(m.start(),m.group()) for m in NUMERIC.finditer(raw)]
    matches += [(m.start(),m.group()) for m in WORDS.finditer(raw) if m.group(2).casefold() in MONTHS]
    return [(pos,text,normalize_date(text)) for pos,text in sorted(matches) if normalize_date(text)]
