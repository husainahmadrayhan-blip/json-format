const norm=value=>String(value??'').toLocaleLowerCase().replace(/[০-৯]/g,d=>'০১২৩৪৫৬৭৮৯'.indexOf(d)).replace(/[^\p{L}\p{N}]/gu,'');

// This only creates a reading view. The pasted text and JSON stay untouched.
export function splitSourceGroups(raw,data){
  const groups={person:[],father:[],mother:[],other:[]};
  let nextName=null;
  for(const line of String(raw||'').split(/\r?\n/)){
    if(!line.trim()){if(nextName)groups[nextName].push(line);else groups.other.push(line);continue;}
    const father=/(?:পিতার?|বাবার?|father['’]?s?|paternal)/i.test(line);
    const mother=/(?:মাতার?|মায়ের?|মায়ের?|mother['’]?s?|maternal)/i.test(line);
    let role=father?'father':mother?'mother':null;
    if(role){nextName=/(?:নাম|\bname\b)/i.test(line)?role:null;}
    else{
      const genericName=/^\s*(?:name|english name|নাম)\s*[:：]/i.test(line);
      const personNames=[data?.person?.nameBn,data?.person?.nameEn,
        [data?.person?.firstNameBn,data?.person?.lastNameBn].filter(Boolean).join(' '),
        [data?.person?.firstNameEn,data?.person?.lastNameEn].filter(Boolean).join(' ')];
      const applicantMatch=genericName&&personNames.some(v=>norm(v).length>=5&&norm(line).includes(norm(v)));
      if(applicantMatch)role='person';
      else if(genericName&&nextName)role=nextName;
      nextName=null;
      if(!role){
        const target=norm(line);
        for(const candidate of ['father','mother']){
          const values=[data?.[candidate]?.nameBn,data?.[candidate]?.nameEn,data?.[candidate]?.brn,data?.[candidate]?.birthDate,data?.[candidate]?.nid];
          if(values.some(v=>norm(v).length>=5&&target.includes(norm(v)))){role=candidate;break;}
        }
      }
      if(!role&&/(?:নাম|\bname\b|জন্ম\s*তারিখ|date\s*of\s*birth|birth\s*date|\bdob\b|লিঙ্গ|gender|sex|সন্তান\s*ক্রম|child\s*order|\bnid\b)/i.test(line))role='person';
    }
    groups[role||'other'].push(line);
  }
  return groups;
}
