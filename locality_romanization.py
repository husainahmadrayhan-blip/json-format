"""Offline Bengali place-name romanization; generated spellings need human review."""
import re
import unicodedata
from address_geo import GEO, DIGITS, norm

SPECIAL = {
    norm(bn): en for bn, en in {
        'চন্দ্র নগর': 'Chondon Nogor', 'চন্দ্রনগর': 'Chondon Nogor',
        'সাতকাপন': 'Satkapon', 'হেমায়েতপুর': 'Hemayetpur',
        'হেসামদ্দি': 'Hesamoddi', 'পাশাপোল': 'Pashapol',
        'পলুয়া': 'Polua', 'কাশিপুর': 'Kashipur',
    }.items()
}

# Prefer bilingual spelling in the supplied Geo data when the Bengali name is unique.
def _geo_spellings():
    names = {}
    for div in GEO['divisions']:
        for district in div['districts']:
            for item in (div, district):
                if item.get('nameBn') and item.get('nameEn'):
                    names.setdefault(norm(item['nameBn']), set()).add(item['nameEn'].strip())
            for up in district.get('upazilas', []):
                for item in [up, *up.get('unions', [])]:
                    if item.get('nameBn') and item.get('nameEn'):
                        names.setdefault(norm(item['nameBn']), set()).add(item['nameEn'].strip())
    return {key: next(iter(value)) for key, value in names.items() if len(value) == 1}

GEO_SPELLINGS = _geo_spellings()
VOWELS = dict(zip('অআইঈউঊঋএঐওঔ', ('o','a','i','i','u','u','ri','e','oi','o','ou')))
SIGNS = {'া':'a','ি':'i','ী':'i','ু':'u','ূ':'u','ৃ':'ri','ে':'e','ৈ':'oi','ো':'o','ৌ':'ou'}
CONSONANTS = {'ক':'k','খ':'kh','গ':'g','ঘ':'gh','ঙ':'ng','চ':'ch','ছ':'chh','জ':'j','ঝ':'jh','ঞ':'n','ট':'t','ঠ':'th','ড':'d','ঢ':'dh','ণ':'n','ত':'t','থ':'th','দ':'d','ধ':'dh','ন':'n','প':'p','ফ':'ph','ব':'b','ভ':'bh','ম':'m','য':'j','য়':'y','র':'r','ল':'l','শ':'sh','ষ':'sh','স':'s','হ':'h','ড়':'r','ঢ়':'rh','ৎ':'t'}
EXTRAS = {'ং':'ng','ঁ':'n','ঃ':'h'}
TOKEN = re.compile(r'[\u0980-\u09ff]+|[A-Za-z]+|[০-৯0-9]+|[^\u0980-\u09ffA-Za-z০-৯0-9]+')

def _word(word):
    output = []
    # Bengali য় is often encoded as য + nukta; handle both the same way.
    chars = list(word.replace('\u09af\u09bc','য়').replace('\u09a1\u09bc','ড়').replace('\u09a2\u09bc','ঢ়'))
    for index, char in enumerate(chars):
        following = chars[index + 1] if index + 1 < len(chars) else ''
        if char in CONSONANTS:
            # Final unmarked vowel and conjunct handling is necessarily approximate.
            vowel = '' if following == '্' or index == len(chars) - 1 else 'o' if following not in SIGNS else ''
            output.append(CONSONANTS[char] + vowel)
        elif char in SIGNS: output.append(SIGNS[char])
        elif char == '্': continue
        elif char in VOWELS: output.append(VOWELS[char])
        elif char in EXTRAS: output.append(EXTRAS[char])
        else: output.append(char.translate(DIGITS))
    return ''.join(output).capitalize()

def romanize_locality(value):
    text = unicodedata.normalize('NFC', str(value or '')).strip()
    if not re.search(r'[\u0980-\u09ff]', text): return ''
    key = norm(text)
    if key in SPECIAL: return SPECIAL[key]
    if key in GEO_SPELLINGS: return GEO_SPELLINGS[key]
    pieces = []
    for token in TOKEN.findall(text):
        token_key = norm(token)
        pieces.append(SPECIAL.get(token_key) or GEO_SPELLINGS.get(token_key) or
                      (_word(token) if re.search(r'[\u0980-\u09ff]', token) and not token.isdigit() else token.translate(DIGITS)))
    return ''.join(pieces).strip()
