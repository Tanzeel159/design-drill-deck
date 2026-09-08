/* Native layout acceptance gate. Never contacts third-party URLs. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http');
const ROOT=path.resolve(__dirname,'..');
async function run({input, screenshots=false}={}){
 const payload=JSON.parse(fs.readFileSync(path.join(ROOT,'data/daily.json'),'utf8'));
 const cards=input?JSON.parse(fs.readFileSync(input,'utf8')).prompts:payload.prompts;
 const mime={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.ttf':'font/ttf','.svg':'image/svg+xml'};
 const server=http.createServer((req,res)=>{
   const url=new URL(req.url,'http://localhost');
   if(url.pathname==='/api/feed'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(payload));}
   const clean=decodeURIComponent(url.pathname),file=path.resolve(ROOT,'.'+clean+(clean.endsWith('/')?'index.html':''));
   if(!file.startsWith(ROOT+path.sep)||!['preview','src','data','assets'].includes(path.relative(ROOT,file).split(path.sep)[0])){res.statusCode=404;return res.end();}
   try{res.setHeader('Content-Type',mime[path.extname(file)]||'text/plain');res.end(fs.readFileSync(file));}catch(e){res.statusCode=404;res.end();}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 let browser;
 try{
  const opts={headless:true};
  if(process.env.DDD_BROWSER)opts.executablePath=process.env.DDD_BROWSER;
  else if(process.platform==='win32')opts.channel='msedge';
  browser=await chromium.launch(opts);
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/preview/?prompt=ddd-012&zoom=native`);
  await page.waitForFunction(()=>document.body.dataset.previewReady==='true',{},{timeout:15000});
  const results=[];
  const devices=await page.evaluate(()=>Object.keys(deckStudio.devices));
  for(const card of cards){
    let variant='visual',checks=[];
    for(const device of devices){
      const result=await page.evaluate(async({device,card})=>await deckStudio.renderCard(device,card),{device,card});
      if(result.variant==='Poster'&&device.startsWith('x-')||result.variant==='Poster'&&device==='og-full')variant='poster';
      checks.push(result);
    }
    // A single persisted layout must pass every full-screen device, not just the OG.
    if(variant==='poster')for(const device of devices.filter(d=>deckIsFull(d))){
      const replacement=await page.evaluate(async({device,card})=>await deckStudio.renderCard(device,card,'intermediate','poster'),{device,card});
      checks=checks.map(r=>r.device===device?replacement:r);
    }
    results.push({id:card.id,render_layout:variant,checks,accepted:checks.every(r=>!r.errors.length)});
  }
  if(!input){
    for(const device of devices)for(const level of ['beginner','advanced']){
      const r=await page.evaluate(async({device,level})=>deckStudio.renderCard(device,null,level),{device,level});
      if(r.errors.length)errors.push(`Empty ${device}/${level}: ${r.errors.join(',')}`);
    }
    const unknown={...cards[0],visual_key:'unknown'};
    const fallback=await page.evaluate(p=>deckStudio.renderCard('og-full',p),unknown);
    if(fallback.variant!=='Poster'||fallback.errors.length)errors.push('Unknown visual fallback failed');
  }
  if(screenshots){
    fs.mkdirSync(path.join(ROOT,'qa'),{recursive:true});
    for(const id of ['ddd-012','ddd-043','ddd-049']){
      await page.goto(`http://127.0.0.1:${server.address().port}/preview/?prompt=${id}`);
      await page.waitForFunction(()=>document.body.dataset.previewReady==='true');
      await page.screenshot({path:path.join(ROOT,`qa/${id}-studio.png`)});
      await page.locator('#active-view').screenshot({path:path.join(ROOT,`qa/${id}-card.png`)});
    }
    for(const device of devices.filter(d=>d!=='og-full')){
      await page.goto(`http://127.0.0.1:${server.address().port}/preview/?prompt=ddd-043&device=${device}`);
      await page.waitForFunction(()=>document.body.dataset.previewReady==='true');
      await page.screenshot({path:path.join(ROOT,`qa/${device}.png`)});
    }
  }
  return {results,errors,checked:results.length*devices.length,passed:!errors.length&&results.every(r=>r.accepted)};
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
}
function deckIsFull(device){return ['og-full','x-landscape','x-portrait'].includes(device);}
if(require.main===module){
 const args=process.argv.slice(2),input=args.includes('--input')?args[args.indexOf('--input')+1]:null;
 run({input,screenshots:args.includes('--screenshots')}).then(report=>{console.log(JSON.stringify(report));process.exitCode=report.passed?0:1;}).catch(e=>{console.error(e.stack);process.exitCode=2;});
}
module.exports={run};
