/* Export measured local layout values for the editable Figma implementation page. */
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{
 const browser=await chromium.launch(process.platform==='win32'?{channel:'msedge'}:{});
 const page=await browser.newPage({viewport:{width:1600,height:1100}});
 const examples=[['ddd-012','og-full'],['ddd-043','og-full'],['ddd-049','og-full'],['ddd-012','og-half-horizontal'],['ddd-012','og-half-vertical'],['ddd-012','og-quadrant'],['ddd-012','x-landscape'],['ddd-049','x-portrait']];
 const result=[];
 for(const [id,device] of examples){
  await page.goto(`http://127.0.0.1:4173/preview/?prompt=${id}&device=${device}&zoom=native`);
  await page.waitForFunction(()=>document.body.dataset.previewReady==='true');
  result.push(await page.evaluate(({id,device})=>{
   const screen=document.querySelector('.screen'),origin=screen.getBoundingClientRect();
   function read(selector){const e=document.querySelector(selector);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.textContent,x:r.x-origin.x,y:r.y-origin.y,width:r.width,height:r.height,fontSize:parseFloat(s.fontSize),lineHeight:parseFloat(s.lineHeight),fontWeight:s.fontWeight,letterSpacing:parseFloat(s.letterSpacing)||0,padding:[s.paddingTop,s.paddingRight,s.paddingBottom,s.paddingLeft].map(parseFloat),gap:parseFloat(s.gap)||0,display:s.display,svg:e.querySelector('svg')?.outerHTML};}
   return {id,device,width:origin.width,height:origin.height,card:read('.ddd-card'),header:read('.ddd-kicker'),main:read('.ddd-main'),copy:read('.ddd-copy'),title:read('.ddd-title'),brief:read('.ddd-brief'),art:read('.ddd-art'),footer:read('.ddd-footer'),source:read('.ddd-footer span:first-child'),date:read('.ddd-footer span:last-child')};
  },{id,device}));
 }
 fs.writeFileSync('qa/figma-layouts.json',JSON.stringify(result,null,2));
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
