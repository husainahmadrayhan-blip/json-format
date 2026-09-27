"""Best-effort offline English place-name transcription, with Geo names preferred."""
import re
from address_geo import GEO
from locality_romanization import SPECIAL

BN_DIGITS = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')

def known_names():
    found={}
    for division in GEO['divisions']:
        for district in division['districts']:
            for entry in (division,district):
                if entry.get('nameEn') and entry.get('nameBn'):
                    found.setdefault(entry['nameEn'].strip().casefold(),set()).add(entry['nameBn'].strip())
            for up in district.get('upazilas',[]):
                for entry in (up,*up.get('unions',[])):
                    if entry.get('nameEn') and entry.get('nameBn'):
                        found.setdefault(entry['nameEn'].strip().casefold(),set()).add(entry['nameBn'].strip())
    for bn,en in SPECIAL.items():found.setdefault(en.casefold(),set()).add(bn)
    return {en:next(iter(bns)) for en,bns in found.items() if len(bns)==1}

KNOWN=known_names()
KNOWN.update({'chondon nogor':'চন্দ্র নগর','satkapon':'সাতকাপন'})
CONSONANTS={'chh':'ছ','ch':'চ','kh':'খ','gh':'ঘ','th':'থ','dh':'ধ','ph':'ফ','bh':'ভ','sh':'শ',
            'ng':'ং','ny':'ন্য','k':'ক','g':'গ','j':'জ','t':'ত','d':'দ','n':'ন','p':'প',
            'f':'ফ','b':'ব','m':'ম','r':'র','l':'ল','s':'স','h':'হ','y':'য়','w':'ও','v':'ভ','z':'জ','q':'ক','x':'ক্স','c':'ক'}
VOWELS={'aa':'া','ee':'ী','ii':'ী','oo':'ু','ou':'ৌ','oi':'ৈ','ai':'ৈ',
        'a':'া','i':'ি','e':'ে','o':'ো','u':'ু'}
INITIAL={'a':'আ','e':'এ','i':'ই','o':'ও','u':'উ'}

def word_to_bn(word):
    if word.casefold() in KNOWN:return KNOWN[word.casefold()]
    word=word.casefold();out='';i=0; previous_consonant=False
    while i<len(word):
        token=next((part for part in sorted(CONSONANTS,key=len,reverse=True) if word.startswith(part,i)),None)
        if token:
            if previous_consonant:out+='্'
            out+=CONSONANTS[token];previous_consonant=True;i+=len(token);continue
        vowel=next((part for part in sorted(VOWELS,key=len,reverse=True) if word.startswith(part,i)),None)
        if vowel:
            if previous_consonant:out+=VOWELS[vowel]
            else:out+=INITIAL.get(vowel[0],'আ')
            previous_consonant=False;i+=len(vowel);continue
        i+=1
    return out

def bengalize_locality(value):
    value=str(value or '').strip()
    if not re.search(r'[A-Za-z]',value):return ''
    pieces=[]
    for match in re.finditer(r'[A-Za-z]+|[0-9]+|[^A-Za-z0-9]+',value):
        token=match.group();pieces.append(word_to_bn(token) if token.isascii() and token.isalpha() else token.translate(BN_DIGITS))
    # Use authoritative spelling for exact multiword place names.
    m=re.fullmatch(r'\s*([A-Za-z][A-Za-z ]*?)(\s*[-–]\s*[0-9]+)?\s*',value)
    if m and m.group(1).strip().casefold() in KNOWN:
        return KNOWN[m.group(1).strip().casefold()]+(m.group(2) or '').translate(BN_DIGITS)
    return ''.join(pieces).strip()
