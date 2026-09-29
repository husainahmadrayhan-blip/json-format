import {spawn,spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {existsSync} from 'node:fs';
const root=dirname(fileURLToPath(import.meta.url));
// Python serves dist/, so refresh it on every local start when npm packages
// are available. The ZIP also includes dist/ for a Python-only installation.
if(existsSync(join(root,'node_modules','vite'))){
 const build=spawnSync(process.platform==='win32'?'npm.cmd':'npm',['run','build'],{cwd:root,stdio:'inherit',timeout:120000,shell:process.platform==='win32'});
 if(build.status!==0){console.error('React build ব্যর্থ হয়েছে; npm start বন্ধ করা হলো।');process.exit(1)}
}
if(!existsSync(join(root,'dist','index.html'))){
 console.error('React dist/index.html নেই। npm install এবং npm run build চালান।');process.exit(1);
}
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
