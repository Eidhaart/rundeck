import {chromium} from 'playwright';
import fs from 'fs';
import {G} from './glyphs.mjs';import {APPS} from './apps.mjs';
const font=fs.readFileSync('node_modules/@fontsource/share-tech-mono/files/share-tech-mono-latin-400-normal.woff2').toString('base64');
const slug=s=>s.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'').replace(/^(\d)/,'a$1');
const count={};APPS.forEach(a=>count[a[3]]=(count[a[3]]||0)+1);
const missing=APPS.filter(a=>!G[a[3]]).map(a=>a[3]);if(missing.length){console.log('MISSING GLYPHS',missing);process.exit(1)}
fs.mkdirSync('out',{recursive:true});
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',args:['--no-sandbox']});
const p=await b.newPage();const S=+process.argv[2]||192;await p.setViewportSize({width:S,height:S});
const list=[];
for(const [label,pkg,act,g,tag] of APPS){
 const showTag=count[g]>1, gs=Math.round(S*(showTag?.5:.56)), dy=showTag?-S*.07:0;
 await p.setContent(`<html><head><style>@font-face{font-family:stm;src:url(data:font/woff2;base64,${font})}</style></head><body style="margin:0;width:${S}px;height:${S}px;position:relative;overflow:hidden;background:radial-gradient(circle at 50% 40%,#2a1318 0%,#150f1d 45%,#070a13 100%)">
 <div style="position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(0,0,0,.28) 0 ${Math.max(1,S/256)}px,transparent ${Math.max(1,S/256)}px ${Math.max(3,S/86)}px)"></div>
 <div style="position:absolute;left:50%;top:50%;transform:translate(-50%,calc(-50% + ${dy}px));filter:drop-shadow(0 0 ${S*.035}px rgba(255,18,56,.8))">
 <svg viewBox="0 0 40 40" width="${gs}" height="${gs}" fill="none" stroke="#ff1238" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><style>.f{fill:#ff1238;stroke:none}</style>${G[g]}</svg></div>
 ${showTag?`<div style="position:absolute;left:0;right:0;top:${S*.69}px;text-align:center;font-family:stm;font-size:${S*.115}px;letter-spacing:${S*.012}px;color:#1fe3f0;text-shadow:0 0 ${S*.03}px rgba(31,227,240,.7)">${tag}</div>`:''}
 </body></html>`);
 await p.waitForTimeout(20);const name=slug(label);await p.screenshot({path:`out/${name}.png`});list.push({label,pkg,act,name});
}
fs.writeFileSync('out/index.json',JSON.stringify(list,null,1));
// contact sheet
const cols=10,cell=120,rows=Math.ceil(list.length/cols);await p.setViewportSize({width:cols*cell,height:rows*(cell+22)});
await p.setContent(`<body style="margin:0;background:#0b0b10;display:grid;grid-template-columns:repeat(${cols},${cell}px);font:11px sans-serif;color:#aaa">${list.map(l=>`<div style="text-align:center;padding:6px 0 4px"><img src="data:image/png;base64,${fs.readFileSync('out/'+l.name+'.png').toString('base64')}" style="width:88px;height:88px;border-radius:24px"><div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:2px 4px">${l.label}</div></div>`).join('')}</body>`);
await p.waitForTimeout(300);await p.screenshot({path:'sheet.png',fullPage:true});
console.log('rendered',list.length);await b.close();
