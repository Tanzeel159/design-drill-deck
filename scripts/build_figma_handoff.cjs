/* Offline recovery for a cloud MCP rate limit. Uses the standard Figma Plugin API. */
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..');
const screens=JSON.parse(fs.readFileSync(path.join(root,'qa/figma-ready.json'),'utf8'));
screens[0].nodeId='21:17';
const build=async function(screens){
 const page=figma.root.children.find(p=>p.id==='9:14'||p.name==='02 · Local implementation');
 if(!page)throw Error('Open the Design Drill Deck file before running this handoff.');
 await figma.setCurrentPageAsync(page);
 await Promise.all(['Regular','Medium','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
 const ink=await figma.variables.getVariableByIdAsync('VariableID:1:9');
 const paper=await figma.variables.getVariableByIdAsync('VariableID:1:10');
 const heading=await figma.getNodeByIdAsync('21:15');
 const created=[],changed=[];
 const paint=v=>{if(!v)return [];const raw=Object.values(v.valuesByMode)[0];return [figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:raw.r,g:raw.g,b:raw.b}},'color',v)];};
 function stack(parent,name,w,h,direction='VERTICAL'){
  const n=figma.createFrame();parent.appendChild(n);n.name=name;n.layoutMode=direction;
  n.primaryAxisSizingMode='FIXED';n.counterAxisSizingMode='FIXED';n.resize(Math.max(.01,w),Math.max(.01,h));
  n.fills=[];n.itemSpacing=0;n.primaryAxisAlignItems='MIN';n.counterAxisAlignItems='MIN';created.push(n.id);return n;
 }
 function svg(parent,source,w,h,name){
  source=source.replace(/width="[^"]+"/,'width="'+w+'"').replace(/height="[^"]+"/,'height="'+h+'"');
  const n=figma.createNodeFromSvg(source);parent.appendChild(n);n.name=name;created.push(n.id);return n;
 }
 function text(t,parent){
  if(t.svg)return svg(parent,t.svg,t.w,t.h,'Native text / '+t.text);
  if(heading&&['Who it is for','Goal','Constraint','Your task','Work through','Discuss'].includes(t.text)){
   const n=heading.createInstance();parent.appendChild(n);n.setProperties({'Label#21:0':t.text});n.resize(Math.max(t.w+12,parent.width-(parent.layoutMode==='HORIZONTAL'?31:0)),t.h);n.name=t.text;created.push(n.id);return n;
  }
  const n=figma.createText();parent.appendChild(n);n.fontName={family:'Inter',style:t.weight>=600?'Bold':t.weight>=450?'Medium':'Regular'};
  n.fontSize=t.size;n.lineHeight={unit:'PIXELS',value:t.line};n.letterSpacing={unit:'PIXELS',value:t.tracking||0};
  const content=t.renderText||t.text,lines=content.split('\n');
  n.textAutoResize='WIDTH_AND_HEIGHT';const spacing=[];
  for(let i=0;i<lines.length;i++){n.characters=lines[i];spacing.push(lines[i].length>1&&t.lineWidths?.[i]?(t.lineWidths[i]-n.width)/(lines[i].length-1):0);}
  n.characters=content;let start=0;
  for(let i=0;i<lines.length;i++){if(lines[i].length)n.setRangeLetterSpacing(start,start+lines[i].length,{unit:'PIXELS',value:spacing[i]});start+=lines[i].length+1;}
  n.textAutoResize='NONE';n.resize(t.w+1,t.h);n.name=t.text;n.fills=paint(ink);created.push(n.id);return n;
 }
 function divider(parent,w,h){
  let d='';if(w>h){for(let x=0;x<w;x+=4)d+=`M${x} 0h.7v.7h-.7Z`;}
  else{for(let y=0;y<h;y+=4)d+=`M0 ${y}h.7v.7h-.7Z`;}
  return svg(parent,`<svg width="${Math.max(1,w)}" height="${Math.max(1,h)}" viewBox="0 0 ${Math.max(1,w)} ${Math.max(1,h)}"><path fill="#000" d="${d}"/></svg>`,Math.max(1,w),Math.max(1,h),'Dotted divider');
 }
 function column(c,parent){
  if(c.divider){divider(parent,c.w,c.h);return;}
  const f=stack(parent,c.name,c.w,c.h);
  if(c.arts?.length&&c.texts.length===2){
   const a=c.arts[0],t=c.texts[0],row=stack(f,'Icon + heading',c.w,Math.max(a.h,t.h),'HORIZONTAL');
   row.counterAxisAlignItems='CENTER';row.itemSpacing=t.x-a.x-a.w;svg(row,a.svg,a.w,a.h,'Context icon');text(t,row);
   f.itemSpacing=c.texts[1].y-c.y-row.height;text(c.texts[1],f);
  }else{
   f.itemSpacing=c.texts.length>1?c.texts[1].y-c.texts[0].y-c.texts[0].h:0;
   for(const t of c.texts)text(t,f);
  }
 }
 function section(s,parent){
  const name=s.name.split(' ')[0].replace('ddd-','');
  const f=stack(parent,name,s.w,s.h);
  if(s.columns){
   const vertical=s.columns.at(-1).y>s.columns[0].y+5;f.layoutMode=vertical?'VERTICAL':'HORIZONTAL';
   f.itemSpacing=vertical?s.columns[1].y-s.columns[0].y-s.columns[0].h:s.columns[1].x-s.columns[0].x-s.columns[0].w;
   for(const c of s.columns)column(c,f);
  }else if(name==='divider')divider(f,s.w,s.h);
  else if(s.arts?.length){
   const a=s.arts[0];f.layoutMode='HORIZONTAL';f.counterAxisAlignItems='CENTER';
   svg(f,a.svg,a.w,a.h,'Category illustration');f.itemSpacing=s.texts[0].x-a.x-a.w;
   const last=s.texts.at(-1),copy=stack(f,'Challenge',s.texts[0].w,last.y+last.h-s.texts[0].y);
   copy.itemSpacing=s.texts[1].y-s.texts[0].y-s.texts[0].h;for(const t of s.texts)text(t,copy);
  }else{
   f.itemSpacing=s.texts?.length>1?s.texts[1].y-s.texts[0].y-s.texts[0].h:0;
   for(const t of s.texts||[])text(t,f);
  }
 }
 for(const s of screens){
  const screen=await figma.getNodeByIdAsync(s.nodeId);if(!screen)throw Error('Missing target screen '+s.nodeId);
  for(const child of [...screen.children])if(['Device brief','Native footer'].includes(child.name))child.remove();
  screen.resize(s.width,s.height);screen.fills=paint(paper);changed.push(screen.id);
  const r=stack(screen,'Device brief',s.card.w,s.card.h);r.x=s.card.x;r.y=s.card.y;
  r.paddingLeft=s.sections[0].x-s.card.x;r.paddingRight=s.card.w-r.paddingLeft-s.sections[0].w;
  r.paddingTop=s.sections[0].y-s.card.y;r.itemSpacing=s.sections[1].y-s.sections[0].y-s.sections[0].h;
  for(const sec of s.sections)section(sec,r);
  const f=stack(screen,'Native footer',s.footer.w,s.footer.h,'HORIZONTAL');f.x=s.footer.x;f.y=s.footer.y;
  f.primaryAxisAlignItems='SPACE_BETWEEN';f.counterAxisAlignItems='CENTER';f.paddingLeft=8;f.paddingRight=8;
  f.strokes=paint(ink);f.strokeTopWeight=1;f.strokeBottomWeight=0;f.strokeLeftWeight=0;f.strokeRightWeight=0;f.dashPattern=[1,3];
  for(const [index,t] of s.footer.texts.entries()){const n=text(t,f);if(n.type==='TEXT')n.textAlignHorizontal=index?'RIGHT':'LEFT';}
 }
 const first=await figma.getNodeByIdAsync(screens[0].nodeId);figma.viewport.scrollAndZoomIntoView([first]);
 return {createdNodeIds:created,mutatedNodeIds:changed,screens:screens.length};
};
const dir=path.join(root,'qa/figma-handoff');fs.mkdirSync(dir,{recursive:true});
const run=`(${build.toString()})(${JSON.stringify(screens)})`;
fs.writeFileSync(path.join(dir,'bridge.js'),`return await ${run};`);
fs.writeFileSync(path.join(dir,'plugin.js'),`${run}.then(()=>figma.closePlugin('Updated all nine device screens.')).catch(e=>figma.closePlugin(e.message));`);
fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify({name:'Design Drill Deck — finish brief redesign',id:'design-drill-deck-brief-handoff',api:'1.0.0',main:'plugin.js',editorType:['figma'],documentAccess:'dynamic-page',networkAccess:{allowedDomains:['none']}},null,2));
console.log('Prepared offline Figma handoff for nine existing screens');
