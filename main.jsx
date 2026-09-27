import React,{useEffect,useMemo,useRef,useState} from 'react';
import{createRoot}from'react-dom/client';
import './style.css';
import officePresets from './office-presets.json';
import {assignOffice} from './office-logic.js';

const VERSION='v58-ascii-english-fields';
const GROUPS=[
 ['person','আবেদনকারী',[['firstNameBn','বাংলা প্রথম নাম'],['lastNameBn','বাংলা শেষ নাম'],['firstNameEn','English first name'],['lastNameEn','English last name'],['birthDate','জন্মতারিখ'],['childOrder','সন্তান ক্রম'],['gender','লিঙ্গ']]],
 ['father','পিতা',[['nameBn','বাংলা নাম'],['nameEn','English name'],['birthDate','জন্মতারিখ'],['nid','NID'],['brn','BRN'],['nationality','জাতীয়তা']]],
 ['mother','মাতা',[['nameBn','বাংলা নাম'],['nameEn','English name'],['birthDate','জন্মতারিখ'],['nid','NID'],['brn','BRN'],['nationality','জাতীয়তা']]],
];
const ADDRESSES=[['birthPlace','জন্মস্থান'],['permanentAddress','স্থায়ী ঠিকানা'],['presentAddress','বর্তমান ঠিকানা']];
const ADDRESS_FIELDS=[['country','দেশ'],['division','বিভাগ'],['district','জেলা'],['upazila','উপজেলা'],['union','ইউনিয়ন/এলাকা'],['area','অঞ্চল'],['ward','ওয়ার্ড'],['postOfficeBn','ডাকঘর বাংলা'],['postOfficeEn','Post office English'],['postCode','পোস্ট কোড'],['villageBn','গ্রাম বাংলা'],['villageEn','Village English'],['houseRoadBn','বাসা/বাড়ি বাংলা'],['houseRoadEn','House/Holding English']];
const get=(obj,path)=>path.split('.').reduce((v,k)=>v?.[k],obj)??'';
const EMPTY='মূল লেখায় নেই';
const normalizeBnName=value=>String(value??'').replace(/([\u0980-\u09ff])[ \t]*[:：]/g,'$1ঃ');
const cleanEnglish=value=>String(value??'').normalize('NFKD').replace(/[’‘]/g,"'").replace(/[–—−]/g,'-').replace(/[^\x20-\x7E]/g,'').trim();
function cleanEnglishFields(value){
 if(Array.isArray(value))return value.map(cleanEnglishFields);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,key.endsWith('En')&&typeof item==='string'?cleanEnglish(item):cleanEnglishFields(item)]));
 return value;
}
function normalizeNameFields(value){
 const next=cleanEnglishFields(structuredClone(value));
 for(const key of ['firstNameBn','lastNameBn'])if(typeof next.person?.[key]==='string')next.person[key]=normalizeBnName(next.person[key]);
 for(const role of ['father','mother'])if(typeof next[role]?.nameBn==='string')next[role].nameBn=normalizeBnName(next[role].nameBn);
 return next;
}
const OFFICE_STORE='bdris-react-office-addresses-v1';
const OFFICE_KEYS=['country','division','district','upazila','union','ward','area','postOfficeBn','postOfficeEn','postCode','villageBn','villageEn','houseRoadBn','houseRoadEn'];
function storedOffices(){try{const value=JSON.parse(localStorage.getItem(OFFICE_STORE)||'[]');return Array.isArray(value)?value.filter(x=>x&&typeof x.id==='string'&&typeof x.name==='string'&&x.address&&typeof x.address==='object'):[]}catch{return []}}

function App(){
 const[raw,setRaw]=useState('');const[models,setModels]=useState([]);const[model,setModel]=useState('');const[groqKey,setGroqKey]=useState('');const[geminiKey,setGeminiKey]=useState('');
 const[tree,setTree]=useState(null);const[selectedCandidate,setSelectedCandidate]=useState(null);const[server,setServer]=useState('সার্ভার পরীক্ষা হচ্ছে…');const[loading,setLoading]=useState(false);const[status,setStatus]=useState('');
 const[result,setResult]=useState(null);const[data,setData]=useState(null);const[edited,setEdited]=useState([]);const[approved,setApproved]=useState(false);const[error,setError]=useState('');
 const[customOffices,setCustomOffices]=useState(storedOffices);const[officeSources,setOfficeSources]=useState({});const[activeOffice,setActiveOffice]=useState('');const birthBeforeOffice=useRef(null);
 const[officeForm,setOfficeForm]=useState(false);const[officeName,setOfficeName]=useState('');const[officeJSON,setOfficeJSON]=useState('');const[officeError,setOfficeError]=useState('');
 const offices=[...officePresets,...customOffices];
 function applyOffices(chosen,mode){
  if(!data)return setOfficeError('আগে লেখা Parse করুন');
  const office=offices.find(item=>item.id===chosen.permanentAddress);
  if(!office)return setOfficeError('নির্বাচিত অফিস পাওয়া যায়নি');
  try{
   if(mode==='all'&&!selectedCandidate?.startsWith('office:'))birthBeforeOffice.current={address:structuredClone(data.birthPlace||{}),selected:selectedCandidate,tree};
   const restore=mode==='permanentPresent'&&selectedCandidate?.startsWith('office:')?birthBeforeOffice.current:null;
   const next=assignOffice(data,office,mode,restore?.address);
   const origin=role=>Object.fromEntries(Object.keys(next[role]||{}).map(key=>[key,{source:'office'}]));
   setData(cleanEnglishFields(next));
   setEdited(prev=>prev.filter(path=>!['permanentAddress','presentAddress',...(mode==='all'?['birthPlace']:[])].some(role=>path.startsWith(role+'.'))));
   setOfficeSources(prev=>({...prev,permanentAddress:origin('permanentAddress'),presentAddress:origin('presentAddress'),...(mode==='all'?{birthPlace:origin('birthPlace')}:restore?{birthPlace:null}:{})}));
   if(mode==='all'){setSelectedCandidate('office:'+office.id);setTree(null)}
   else if(restore){setSelectedCandidate(restore.selected||null);setTree(restore.tree||null)}
   setActiveOffice(office.id+':'+mode);setApproved(false);setOfficeError('');
   setStatus(mode==='all'?'অফিস ঠিকানা ৩টি ঘরেই বসেছে':'অফিস ঠিকানা স্থায়ী ও বর্তমান ঘরে বসেছে; জন্মস্থান অপরিবর্তিত');
  }catch(e){setOfficeError(e.message)}
 }
 function saveOffice(){
  try{
   const name=officeName.trim();if(!name)throw Error('অফিসের নাম লিখুন');
   const parsed=JSON.parse(officeJSON);
   if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))throw Error('ঠিকানা JSON object হতে হবে');
   const rawAddress=parsed.birthPlace||parsed.permanentAddress||parsed.address||parsed;
   if(!rawAddress||typeof rawAddress!=='object'||Array.isArray(rawAddress))throw Error('ঠিকানার object পাওয়া যায়নি');
   const address=Object.fromEntries(OFFICE_KEYS.filter(key=>typeof rawAddress[key]==='string'||typeof rawAddress[key]==='number').map(key=>[key,String(rawAddress[key])]));
   if(!address.district?.trim())throw Error('JSON-এ district দিতে হবে');
   const id='custom-'+Date.now()+'-'+Math.random().toString(36).slice(2);
   const present=parsed.presentAddress&&typeof parsed.presentAddress==='object'&&!Array.isArray(parsed.presentAddress)?parsed.presentAddress:null;
   const presentAddress=present?Object.fromEntries(OFFICE_KEYS.filter(key=>typeof present[key]==='string'||typeof present[key]==='number').map(key=>[key,String(present[key])])):null;
   if(presentAddress&&!presentAddress.district?.trim())throw Error('বর্তমান ঠিকানার JSON-এ district দিতে হবে');
   const next=[...customOffices,cleanEnglishFields({id,name,address,...(presentAddress?{presentAddress}:{})})];localStorage.setItem(OFFICE_STORE,JSON.stringify(next));setCustomOffices(next);
   setOfficeName('');setOfficeJSON('');setOfficeForm(false);setOfficeError('');setStatus(name+' অফিস ঠিকানা সংরক্ষিত হয়েছে');
  }catch(e){setOfficeError(e instanceof SyntaxError?'সঠিক JSON লিখুন':e.message)}
 }
 function deleteOffice(id){const next=customOffices.filter(item=>item.id!==id);localStorage.setItem(OFFICE_STORE,JSON.stringify(next));setCustomOffices(next);if(activeOffice.startsWith(id+':'))setActiveOffice('');setStatus('অফিস তালিকা থেকে সরানো হয়েছে')}
 async function check(){try{const r=await fetch('/api/version',{cache:'no-store'});const j=await r.json();if(j.version!==VERSION)throw Error(`অন্য সার্ভার চলছে (${j.version||'version নেই'})`);setServer('✅ '+VERSION+' চালু');return true}catch(e){setServer('⚠️ '+e.message);return false}}
 async function loadModels(){try{const r=await fetch('/api/models');const j=await r.json();if(!r.ok)throw Error(j.error||'Ollama পাওয়া যায়নি');setModels(j.models||[]);setModel(prev=>prev||(j.models?.[0]||''));setStatus((j.models||[]).length?'Ollama মডেল পাওয়া গেছে':'কোনো মডেল পাওয়া যায়নি; নিয়মভিত্তিক Parse চলবে')}catch(e){setModels([]);setStatus('Ollama ছাড়াও নিয়মভিত্তিক Parse চলবে: '+e.message)}}
 useEffect(()=>{check();loadModels()},[]);
 async function parse(mode){if(!raw.trim()){setError('আগে তথ্য পেস্ট করুন');return}setLoading(true);setError('');setApproved(false);setData(null);setResult(null);try{
   if(!await check())throw Error('এই ট্যাবটি নতুন React সার্ভারের নয়। npm start-এর উইন্ডোয় দেখানো সঠিক URL খুলুন।');
   const r=await fetch('/api/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({raw,model:mode==='ollama'?model:'',...(mode==='groq'?{provider:'groq',apiKey:groqKey}:mode==='gemini'?{provider:'gemini',apiKey:geminiKey}:{})})});
   const j=await r.json();if(!r.ok)throw Error(j.error||'Parse ব্যর্থ');if(j.version!==VERSION)throw Error('সার্ভার সংস্করণ মিলছে না');
   setEdited([]);setOfficeSources({});setActiveOffice('');birthBeforeOffice.current=null;setResult(j);setData(normalizeNameFields(j.data));setSelectedCandidate(j.addressCandidates?.length===1?j.addressCandidates[0].id:null);if(j.addressCandidates?.length===1)await loadTree(j.addressCandidates[0].districtId);else setTree(null);setStatus(j.warnings?.find(w=>w.includes('Groq ব্যর্থ')||w.includes('Gemini ব্যর্থ')||w.includes('Ollama ব্যর্থ'))|| (j.method==='rules+gemini'?'নিয়মের পর Gemini দিয়ে খালি ফিল্ড যাচাই হয়েছে':j.method==='rules+groq'?'নিয়মের পর Groq দিয়ে খালি ফিল্ড যাচাই হয়েছে':j.method==='rules+ollama'?'নিয়মের পর Ollama ব্যবহার হয়েছে':'নিয়মভিত্তিক ফল তৈরি হয়েছে'));
  }catch(e){setError(e.message)}finally{setLoading(false)}}
 async function loadTree(id){try{const r=await fetch('/api/geo/tree?district='+encodeURIComponent(id),{cache:'no-store'});const j=await r.json();if(!r.ok)throw Error(j.error||'Geo Data পাওয়া যায়নি');setTree(j)}catch(e){setTree(null);setError(e.message)}}
 async function selectCandidate(candidate){setSelectedCandidate(candidate.id);birthBeforeOffice.current=null;setActiveOffice('');setApproved(false);setEdited([]);setOfficeSources(prev=>({...prev,birthPlace:undefined}));setData(prev=>({...prev,birthPlace:cleanEnglishFields(structuredClone(candidate.address))}));await loadTree(candidate.districtId)}
 function changeGeo(field,value){
  const up=field==='upazila'?tree?.upazilas?.find(x=>x.name===value):tree?.upazilas?.find(x=>x.name===get(data,'birthPlace.upazila'));
  const un=field==='union'?up?.unions?.find(x=>x.name===value):up?.unions?.find(x=>x.name===get(data,'birthPlace.union'));
  const firstUnion=field==='upazila'?(up?.unions?.find(x=>x.wards?.length)||up?.unions?.[0]):un;
  const chosenUnion=field==='upazila'?firstUnion:un;
  const firstWard=chosenUnion?.wards?.find(x=>x.number)?.number||'';
  setData(prev=>{const next=structuredClone(prev);const addr=next.birthPlace;
   if(field==='upazila'){addr.upazila=value;addr.union=chosenUnion?.name||'';addr.ward=firstWard}
   if(field==='union'){addr.union=value;addr.ward=firstWard}
   if(field==='ward')addr.ward=value;
   return next});setApproved(false);setEdited(prev=>[...new Set([...prev,'birthPlace.'+field])]);
 }
 function edit(path,value){if(/(?:firstNameBn|lastNameBn|nameBn)$/.test(path))value=normalizeBnName(value);if(/En$/.test(path))value=cleanEnglish(value);setEdited(prev=>prev.includes(path)?prev:[...prev,path]);setData(prev=>{const next=structuredClone(prev);const parts=path.split('.');const field=parts.pop();let current=next;for(const part of parts)current=current[part]??=( {} );current[field]=value;return next});setApproved(false)}
 function toggleNameQuote(path){const value=get(data,path);if(value)edit(path,value.endsWith("'")?value.slice(0,-1):value+"'")}
 const json=useMemo(()=>data?JSON.stringify(cleanEnglishFields(data),null,2):'', [data]);
 async function copy(){if(!approved)return;try{await navigator.clipboard.writeText(json);setStatus('JSON কপি হয়েছে')}catch{setStatus('কপি ব্যর্থ; নিচের JSON থেকে হাতে কপি করুন')}}
 function download(){if(!approved)return;const url=URL.createObjectURL(new Blob([json],{type:'application/json;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='verified-birth-data.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 return <main className="wrap"><header className="hero"><div><div className="eyebrow">অফলাইনে চলে · React UI · Python rules</div><h1>জন্মতথ্য থেকে JSON</h1><p>লেখা থেকে পাওয়া তথ্য দেখুন, Geo Data-র প্রস্তাব যাচাই করুন, তারপর JSON নিন।</p></div><div className="server">{server}<small>ঠিকানা: {location.host}</small></div></header>
 <div className="notice">ঠিকানার Geo প্রস্তাব <b>বাসস্থানের প্রমাণ নয়</b>। ভুল বা অনুপস্থিত তথ্য যাচাই ছাড়া ব্যবহার করবেন না।</div>
 <section className="grid"><div className="panel input"><div className="panel-head"><h2>মূল লেখা</h2><span>WhatsApp ফরম্যাট পেস্ট করুন</span></div><textarea value={raw} onChange={e=>{setRaw(e.target.value);setApproved(false);setData(null);setResult(null);setEdited([]);setTree(null);setSelectedCandidate(null)}} placeholder="নাম: ...\nজন্ম তারিখ: ...\nপিতার নাম: ...\nজেলা: ..." spellCheck={false}/><div className="actions"><button onClick={()=>parse("rules")} disabled={loading}>নিয়ম দিয়ে JSON</button><button className="secondary" onClick={()=>parse("ollama")} disabled={loading||!model}>নিয়ম → দরকারে Ollama</button><button onClick={()=>parse("groq")} disabled={loading}>নিয়ম → দরকারে Groq</button><button onClick={()=>parse("gemini")} disabled={loading}>নিয়ম → দরকারে Gemini</button></div><div className="model"><label>লোকাল মডেল <select value={model} onChange={e=>setModel(e.target.value)}><option value="">নির্বাচন করুন</option>{models.map(m=><option key={m}>{m}</option>)}</select></label><button className="text-button" onClick={loadModels}>মডেল খুঁজুন</button></div><div className="groq-settings"><label>Groq API key (শুধু এই সেশনে)<input type="password" autoComplete="off" value={groqKey} onChange={e=>setGroqKey(e.target.value)} placeholder="gsk_... (অথবা GROQ_API_KEY পরিবেশ ভ্যারিয়েবল)"/></label><small>Groq আবেদনকারীর খালি বাংলা–ইংরেজি নাম, জন্মতারিখ ও লিঙ্গ এবং পিতা-মাতার খালি বাংলা–ইংরেজি নাম চেষ্টা করে। আবেদনকারীর জন্ম ২০১৩ বা পরে হলে উৎসে থাকা পিতা-মাতার ১৭ অঙ্কের BRN ও জন্মতারিখও চেষ্টা করে। সন্তানক্রম, জাতীয়তা ও ঠিকানা Groq পূরণ করে না। প্রয়োজন হলে তবেই মূল লেখা Groq-তে যাবে; key ব্রাউজারে সংরক্ষিত হয় না।</small><label>Gemini API key (আলাদা Google AI Studio key)<input type="password" autoComplete="off" value={geminiKey} onChange={e=>setGeminiKey(e.target.value)} placeholder="Gemini key অথবা GEMINI_API_KEY পরিবেশ ভ্যারিয়েবল"/></label><small>Gemini 2.5 Flash: একই উৎস যাচাই ও নির্দিষ্ট খালি ফিল্ডের নিয়ম। Groq key এখানে চলবে না; Google AI Studio থেকে আলাদা key লাগবে।</small></div><p className="muted">{loading?'পার্সিং চলছে…':status}</p>{error&&<p className="error" role="alert">{error}</p>}</div>
 <div className="panel"><div className="panel-head"><h2>প্রয়োজনীয় তথ্য</h2><span>উৎস মিলিয়ে প্রয়োজনে ঠিক করুন</span></div>{data?<div className="field-groups">{GROUPS.map(([role,title,fields])=><section className="field-group" key={role}><h3>{title}</h3><div className="fields">{fields.map(([field,label])=><label key={field}><span>{label}</span>{field==='gender'&&role==='person'?<select value={get(data,role+'.'+field)} disabled={Boolean(result?.evidence?.['person.gender']?.status==='source-match'&&get(data,'person.gender'))} onChange={e=>edit(role+'.'+field,e.target.value)}><option value="">নেই / হাতে নির্বাচন</option><option value="MALE">পুরুষ</option><option value="FEMALE">মহিলা</option></select>:/^(?:firstName|lastName|name)(?:Bn|En)$/.test(field)?<div className="name-control"><input value={get(data,role+'.'+field)} placeholder={EMPTY} onChange={e=>edit(role+'.'+field,e.target.value)}/><button type="button" className="quote-button" disabled={!get(data,role+'.'+field)} aria-label={label+" নামের শেষে ' যোগ বা সরান"} title="নামের শেষে ' যোগ বা সরান" onClick={()=>toggleNameQuote(role+'.'+field)}>✔️</button></div>:<input value={get(data,role+'.'+field)} placeholder={EMPTY} onChange={e=>edit(role+'.'+field,e.target.value)}/>}</label>)}</div></section>)}</div>:<div className="empty">লেখা পেস্ট করে “নিয়ম দিয়ে JSON” চাপুন।</div>}</div></section>
 <section className="panel section"><div className="panel-head"><h2>অফিস ঠিকানা বাছাই</h2><span>{officePresets.length}টি প্রস্তুত · {customOffices.length}টি নিজের যোগ করা</span></div>
 <p className="muted">লেখা Parse করার পরে অফিসের একটি বোতাম চাপুন। “৩ ঠিকানায়” জন্মস্থান, স্থায়ী ও বর্তমান ঠিকানায় বসাবে; “স্থায়ী + বর্তমান” জন্মস্থানকে আগের মতো রাখবে।</p>
 <div className="office-cards">{offices.map(office=><div className="office-card" key={office.id}><strong>📍 {office.name}</strong><small>{office.address.district} · {office.address.ward?'ওয়ার্ড '+office.address.ward:office.address.area||'অঞ্চল নেই'}</small><div className="office-card-actions"><button className={activeOffice===office.id+':all'?'office-active':''} onClick={()=>applyOffices({birthPlace:office.id,permanentAddress:office.id,presentAddress:office.id},'all')}>৩ ঠিকানায় অফিস</button><button className={activeOffice===office.id+':permanentPresent'?'office-active secondary':'secondary'} onClick={()=>applyOffices({permanentAddress:office.id,presentAddress:office.id},'permanentPresent')}>স্থায়ী + বর্তমান অফিস</button></div></div>)}</div>
 <div className="actions"><button className="secondary" onClick={()=>setOfficeForm(value=>!value)}>{officeForm?'নতুন অফিস বন্ধ করুন':'＋ নতুন অফিস ঠিকানা যোগ'}</button></div>
 {officeForm&&<div className="office-form"><label>অফিসের নাম<input value={officeName} onChange={e=>setOfficeName(e.target.value)} placeholder="যেমন: নতুন অফিস"/></label><label>ঠিকানার JSON<textarea value={officeJSON} onChange={e=>setOfficeJSON(e.target.value)} placeholder={'{"country":"1","division":"ঢাকা বিভাগ","district":"ঢাকা","upazila":"...","union":"...","ward":"...","postOfficeBn":"...","villageBn":"..."}'}/></label><button onClick={saveOffice}>অফিস সংরক্ষণ করুন</button><p className="muted">এই ব্রাউজারে সংরক্ষিত থাকবে; বাংলা ও ইংরেজি মান যেমন দেবেন তেমনই রাখা হবে।</p></div>}
 {customOffices.length>0&&<div className="custom-offices">নিজের অফিস: {customOffices.map(office=><span key={office.id}>{office.name} <button className="text-button" onClick={()=>deleteOffice(office.id)} aria-label={office.name+' মুছুন'}>মুছুন</button></span>)}</div>}
 {officeError&&<p className="error" role="alert">{officeError}</p>}</section>
 {data&&<><section className="panel section"><div className="panel-head"><h2>জন্মস্থানের ঠিকানা বাছাই</h2><span>আগে জেলা, পরে একই জেলার Geo hierarchy</span></div>
{(result.addressCandidates||[]).length?<><div className="candidate-list">{result.addressCandidates.map(c=><button key={c.id} className={selectedCandidate===c.id?'candidate selected':'candidate'} onClick={()=>selectCandidate(c)}><strong>{c.label}</strong><small>জেলা: {c.address.district} · ইউনিয়ন: {c.address.union||'Geo-তে নেই'} · ওয়ার্ড: {c.address.ward||'Geo-তে নেই'}</small></button>)}</div>{!selectedCandidate&&<p className="error">একাধিক জেলা পাওয়া গেছে। জন্মস্থানের জেলা বাছলে JSON-এর birthPlace পূরণ হবে।</p>}
{selectedCandidate&&tree&&<><p className="muted">নিচের তালিকা থেকে উপজেলা, ইউনিয়ন ও ওয়ার্ড বদলাতে পারেন। লিখিত ডাকঘর/গ্রাম থাকলে সেটি সংরক্ষিত থাকবে।</p><div className="address-fields">
{(()=>{const up=tree.upazilas.find(x=>x.name===get(data,'birthPlace.upazila'));const un=up?.unions.find(x=>x.name===get(data,'birthPlace.union'));return <>
<label>উপজেলা<select value={get(data,'birthPlace.upazila')} onChange={e=>changeGeo('upazila',e.target.value)}>{tree.upazilas.map(x=><option key={x.id} value={x.name}>{x.name}</option>)}</select></label>
<label>ইউনিয়ন/এলাকা<select value={get(data,'birthPlace.union')} onChange={e=>changeGeo('union',e.target.value)}>{(up?.unions||[]).map(x=><option key={x.id} value={x.name}>{x.name}</option>)}</select></label>
<label>ওয়ার্ড<select value={get(data,'birthPlace.ward')} onChange={e=>changeGeo('ward',e.target.value)}><option value="">ওয়ার্ড ডেটা নেই</option>{(un?.wards||[]).filter(x=>x.number).map(x=><option key={x.id} value={x.number}>{x.name} ({x.number})</option>)}</select></label>
</>})()}</div></>}
{result.addressCandidates.find(x=>x.id===selectedCandidate)?.warnings?.map((w,i)=><p key={i} className="warning">⚠️ {w}</p>)}</>:<p className="muted">জেলা পাওয়া যায়নি। মূল লেখায় জেলার নাম দিন অথবা উপরের অফিস ঠিকানা বেছে নিন।</p>}{selectedCandidate?.startsWith('office:')&&<p className="muted">অফিস ঠিকানা জন্মস্থানে বসেছে; নিচের ঠিকানার ফিল্ডে প্রয়োজনে বদলাতে পারেন।</p>}</section>
<section className="panel section"><div className="panel-head"><h2>ঠিকানা</h2><span>অমিল থাকলে সতর্কতা পড়ুন</span></div>{result.addressWarnings?.length>0&&<div className="warning">{result.addressWarnings.map((w,i)=><p key={i}>⚠️ {w}</p>)}</div>}{ADDRESSES.map(([role,title])=><details key={role} open={role==='birthPlace'}><summary>{title} <small>{data[role]?.district||'জেলা নেই'}</small></summary><div className="address-fields">{ADDRESS_FIELDS.map(([field,label])=>{const src=officeSources[role]?.[field]||(role==='birthPlace'&&selectedCandidate?(result.addressCandidates||[]).find(x=>x.id===selectedCandidate)?.sources?.[field]:result.addressSources?.[role]?.[field]);const wasEdited=edited.includes(role+'.'+field);return <label key={field}><span>{label}{wasEdited&&<em className="source manual">হাতে সংশোধিত</em>}{!wasEdited&&src&&<em className={'source '+src.source}>{src.source==='office'?'অফিস ঠিকানা':src.source==='geo'?'Geo প্রস্তাব':src.source==='input'?'মূল লেখা':src.source==='default'?'ডিফল্ট':src.source==='transliteration'?(src.from?.endsWith('En')?'ইংরেজি থেকে বাংলা':'বাংলা থেকে ইংরেজি'):'লেখায় মিলেছে'}</em>}</span><input value={get(data,role+'.'+field)} readOnly={role==='birthPlace'&&!!selectedCandidate&&!selectedCandidate.startsWith('office:')&&['country','division','district','upazila','union','ward'].includes(field)} placeholder={EMPTY} onChange={e=>edit(role+'.'+field,e.target.value)}/></label>})}</div></details>)}</section>
 <section className="panel section"><div className="panel-head"><h2>উৎস যাচাই</h2><span>ফল কপি করার আগে মিলিয়ে নিন</span></div>{edited.length>0&&<div className="warning">⚠️ {edited.length}টি ফিল্ড হাতে বদলানো হয়েছে; বদলানো মান মূল লেখার সঙ্গে আবার মিলিয়ে নিন।</div>}<div className="reviews">{Object.entries(result.evidence||{}).map(([path,info])=><div className="review" key={path}><strong>{path}</strong><span className={'badge '+info.status}>{info.status==='source-match'?'উৎস পাওয়া গেছে':info.status==='empty'?'খালি':'যাচাই প্রয়োজন'}</span><small>{info.source||info.reason}</small></div>)}</div>{result.warnings?.length>0&&<div className="warning">{result.warnings.map((w,i)=><p key={i}>⚠️ {w}</p>)}</div>}
 <label className="approval"><input type="checkbox" disabled={(result.addressCandidates||[]).length>1&&!selectedCandidate} checked={approved} onChange={e=>setApproved(e.target.checked)}/><span>আমি মূল লেখা, নাম, জন্মতারিখ ও ঠিকানা মিলিয়ে দেখেছি; Geo প্রস্তাবও যাচাই করেছি।</span></label></section>
 <section className="panel section"><div className="panel-head"><h2>JSON ফলাফল</h2><div className="actions"><button disabled={!approved||((result.addressCandidates||[]).length>1&&!selectedCandidate)} onClick={copy}>JSON কপি</button><button disabled={!approved||((result.addressCandidates||[]).length>1&&!selectedCandidate)} className="secondary" onClick={download}>JSON ডাউনলোড</button></div></div><pre>{json}</pre></section></>}
 <footer>নিয়ম/Ollama এই কম্পিউটারে চলে। Groq বা Gemini বোতাম চাপলে খালি তথ্যের প্রয়োজনে লেখা নির্বাচিত API-তে পাঠানো হয়।</footer></main>
}
createRoot(document.getElementById('root')).render(<App/>);
