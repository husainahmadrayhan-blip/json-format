import {spawn,spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
const root=dirname(fileURLToPath(import.meta.url));
const candidates=process.platform==='win32'?[['py',['-3']],['python',[]]]:[['python3',[]],['python',[]]];
let python;
for(const [cmd,args] of candidates){
 const probe=spawnSync(cmd,[...args,'--version'],{cwd:root,encoding:'utf8',timeout:5000});
 if(probe.status===0){python=[cmd,args];break;}
}
if(!python){console.error('Python 3 পাওয়া যায়নি। Python 3 ইনস্টল করে npm start আবার চালান।');process.exit(1)}
const [cmd,args]=python;
const child=spawn(cmd,[...args,join(root,'server.py')],{cwd:root,stdio:'inherit',windowsHide:false});
child.on('error',error=>{console.error('সার্ভার চালু হয়নি:',error.message);process.exitCode=1});
child.on('exit',(code,signal)=>{if(code!==null)process.exitCode=code;else if(signal!=='SIGINT'&&signal!=='SIGTERM')process.exitCode=1});
process.on('SIGINT',()=>child.kill('SIGINT'));
process.on('SIGTERM',()=>child.kill('SIGTERM'));
