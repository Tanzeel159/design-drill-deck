/* The same renderer is used interactively and by the acceptance checks. */
const engine = new liquidjs.Liquid();
const DEVICE_CONFIGS = {
  'og-full': {label:'OG · Full screen',width:800,height:480,layout:'full',screenClass:'screen screen--og screen--1bit'},
  'x-landscape': {label:'X · Landscape',width:1872,height:1404,layout:'full',screenClass:'screen screen--v2 screen--lg screen--4bit'},
  'x-portrait': {label:'X · Portrait',width:1404,height:1872,layout:'full',screenClass:'screen screen--v2 screen--lg screen--portrait screen--4bit'},
  'og-half-horizontal': {label:'OG · Half horizontal',width:800,height:480,layout:'half_horizontal',screenClass:'screen screen--og screen--1bit'},
  'og-half-vertical': {label:'OG · Half vertical',width:800,height:480,layout:'half_vertical',screenClass:'screen screen--og screen--1bit'},
  'og-quadrant': {label:'OG · Quadrant',width:800,height:480,layout:'quadrant',screenClass:'screen screen--og screen--1bit'}
};
const $ = id => document.getElementById(id);
let templates = {}, shared = '', baseData, feed, renderEpoch = 0, renderQueue = Promise.resolve();
function option(value,label){const o=document.createElement('option');o.value=value;o.textContent=label;return o;}
function deviceMarkup(c){
  const active=`<div class="view view--${c.layout}" id="active-view"></div>`;
  if(c.layout==='full')return `<div class="${c.screenClass}">${active}</div>`;
  const count=c.layout==='quadrant'?4:2;
  const mashup=c.layout==='half_horizontal'?'1Tx1B':c.layout==='half_vertical'?'1Lx1R':'2x2';
  return `<div class="${c.screenClass}"><div class="mashup mashup--${mashup}"><div class="mashup-cell">${active}</div>${Array.from({length:count-1},()=>`<div class="mashup-cell"><div class="view view--${c.layout}"><div class="placeholder-view">Another plugin</div></div></div>`).join('')}</div></div>`;
}
function auditCard(){
  const root=document.querySelector('.ddd-card');if(!root)return ['Card did not render'];
  const bounds=root.getBoundingClientRect(),errors=[];
  for(const el of root.querySelectorAll('.ddd-title,.ddd-brief,.ddd-kicker,.ddd-footer,.ddd-art')){
    if(getComputedStyle(el).display==='none'||!el.getClientRects().length)continue;
    const r=el.getBoundingClientRect();
    if(r.left<bounds.left-1||r.top<bounds.top-1||r.right>bounds.right+1||r.bottom>bounds.bottom+1||el.scrollWidth>el.clientWidth+1)errors.push(`${el.className}: outside card`);
  }
  const main=root.querySelector('.ddd-main'),copy=root.querySelector('.ddd-copy');
  if(main&&copy){const m=main.getBoundingClientRect(),c=copy.getBoundingClientRect();if(c.top<m.top-1||c.bottom>m.bottom+1)errors.push('Copy exceeds main area');}
  const footer=root.querySelector('.ddd-footer');
  if(footer){const spans=[...footer.children];if(spans.length>1&&spans[0].getBoundingClientRect().right>spans[1].getBoundingClientRect().left-2)errors.push('Footer overlaps');}
  return errors;
}
async function renderCard(device,prompt,level='intermediate',forceLayout){
  const config=DEVICE_CONFIGS[device],data=structuredClone(feed||baseData);
  data.prompts=prompt?[{...prompt,...(forceLayout?{render_layout:forceLayout}:{})}]:[];
  data.daily_picks={preview:{all:{[level]:{prompt_id:prompt?.id,drill_number:1,pool_size:data.prompts.length}}}};
  data.trmnl={plugin_settings:{custom_fields_values:{focus_area:'all',difficulty:level,rotation_mode:'preview'}}};
  $('device-zoom').style.transform='none';
  $('device-zoom').innerHTML=deviceMarkup(config);
  const view=$('active-view');view.innerHTML=await engine.parseAndRender(shared+templates[config.layout],data);
  await document.fonts.ready;
  const root=view.querySelector('.ddd-card');
  let errors=auditCard();
  if(errors.length&&config.layout==='full'&&!forceLayout){root.classList.add('ddd-poster');errors=auditCard();}
  const variant=root.classList.contains('ddd-poster')?'Poster':'Visual Brief';
  return {errors,variant,device,promptId:prompt?.id||null};
}
function fitPreview(){
  const c=DEVICE_CONFIGS[$('device-select').value];if(!c)return;
  const stage=$('preview-stage'),native=$('zoom-select').value==='native';
  const scale=native?1:Math.min(1,Math.max(1,stage.clientWidth-64)/c.width,Math.max(1,stage.clientHeight-48)/c.height);
  stage.classList.toggle('native',native);$('device-canvas').style.width=`${c.width*scale}px`;$('device-canvas').style.height=`${c.height*scale}px`;
  $('device-zoom').style.transform=`scale(${scale})`;$('scale-label').textContent=`${c.width} × ${c.height} · ${Math.round(scale*100)}%`;
}
function selectedPrompt(){
  const id=$('drill-select').value;if(id!=='today')return feed.prompts.find(p=>p.id===id);
  const pick=feed.daily_picks[$('rotation-select').value]?.[$('focus-select').value]?.[$('difficulty-select').value];
  return feed.prompts.find(p=>p.id===pick?.prompt_id);
}
function fullBrief(p){
  const el=$('brief-content');el.replaceChildren();if(!p){el.textContent='No saved prompt is available.';return;}
  function block(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;el.append(n);return n;}
  block('h2',p.display_title||p.problem);block('p',`${p.mode} · ${p.provenance?.source==='generated'?'API generated':p.provenance?.source==='mock'?'Demo response':'Curated'} · ${p.id}`,'origin');
  block('p',p.problem);
  const level=feed.difficulty_levels.find(l=>l.key===$('difficulty-select').value);
  const observation=['Everyday UX','Dark Patterns'].includes(p.mode);
  block('h3',`${level.label} practice`);
  block('p',observation?({beginner:'Describe one observation and sketch an alternative.',intermediate:'Explain the user impact, sketch an alternative, and propose a way to test it.',advanced:'Compare alternatives, examine tradeoffs, and explain how to measure the improvement.'}[$('difficulty-select').value]):level.scope_note);
  for(const [label,key] of [['Who it is for','primary_user'],['Goal','business_goal'],['Constraint','constraint'],['Watch for','watch_for']]){block('h3',label);block('p',p[key]);}
  block('h3','Work through');const ul=block('ul','');for(const item of p.required_patterns.slice(0,level.pattern_limit)){const li=document.createElement('li');li.textContent=item;ul.append(li);}
  block('h3','Discuss');block('p',p.interview_focus);
  const a=block('a','Link to this brief');a.href=`?prompt=${encodeURIComponent(p.id)}&source=${$('source-select').value}&brief=1`;
}
async function renderAll(){
  const epoch=++renderEpoch,p=selectedPrompt(),device=$('device-select').value;
  const level=$('difficulty-select').value;
  const task=renderQueue.then(()=>epoch===renderEpoch?renderCard(device,p,level):null);
  renderQueue=task.catch(()=>{});
  const result=await task;if(!result||epoch!==renderEpoch)return;
  $('device-label').textContent=DEVICE_CONFIGS[device].label;$('variant-label').textContent=DEVICE_CONFIGS[device].layout==='full'?result.variant:'Compact';
  $('selection-label').textContent=p?`${p.id} / ${p.display_title}`:'Empty-feed preview';
  $('fit-status').textContent=result.errors.length?result.errors.join(' · '):'Text fits at native size';$('fit-status').dataset.error=String(!!result.errors.length);
  const source=p?.provenance?.source||'curated';
  $('source-status').textContent=source==='mock'?'Demo API response · no API call or spending':source==='generated'?'Saved API prompt · no generation during refresh':'Offline deck · works without the generation API';
  fullBrief(p);fitPreview();window.lastRender=result;
}
function refreshPromptOptions(){
  const old=$('drill-select').value,scope=$('focus-select').value;
  $('drill-select').replaceChildren(option('today',"Today’s selection"));
  feed.prompts.filter(p=>scope==='all'||p.mode.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')===scope).forEach(p=>$('drill-select').append(option(p.id,`${p.id.replace('ddd-','')} · ${p.display_title}`)));
  if([...$('drill-select').options].some(o=>o.value===old))$('drill-select').value=old;
}
async function loadSource(){
  const source=$('source-select').value;
  try{const response=await fetch(`/api/feed?source=${source}`);if(!response.ok)throw Error('Local feed unavailable');feed=await response.json();}
  catch(e){feed=structuredClone(baseData);$('status').textContent='Static offline preview';}
  if(new URLSearchParams(location.search).has('empty'))feed.prompts=[];
  refreshPromptOptions();await renderAll();
}
function toggleBrief(open){$('brief-panel').hidden=!open;$('brief-toggle').setAttribute('aria-expanded',String(open));fitPreview();}
async function init(){
  baseData=await fetch('../data/daily.json').then(r=>r.json());feed=baseData;
  shared=await fetch('../src/shared.liquid').then(r=>r.text());
  for(const name of ['full','half_horizontal','half_vertical','quadrant'])templates[name]=await fetch(`../src/${name}.liquid`).then(r=>r.text());
  for(const [key,c] of Object.entries(DEVICE_CONFIGS))$('device-select').append(option(key,c.label));
  for(const s of baseData.scopes)$('focus-select').append(option(s.key,s.label));
  for(const l of baseData.difficulty_levels)$('difficulty-select').append(option(l.key,l.label));
  $('difficulty-select').value=baseData.default_difficulty;
  const params=new URLSearchParams(location.search);
  for(const [key,id] of Object.entries({device:'device-select',focus:'focus-select',level:'difficulty-select',order:'rotation-select',source:'source-select',zoom:'zoom-select'})){if([...$(id).options].some(o=>o.value===params.get(key)))$(id).value=params.get(key);}
  await loadSource();
  const requested=params.get('prompt')||(params.has('drill')?baseData.prompts[Number(params.get('drill'))]?.id:null);
  if(requested&&[...$('drill-select').options].some(o=>o.value===requested))$('drill-select').value=requested;
  for(const id of ['device-select','difficulty-select','rotation-select','drill-select'])$(id).addEventListener('change',renderAll);
  $('focus-select').addEventListener('change',()=>{refreshPromptOptions();renderAll();});$('source-select').addEventListener('change',()=>{$('drill-select').value='today';loadSource();});
  $('zoom-select').addEventListener('change',fitPreview);$('brief-toggle').addEventListener('click',()=>toggleBrief($('brief-panel').hidden));$('brief-close').addEventListener('click',()=>toggleBrief(false));
  for(const [id,delta] of [['previous',-1],['next',1]])$(id).addEventListener('click',()=>{const s=$('drill-select');s.selectedIndex=(s.selectedIndex+delta+s.length)%s.length;renderAll();});
  new ResizeObserver(fitPreview).observe($('preview-stage'));
  if(params.has('brief'))toggleBrief(true);
  await renderAll();$('status').textContent=`${baseData.prompts.length} saved prompts · ${baseData.scopes.length-1} categories`;
  window.deckStudio={renderCard,auditCard,devices:DEVICE_CONFIGS,get prompts(){return feed.prompts},get templates(){return templates}};
  document.body.dataset.previewReady='true';
}
init().catch(e=>{$('status').textContent=e.message;document.body.dataset.previewError=e.message;});
