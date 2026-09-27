"""Offline regression checks for address extraction; no external packages."""
from address_choices import candidates
from server import blank,parse_result

cases = [
    ('single district', 'জন্মস্থান : চট্টগ্রাম', {'district':'চট্টগ্রাম','postOfficeBn':'চন্দ্র নগর','villageBn':'সাতকাপন'}),
    ('inline English', 'Village: Choyom Tatka, Hesamoddi-8270, Mehendiganj, Barishal',
     {'district':'বরিশাল','upazila':'মেহেন্দীগঞ্জ','villageEn':'Choyom Tatka','postOfficeEn':'Hesamoddi-8270','postCode':'8270'}),
    ('decorated labels', '★গ্রামঃ পলুয়া\n★Village: Polua\n★ডাকঘর: পাশাপোল\n★Postoffice: Pashapol\nজেলা: যশোর',
     {'villageBn':'পলুয়া','villageEn':'Polua','postOfficeBn':'পাশাপোল','postOfficeEn':'Pashapol'}),
    ('embedded labels', 'গ্রাম-মাদ্রাসা রোড, যাদুরচর, পোস্ট অফিস-হেমায়েতপুর, থানা-সাভার, জেলা-ঢাকা',
     {'district':'ঢাকা','postOfficeBn':'হেমায়েতপুর','villageBn':'মাদ্রাসা রোড, যাদুরচর'}),
    ('ordered locality', 'ঠিকানা\nজেলা: খুলনা\nওয়ার্ড: ১\nচন্দ্রনগর\nChondon Nogor\nসাতকাপন\nSatkapon',
     {'postOfficeBn':'চন্দ্রনগর','postOfficeEn':'Chondon Nogor','villageBn':'সাতকাপন','villageEn':'Satkapon'}),
    ('house and post', 'বাসা/হোল্ডিং: জমাদারহাট হোসেন মঞ্জিল, পশ্চিম গোমদন্ডী\nডাকঘর: পশ্চিম গোমদন্ডী-৪৩৬৬\nজেলা: চট্টগ্রাম',
     {'houseRoadBn':'জমাদারহাট হোসেন মঞ্জিল, পশ্চিম গোমদন্ডী','postCode':'4366'}),
    ('Unicode district', 'জেলাঃ নোয়াখালী\nউপজেলা: সেনবাগ\nগ্রাম: উত্তর জয়নগর',
     {'district':'নোয়াখালী','upazila':'সেনবাগ','villageBn':'উত্তর জয়নগর'}),
]
for label,raw,expected in cases:
    choices=candidates(raw)
    assert len(choices)==1,(label,choices)
    data=choices[0]['address']
    for field,want in expected.items():
        assert data.get(field)==want,(label,field,data.get(field),want)
    result=parse_result(raw,blank(),[],'rules',[])
    assert result['data']['birthPlace']==data,label

multiple=candidates('জেলা: বরিশাল\nউপজেলা: বাবুগঞ্জ\nঠিকানা ২\nজেলা: খুলনা\nউপজেলা: বাটিয়াঘাটা')
assert [x['address']['district'] for x in multiple]==['বরিশাল','খুলনা']
assert not candidates('নাম: ঢাকা\nউপজেলা: কিশোরগঞ্জ সদর')
assert len(candidates('জেলা: নীলফামারী\nউপজেলা: কিশোরগঞ্জ সদর'))==1
translated = candidates('জেলা: ঢাকা\nডাকঘর: হেমায়েতপুর\nগ্রাম: কাশিপুর')[0]
assert translated['address']['postOfficeBn'] == 'হেমায়েতপুর'
assert translated['address']['postOfficeEn'] == 'Hemayetpur'
assert translated['address']['villageBn'] == 'কাশিপুর'
assert translated['address']['villageEn'] == 'Kashipur'
assert translated['sources']['postOfficeEn']['source'] == 'transliteration'
assert translated['sources']['villageEn']['source'] == 'transliteration'
assert candidates('জেলা: ঢাকা\nডাকঘর: হেসামদ্দি-৮২৭০')[0]['address']['postOfficeEn'] == 'Hesamoddi-8270'
explicit = candidates('জেলা: ঢাকা\nডাকঘর: হেমায়েতপুর\nPost Office: Official Place\nগ্রাম: কাশিপুর\nVillage: Official Village')[0]
assert explicit['address']['postOfficeEn'] == 'Official Place'
assert explicit['address']['villageEn'] == 'Official Village'
assert explicit['sources']['postOfficeEn']['source'] == 'input'
assert candidates('জন্মস্থান: ঢাকা')[0]['address']['postOfficeEn'] == 'Chondon Nogor'
english_only=candidates('জেলা: ঢাকা\nPost Office: Chondon Nogor - 1212\nVillage: Satkapon')[0]
assert english_only['address']['postOfficeBn']=='চন্দ্র নগর - ১২১২'
assert english_only['address']['postOfficeEn']=='Chondon Nogor - 1212'
assert english_only['address']['postCode']=='1212'
assert english_only['address']['villageBn']=='সাতকাপন'
assert english_only['sources']['postOfficeBn']['source']=='transliteration'
assert english_only['sources']['villageEn']['source']=='input'
bn_only=candidates('জেলা: ঢাকা\nডাকঘর: হেমায়েতপুর-১২১২\nগ্রাম: কাশিপুর')[0]['address']
assert bn_only['postOfficeEn']=='Hemayetpur-1212' and bn_only['postOfficeBn']=='হেমায়েতপুর-১২১২'
for locality in (english_only['address'],bn_only):
    assert all(not __import__('re').search('[A-Za-z]',locality[field]) for field in ('postOfficeBn','villageBn'))
    assert all(not __import__('re').search('[\u0980-\u09ff]',locality[field]) for field in ('postOfficeEn','villageEn'))
inline_house = ('জন্মস্থান: জয়পুরহাট\nবাড়ি: , গ্রামঃ রাধানগর (করতী), ডাকঘরঃ পাঁচবিবি-৫৯১০, '
                'ওয়ার্ড-০৬, পৌরসভাঃ পাঁচবিবি, উপজেলাঃ পাঁচবিবি, জেলাঃ জয়পুরহাট')
parsed = candidates(inline_house)[0]['address']
assert parsed['villageBn'] == 'রাধানগর (করতী)'
assert parsed['postOfficeBn'] == 'পাঁচবিবি-৫৯১০'
assert not parsed.get('houseRoadBn'), parsed
with_house = inline_house.replace('বাড়ি: ,', 'বাড়ি: ১২,')
assert candidates(with_house)[0]['address']['houseRoadBn'] == '১২'
print('Address verification passed:',len(cases)+9,'cases')
