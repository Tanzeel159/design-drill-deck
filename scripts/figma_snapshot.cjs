/* Capture the actual browser layout for a faithful Figma sync. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http');
const ROOT=path.resolve(__dirname,'..');
const targets=[
 ['ddd-002','og-full',null],['ddd-012','og-full','11:14'],['ddd-043','og-full','11:30'],['ddd-049','og-full','11:37'],
 ['ddd-012','og-half-horizontal','11:55'],['ddd-012','og-half-vertical','11:62'],['ddd-012','og-quadrant','11:69'],
 ['ddd-012','x-landscape','13:14'],['ddd-049','x-portrait','13:27']
];
(async()=>{
 const server=http.createServer((req,res)=>{
  const u=new URL(req.url,'http://localhost'),file=path.resolve(ROOT,'.'+u.pathname+(u.pathname.endsWith('/')?'index.html':''));
  if(!file.startsWith(ROOT+path.sep)||!['preview','src','data','assets'].includes(path.relative(ROOT,file).split(path.sep)[0])){res.statusCode=404;return res.end();}
  try{res.setHeader('Content-Type',({'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.ttf':'font/ttf'})[path.extname(file)]||'text/plain');res.end(fs.readFileSync(file));}catch{res.statusCode=404;res.end();}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:2200,height:2200}}),out=[];
  for(const [id,device,nodeId] of targets){
   await page.goto(`http://127.0.0.1:${server.address().port}/preview/?prompt=${id}&device=${device}&zoom=native`);
   await page.waitForFunction(()=>document.body.dataset.previewReady==='true');
   const snapshot=await page.evaluate(()=>{
    const screen=document.querySelector('.screen'),base=screen.getBoundingClientRect();
    const scale=base.width/screen.offsetWidth;
    function rect(el){const r=el.getBoundingClientRect();return {x:(r.x-base.x)/scale,y:(r.y-base.y)/scale,w:r.width/scale,h:r.height/scale};}
    const cvs=document.createElement('canvas').getContext('2d');
    function text(el){
     const style=getComputedStyle(el),box=rect(el),chars=[];
     const walk=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let n;
     while(n=walk.nextNode()){
      const s=getComputedStyle(n.parentElement);cvs.font=`${s.fontWeight} ${s.fontSize} ${s.fontFamily}`;
      const asc=cvs.measureText('Hg').fontBoundingBoxAscent;
      for(let i=0;i<n.length;i++){
       const range=document.createRange();range.setStart(n,i);range.setEnd(n,i+1);const r=range.getBoundingClientRect();
       chars.push({c:n.textContent[i],x:(r.x-base.x)/scale,y:(r.y-base.y+asc*scale)/scale,w:r.width/scale,font:s.fontFamily,size:parseFloat(s.fontSize),weight:Number(s.fontWeight)});
      }
     }
     return {...box,text:el.textContent.trim(),font:style.fontFamily,size:parseFloat(style.fontSize),weight:Number(style.fontWeight),line:parseFloat(style.lineHeight),tracking:parseFloat(style.letterSpacing)||0,chars};
    }
    const root=document.querySelector('.ddd-card'),sections=[];
    // Group related text into sections while retaining exact browser measurements.
    for(const el of root.children){
     if(!el.getClientRects().length||getComputedStyle(el).display==='none')continue;
     if(el.matches('.ddd-details,.ddd-context-row,.ddd-work-row')){
      sections.push({...rect(el),name:el.className.split(' ')[0],columns:[...el.children].map(col=>({...rect(col),name:col.querySelector('[data-field]')?.dataset.field||col.className.split(' ')[0],divider:col.classList.contains('divider'),texts:[...col.querySelectorAll('h1,h2,p')].map(text),arts:[...col.querySelectorAll('svg')].map(svg=>({...rect(svg),svg:svg.outerHTML}))}))});
     }else sections.push({...rect(el),name:el.className,texts:el.matches('h1,h2,p')?[text(el)]:[...el.querySelectorAll('h1,h2,p')].map(text),arts:[...el.querySelectorAll('.ddd-art svg')].map(svg=>({...rect(svg),svg:svg.outerHTML}))});
    }
    const footer=document.querySelector('#active-view > .title_bar');
    return {width:screen.offsetWidth,height:screen.offsetHeight,card:rect(root),sections,footer:{...rect(footer),texts:[...footer.children].map(text)}};
   });
   out.push({id,device,nodeId,...snapshot});
   await page.locator('.screen').screenshot({path:path.join(ROOT,`qa/figma-${id}-${device}.png`)});
  }
  fs.writeFileSync(path.join(ROOT,'qa/figma-snapshots.json'),JSON.stringify(out));
  console.log(`Captured ${out.length} device screens`);
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
