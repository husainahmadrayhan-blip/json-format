const ADDRESS_KEYS=['country','division','district','upazila','union','ward','area','postOfficeBn','postOfficeEn','postCode','villageBn','villageEn','houseRoadBn','houseRoadEn'];

export function officeAddress(office,role){
 const source=role==='presentAddress'?(office.presentAddress||office.address):office.address;
 return Object.fromEntries(ADDRESS_KEYS.filter(key=>typeof source?.[key]==='string'||typeof source?.[key]==='number').map(key=>[key,String(source[key])]));
}

export function assignOffice(data,office,mode,priorBirth){
 if(mode!=='all'&&mode!=='permanentPresent')throw Error('অফিস ব্যবহারের ধরন ভুল');
 const permanentAddress=officeAddress(office,'permanentAddress');
 const presentAddress=officeAddress(office,'presentAddress');
 if(!permanentAddress.district||!presentAddress.district)throw Error(office.name+' ঠিকানায় জেলা নেই');
 const result={...data,permanentAddress,presentAddress};
 if(mode==='all'){
  const birthPlace=officeAddress(office,'birthPlace');
  if(!birthPlace.district)throw Error(office.name+' জন্মস্থানের ঠিকানায় জেলা নেই');
  result.birthPlace=birthPlace;
 }else if(priorBirth!==undefined)result.birthPlace=structuredClone(priorBirth);
 return result;
}
