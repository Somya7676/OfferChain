'use strict';
const $ = id => document.getElementById(id);
const pages = ['dashboard', 'register', 'verify', 'explorer'];
const labels = {dashboard:'Dashboard',register:'Register offer',verify:'Verify offer',explorer:'Blockchain explorer'};
let toastTimer;
function toast(message) { const el=$('toast'); el.textContent=message; el.classList.add('show'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove('show'),3000); }
function element(tag, text, className) { const node=document.createElement(tag); if(text !== undefined) node.textContent=text; if(className) node.className=className; return node; }
function copyButton(label, value) { const btn=element('button', label, 'inline-copy'); btn.type='button'; btn.addEventListener('click',()=>copy(value)); return btn; }
async function copy(value) {
  try { if(!navigator.clipboard || !window.isSecureContext) throw Error(); await navigator.clipboard.writeText(value); toast('Copied to clipboard.'); }
  catch (_) { const field=element('textarea'); field.value=value; field.style.position='fixed'; field.style.left='-9999px'; document.body.appendChild(field); field.select(); try { if(!document.execCommand('copy')) throw Error(); toast('Copied to clipboard.'); } catch (_) { toast('Copy failed. Please select and copy the text.'); } field.remove(); }
}
async function api(url, options) {
  let response;
  try { response=await fetch(url, options); } catch (_) { throw new Error('Unable to reach the server. Check your connection and try again.'); }
  let data; try { data=await response.json(); } catch (_) { throw new Error('The server returned an unexpected response.'); }
  if(!response.ok) { const error=new Error(data.message || data.error || 'The request could not be completed.'); error.data=data; error.http=response.status; throw error; }
  return data;
}
function dateText(value) { const d=new Date(value); return Number.isNaN(d.getTime()) ? value : d.toLocaleString(undefined, {dateStyle:'medium', timeStyle:'short'})+' ('+Intl.DateTimeFormat().resolvedOptions().timeZone+')'; }
function route() {
  const page=pages.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'dashboard';
  pages.forEach(name=>{ $(name).hidden=name!==page; const link=document.querySelector(`[data-page="${name}"]`); link.classList.toggle('active',name===page); if(name===page) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current'); });
  $('breadcrumb').textContent=labels[page];
  if(page==='dashboard') refreshDashboard();
  if(page==='explorer') refreshExplorer();
  window.scrollTo(0,0);
}
window.addEventListener('hashchange',route);
function paintStatus(status) {
  const header=$('header-status'); header.className='status-pill '+(status.valid ? '' : 'invalid'); header.replaceChildren(element('span',undefined,'status-dot'),document.createTextNode(status.valid?'Chain valid':'Integrity warning'));
  $('total-offers').textContent=status.valid ? status.total_offers : '—'; $('total-blocks').textContent=status.valid ? status.total_blocks : '—'; $('integrity-value').textContent=status.valid ? 'Valid' : 'Invalid';
  const dashboard=$('dashboard-status'); dashboard.className='health-box'+(status.valid?'':' bad'); dashboard.textContent=status.valid?'✓  All blocks passed integrity checks.':'!  Integrity check failed. '+(status.error||'Inspect the ledger.');
  $('explorer-status').textContent=status.valid?'✓  Chain integrity verified':'!  Chain integrity failed';
}
function paintStatusError(message) {
  $('header-status').className='status-pill invalid'; $('header-status').replaceChildren(element('span',undefined,'status-dot'),document.createTextNode('Ledger unavailable'));
  $('total-offers').textContent='—'; $('total-blocks').textContent='—'; $('integrity-value').textContent='Unavailable'; $('dashboard-status').className='health-box bad'; $('dashboard-status').textContent='!  '+message; $('explorer-status').textContent='!  Ledger unavailable';
}
async function refreshStatus() {
  try { const data=await api('/api/chain/status'); paintStatus(data); return data; }
  catch(error) { if(error.data && error.data.valid===false) {paintStatus(error.data); return error.data;} paintStatusError(error.message); return null; }
}
async function refreshDashboard() {
  $('recent-list').replaceChildren(element('p','Loading records…','empty'));
  const [status, result]=await Promise.all([refreshStatus(), api('/api/offers').catch(error=>({error:error.message}))]);
  const list=$('recent-list'); list.replaceChildren();
  if(!status || !status.valid || result.error) { list.append(element('p',result.error || 'Records are unavailable while integrity is invalid.','empty')); return; }
  if(!result.offers.length) { list.append(element('p','No offers registered yet. Register your first fictional offer to get started.','empty')); return; }
  result.offers.slice(0,4).forEach(b=>{ const row=element('div',undefined,'recent-row'); const symbol=element('span','▤','recent-symbol'); const info=element('div',undefined,'recent-info'); info.append(element('strong',b.offer_id),element('small',`Block #${b.block_index}  ·  ${dateText(b.timestamp)}`)); row.append(symbol,info,element('span','Recorded','mini-badge')); list.append(row); });
}
function td(row, text) { const cell=element('td',text); row.append(cell); return cell; }
function addHashCell(row, hash) { const cell=td(row,undefined); const code=element('code',hash.slice(0,12)+'…'); const detail=element('details'); detail.append(element('summary','Full hash'),element('code',hash),copyButton('Copy hash',hash)); cell.append(code,detail); }
async function refreshExplorer() {
  $('blocks-list').replaceChildren(element('p','Loading blocks…','empty')); $('record-count').textContent='—';
  const [status, result]=await Promise.all([refreshStatus(),api('/api/chain/blocks').catch(error=>({error:error.message}))]);
  const target=$('blocks-list'); target.replaceChildren();
  if(!status || !status.valid || result.error) { target.append(element('p',result.error||'Records are unavailable while integrity is invalid.','empty')); return; }
  $('record-count').textContent=`${result.blocks.length} ${result.blocks.length===1?'block':'blocks'}`;
  const wrap=element('div',undefined,'blocks-table'), table=element('table'), head=element('thead'), hr=element('tr');
  ['Block','Offer ID','Timestamp','Offer hash','Previous hash','Block hash','Status'].forEach(label=>hr.append(element('th',label))); head.append(hr); table.append(head); const body=element('tbody');
  [...result.blocks].reverse().forEach(b=>{ const row=element('tr'); const index=td(row,undefined); index.append(element('strong','#'+b.index)); const id=td(row,undefined); id.append(element('strong',b.index===0?'Genesis block':b.offer_id)); if(b.index!==0) id.append(document.createElement('br'),copyButton('Copy ID',b.offer_id)); td(row,dateText(b.timestamp)); addHashCell(row,b.offer_hash); addHashCell(row,b.previous_hash); addHashCell(row,b.block_hash); const stat=td(row,undefined); stat.append(element('span','✓ Valid','mini-badge')); body.append(row); });
  table.append(body); wrap.append(table); target.append(wrap);
}
function addDetail(dl, label, value) { dl.append(element('dt',label),element('dd',String(value))); }
function renderResult(target, kind, title, message, details, note, hash) {
  target.replaceChildren(); const panel=element('div',undefined,'result'+(kind==='bad'?' bad':kind==='neutral'?' neutral':'')); const heading=element('div',undefined,'result-head'); heading.append(element('div',title,'result-title')); const close=element('button','Dismiss'); close.type='button'; close.setAttribute('aria-label','Dismiss result'); close.addEventListener('click',()=>target.replaceChildren()); heading.append(close); panel.append(heading,element('p',message));
  if(details && Object.keys(details).length){ const dl=element('dl'); Object.entries(details).forEach(([k,v])=>addDetail(dl,k,v)); panel.append(dl); }
  if(hash){ const row=element('div',undefined,'copy-actions'); row.append(copyButton('Copy Offer ID',details['Offer ID']),copyButton('Copy hash',hash)); panel.append(row); }
  if(note) panel.append(element('p',note)); target.append(panel);
}
function setupForm(name) {
  const form=$(name+'-form'), errorEl=$(name+'-error'), result=$(name+'-result');
  form.addEventListener('reset',event=>{ if([...form.elements].some(e=>e.name && e.value) && !confirm('Clear the information you entered?')) {event.preventDefault();return;} errorEl.textContent=''; result.replaceChildren(); });
  if(name==='verify') form.addEventListener('input',()=>result.replaceChildren());
  form.addEventListener('submit',async event=>{
    event.preventDefault(); if(!form.reportValidity()) return; errorEl.textContent=''; if(name==='register') result.replaceChildren();
    const button=form.querySelector('[type=submit]'); const old=button.textContent; button.disabled=true; button.textContent=name==='register'?'Registering…':'Verifying…';
    try {
      const data=Object.fromEntries(new FormData(form)); const response=await api(name==='register'?'/api/offers':'/api/offers/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
      if(name==='register') { renderResult(result,'good','✓  Registration successful',response.message,{'Offer ID':response.offer_id,'Block':`#${response.block_index}`,'Registered':dateText(response.timestamp),'Hash preview':response.hash_preview+'…'},'This record belongs to a local Python blockchain prototype.',response.offer_hash); toast('Offer registered successfully.'); refreshStatus(); }
      else { const types={VERIFIED:['good','✓  VERIFIED'],MISMATCH:['bad','!  MISMATCH'],NOT_FOUND:['neutral','ⓘ  NOT FOUND']}; const type=types[response.status]||['neutral',response.status]; const details={'Offer ID':response.offer_id}; if(response.block_index!==undefined) details.Block='#'+response.block_index; renderResult(result,type[0],type[1],response.message,details,response.status==='VERIFIED'?'A match does not authenticate the employer or guarantee the offer is genuine.':''); }
    } catch(error) { if(name==='verify' && error.data && error.data.status==='CHAIN_INVALID') renderResult(result,'bad','!  CHAIN INVALID','Verification cannot be trusted because the ledger integrity check failed.',{'Offer ID':form.elements.offer_id.value},'Inspect the ledger before continuing.'); else errorEl.textContent=error.message; if(error.data && error.data.status==='CHAIN_INVALID') refreshStatus(); }
    finally {button.disabled=false;button.textContent=old;}
  });
}
setupForm('register'); setupForm('verify');
document.querySelectorAll('.check-chain').forEach(button=>button.addEventListener('click',async()=>{button.disabled=true; const status=await refreshStatus(); button.disabled=false; toast(status?(status.valid?'Integrity check passed.':'Integrity check failed.'):'Could not check integrity.'); if(!$('explorer').hidden) refreshExplorer(); }));
document.querySelectorAll('.refresh-dashboard').forEach(b=>b.addEventListener('click',refreshDashboard));
document.querySelectorAll('.refresh-explorer').forEach(b=>b.addEventListener('click',refreshExplorer));
route();
