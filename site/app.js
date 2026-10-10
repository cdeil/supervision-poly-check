'use strict';
const $ = (id) => document.getElementById(id);
let data, sample, activeCase;
const colors = {sv:'#8dc6bd',coco:'#8ab8d9',shared:'#8dc6bd',extra:'#edab82',missing:'#b6b0e0',background:'#f9faf7'};
const ns='http://www.w3.org/2000/svg';
function el(tag, attrs, content) {const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs||{}))e.setAttribute(k,String(v));if(content!==undefined)e.textContent=content;return e;}
function draw(containerId, mode) {
  const box=$(containerId);box.replaceChildren();
  const svg=el('svg',{viewBox:'0 0 320 328',role:'img','aria-label':`${activeCase.title}: ${mode==='sv'?`${view()==='after'?'After':'Before'} Supervision mask`:mode==='coco'?(view()==='side'?'After Supervision mask':'COCO reference mask'):'pixel differences'}`});
  svg.append(el('title',{},`${activeCase.title}, offset ${sample.offset.toFixed(2)} pixels`));
  svg.append(el('desc',{},`${sample.svArea} Supervision pixels, ${sample.cocoArea} COCO pixels; ${sample.extra} Supervision-only pixels and ${sample.missing} COCO-only pixels.`));
  const ox=30,oy=18,cell=33,size=cell*8;
  svg.append(el('rect',{x:ox,y:oy,width:size,height:size,fill:colors.background}));
  for(let y=0;y<8;y++)for(let x=0;x<8;x++){
    const i=y*8+x,a=sample.supervision[i],b=sample.coco[i];
    let fill=colors.background,glyph='';
    if(mode==='sv'&&a)fill=colors.sv;
    if(mode==='coco'&&b)fill=colors.coco;
    if(mode==='diff'){if(a&&b)fill=colors.shared;else if(a){fill=colors.extra;glyph='+';}else if(b){fill=colors.missing;glyph='−';}}
    const r=el('rect',{x:ox+x*cell,y:oy+y*cell,width:cell,height:cell,fill,class:'pixel','data-pixel':i});
    r.append(el('title',{},`row ${y}, column ${x} · ${view()==='after'?'After':'Before'} Supervision ${a} · ${view()==='side'?'After':'COCO'} ${b}`));
    const inspect=()=>{$('pixel-detail').textContent=`Row ${y}, column ${x} · continuous centre (${x+.5}, ${y+.5}) · ${view()==='after'?'After':'Before'} Supervision: ${a} · ${view()==='side'?'After':'COCO'}: ${b}`;};
    r.addEventListener('pointerenter',inspect);r.addEventListener('click',inspect);svg.append(r);
    if(glyph)svg.append(el('text',{x:ox+(x+.5)*cell,y:oy+(y+.5)*cell+5,'text-anchor':'middle',fill:'#384656','font-size':16,'font-family':'monospace','pointer-events':'none'},glyph));
    if($('centers').checked)svg.append(el('circle',{cx:ox+(x+.5)*cell,cy:oy+(y+.5)*cell,r:1.6,fill:'#1b2938',opacity:.5,'pointer-events':'none'}));
  }
  for(let i=0;i<=8;i++){
    svg.append(el('line',{x1:ox+i*cell,x2:ox+i*cell,y1:oy,y2:oy+size,stroke:'#c7d2cc','stroke-width':.8,'pointer-events':'none'}));
    svg.append(el('line',{x1:ox,x2:ox+size,y1:oy+i*cell,y2:oy+i*cell,stroke:'#c7d2cc','stroke-width':.8,'pointer-events':'none'}));
    svg.append(el('text',{x:ox+i*cell,y:oy+size+17,'text-anchor':'middle',class:'axis-label'},i));
    svg.append(el('text',{x:ox-12,y:oy+i*cell+4,'text-anchor':'middle',class:'axis-label'},i));
  }
  svg.append(el('text',{x:ox+size/2,y:oy+size+38,'text-anchor':'middle',class:'axis-label'},'x · continuous coordinates (px)'));
  const clipId=`clip-${mode}`;
  const defs=el('defs'),clip=el('clipPath',{id:clipId});
  clip.append(el('rect',{x:ox,y:oy,width:size,height:size}));defs.append(clip);svg.append(defs);
  const geometry=el('g',{'clip-path':`url(#${clipId})`});svg.append(geometry);
  function polygon(points, rounded) {
    const mapped=points.map(([x,y])=>`${ox+(x+(rounded ? 0.5 : 0))*cell},${oy+(y+(rounded ? 0.5 : 0))*cell}`).join(' ');
    geometry.append(el('polygon',{points:mapped,fill:'none',stroke:rounded?'#7b66ad':'#1b2938','stroke-width':rounded?1.6:1.8,'stroke-dasharray':rounded?'5 4':'none','stroke-linejoin':'round','pointer-events':'none'}));
    for(const [x,y]of points)geometry.append(el('circle',{cx:ox+(x+(rounded ? 0.5 : 0))*cell,cy:oy+(y+(rounded ? 0.5 : 0))*cell,r:rounded?2.5:2.1,fill:rounded?'#7b66ad':'#1b2938','pointer-events':'none'}));
  }
  if($('outline').checked)sample.polygons.forEach(p=>polygon(p,false));
  if(mode==='sv'&&view()!=='after'&&$('rounded').checked)sample.rounded.forEach(p=>polygon(p,true));
  box.append(svg);
}
function view(){return document.querySelector('input[name="view"]:checked').value;}
function render(){
  if(!data)return;
  activeCase=data.cases.find(c=>c.id===$('shape').value);sample=activeCase.samples[Number($('offset').value)];
  const mode=view(),beforeArea=sample.svArea;
  if(mode==='after')sample={...sample,supervision:sample.proposed,...sample.after};
  if(mode==='side')sample={...sample,coco:sample.proposed};
  const leftName=mode==='after'?'After · Supervision':'Before · Supervision';
  $('sv-name').textContent=leftName;$('binary-name').textContent=leftName;
  $('sv-description').textContent=mode==='after'?'Opt-in · mask_rasterizer="pycocotools"':'Default · rounded vertices · inclusive fill';
  $('coco-name').textContent=mode==='side'?'After · Supervision':'COCO reference';$('binary-reference-name').textContent=mode==='side'?'After · Supervision':'COCO';
  $('coco-description').textContent=mode==='side'?'Opt-in reference mode · matches COCO exactly':'pycocotools polygon → RLE';
  $('extra-label').textContent=mode==='after'?'After only':'Before only';
  $('missing-label').textContent=mode==='side'?'After only':'Reference only';
  $('proposal-note').textContent=mode==='before'?'Before: current default output. The proposal keeps this default and adds an opt-in reference mode.':`After proposal: ${sample.cocoArea} pixels, versus ${beforeArea} before. All 147 measured after masks match COCO exactly; zero differing pixels.`;

  $('offset-value').textContent=`+${sample.offset.toFixed(2)} px`;
  $('offset').setAttribute('aria-valuetext',`${sample.offset.toFixed(2)} pixels right and down`);
  $('sv-area').textContent=sample.svArea;$('coco-area').textContent=sample.cocoArea;$('xor-area').textContent=sample.extra+sample.missing;
  $('iou').textContent=sample.iou.toFixed(3);$('extra-count').textContent=sample.extra;$('missing-count').textContent=sample.missing;
  $('case-note').textContent=mode==='after' ? 'The patched loader preserves continuous vertices, converts with pycocotools and unions all parts into one object mask.' : sample.offset===0 ? activeCase.note : sample.extra+sample.missing===0 ? 'At this offset, both masks agree. Move the polygon to see where their boundary decisions diverge.' : 'The polygon moves continuously, but pixels change in discrete steps. Rounding and edge inclusion determine which cells change.';
  $('rounded-key').hidden=!$('rounded').checked||mode==='after';
  $('coordinates').textContent=sample.polygons.map((p,i)=>`Part ${i+1}:\n${p.map(([x,y])=>`(${x.toFixed(2)}, ${y.toFixed(2)})`).join('  ')}`).join('\n\n');
  $('rounded-coordinates').textContent=sample.rounded.map((p,i)=>`Part ${i+1}: ${p.map(([x,y])=>`(${x}, ${y})`).join(' ')}`).join('\n');
  const binary=m=>Array.from({length:8},(_,y)=>m.slice(y*8,y*8+8).join('')).join('\n');
  $('sv-binary').textContent=binary(sample.supervision);$('coco-binary').textContent=binary(sample.coco);
  draw('sv-plot','sv');draw('coco-plot','coco');draw('diff-plot','diff');
  $('pixel-detail').textContent='Hover or tap a pixel to inspect its row, column and mask values.';
}
for(const control of document.querySelectorAll('input[name="view"]'))control.addEventListener('change',render);
for(const id of ['shape','outline','centers','rounded'])$(id).addEventListener('change',render);
$('offset').addEventListener('input',render);
$('reset').addEventListener('click',()=>{document.querySelector('input[name="view"][value="before"]').checked=true;$('shape').value='square';$('offset').value=13;$('outline').checked=true;$('centers').checked=true;$('rounded').checked=true;render();});
$('download').addEventListener('click',()=>{if(!sample)return;const blob=new Blob([JSON.stringify({versions:data.versions,proposalSource:data.proposalSource,view:view(),canvas:[8,8],case:activeCase.id,...sample},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${activeCase.id}-offset-${sample.offset.toFixed(2)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
fetch('masks.json').then(r=>{if(!r.ok)throw new Error('Could not load measured masks');return r.json();}).then(d=>{data=d;if(data.proposalSource)$('proposal-link').href=data.proposalSource;render();}).catch(()=>{$('case-note').textContent='The measured masks could not be loaded. Reload the page to try again.';$('case-note').setAttribute('role','alert');});
