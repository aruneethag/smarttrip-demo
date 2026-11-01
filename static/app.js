'use strict';
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let trip = null, trips = [], busy = false, pending = null;
const emptyPlan = $('#plan-content').innerHTML;
const initialMessage = 'Hi, I’m SmartTrip AI. Where would you like to go, and when are you thinking of traveling?';
let draftMessages = [{role:'assistant',text:initialMessage}];
const unit = c => c === 'JPY' ? 1 : 100;
const money = (n,c) => n === null ? 'Unknown' : new Intl.NumberFormat('en-US',{style:'currency',currency:c,maximumFractionDigits:c==='JPY'?0:2}).format(n/unit(c));
const escape = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateLabel = s => new Date(s+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
const announce = s => { $('#status').textContent=s; };

async function api(path,method='GET',body,key){
  const response=await fetch(path,{method,headers:{'Content-Type':'application/json',...(key?{'Idempotency-Key':key}:{})},...(body?{body:JSON.stringify(body)}:{})});
  if(response.status===204) return null;
  const data=await response.json();
  if(!response.ok){const e=new Error(data.error?.message||'Request failed. Please retry.'); e.fields=data.error?.fields; e.status=response.status; throw e;}
  return data;
}
function showError(e){
  const box=$('#error'); box.hidden=false; box.textContent=e.message;
  for(const [field,message] of Object.entries(e.fields||{})){
    const note=document.querySelector(`[data-error="${field}"]`);
    if(note){note.textContent=message; const input=note.closest('label')?.querySelector('input,select'); input?.setAttribute('aria-invalid','true');}
  }
  if(e.status===409){const btn=document.createElement('button');btn.textContent='Load latest trip';btn.onclick=()=>run(async()=>{trip=await api('/api/trips/'+trip.id);fillForm(trip.details);render();announce('Loaded the latest saved revision.');});box.append(btn);}
  else if(pending){const btn=document.createElement('button');btn.textContent='Retry request';btn.onclick=()=>run(()=>submitPending());box.append(btn);}
  box.scrollIntoView({block:'nearest',behavior:'smooth'});
}
async function run(fn){
  if(busy)return;
  busy=true; $('#error').hidden=true;
  $$('button').forEach(b=>b.disabled=true);
  try{await fn();}catch(e){showError(e);}finally{busy=false;$$('button').forEach(b=>b.disabled=false);}
}
function clearErrors(){ $$('[data-error]').forEach(n=>n.textContent='');$$('[aria-invalid]').forEach(n=>n.removeAttribute('aria-invalid')); }
function readForm(){
  const f=$('#setup-form').elements;
  return {destination:f.destination.value,timeZone:f.timeZone.value,startDate:f.startDate.value,endDate:f.endDate.value,travelers:Number(f.travelers.value),currency:f.currency.value,
    budgetMinor:Math.round(Number(f.budget.value)*unit(f.currency.value)),interests:f.interests.value.split(',').map(x=>x.trim()).filter(Boolean),pace:f.pace.value,transport:f.transport.value,
    accessibility:f.accessibility.value,dietary:f.dietary.value,budgetIncludes:['activities','meals','local transport',...(f.includeAccommodation.checked?['accommodation']:[]),...(f.includeTravel.checked?['travel to destination']:[])]};
}
function fillForm(d){
  const f=$('#setup-form').elements;
  for(const [key,val] of Object.entries(d)){if(f[key] && key!=='budgetIncludes')f[key].value=Array.isArray(val)?val.join(', '):val;}
  if(d.budgetMinor!==undefined)f.budget.value=d.budgetMinor/unit(d.currency||f.currency.value);
  f.includeAccommodation.checked=d.budgetIncludes?.includes('accommodation')||false;
  f.includeTravel.checked=d.budgetIncludes?.includes('travel to destination')||false;
}
function setTab(tab){
  $('.workspace').classList.toggle('show-plan',tab==='plan');
  $$('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===tab)));
}
function renderMessages(){
  const messages=[...draftMessages,...(trip?.messages||[])];
  $('#messages').innerHTML=messages.map(m=>`<div class="message ${m.role==='user'?'user':'assistant'}"><div class="message-label">${m.role==='user'?'YOU':'SMARTTRIP'}</div>${escape(m.text)}</div>`).join('');
  $('#messages').scrollTop=$('#messages').scrollHeight;
}
function renderConfirmation(){
  const el=$('#confirmation');
  const needs=trip&&(trip.confirmedRevision!==trip.intakeRevision||trip.state==='planning'||!trip.itinerary);
  el.hidden=!needs;
  if(!needs)return;
  const d=trip.details;
  el.innerHTML=`<div class="confirmation-card"><h3>Does this feel like your trip?</h3><p class="notice">Review these details before generating. This demo uses fictional places and illustrative prices.</p><dl><dt>Destination</dt><dd>${escape(d.destination)}</dd><dt>Dates</dt><dd>${dateLabel(d.startDate)} – ${dateLabel(d.endDate)}</dd><dt>Local zone</dt><dd>${escape(d.timeZone)}</dd><dt>Party & budget</dt><dd>${d.travelers} travelers · ${money(d.budgetMinor,d.currency)} total</dd><dt>Includes</dt><dd>${escape(d.budgetIncludes.join(', '))}</dd><dt>Pace & travel</dt><dd>${escape(d.pace)} · ${escape(d.transport)}</dd><dt>Interests</dt><dd>${escape(d.interests.join(', '))}</dd><dt>Preferences</dt><dd>${escape([d.accessibility,d.dietary].filter(Boolean).join('; ')||'None supplied')}</dd></dl><p class="notice">Assumptions: full days, no arrival/departure limits supplied; opening hours, travel times, access, and dietary suitability are unverified.</p><div class="confirmation-buttons"><button class="primary" id="confirm-generate">Confirm & generate demo →</button><button id="edit-details">Edit details</button></div></div>`;
  $('#confirm-generate').onclick=()=>run(async()=>{
    announce('Confirming details and building your demo itinerary…');
    trip=await api(`/api/trips/${trip.id}/confirm`,'POST',{expectedIntakeRevision:trip.intakeRevision});
    await mutation('generate',{expectedIntakeRevision:trip.intakeRevision,expectedRevision:trip.itinerary?.revision||0});
  });
  $('#edit-details').onclick=()=>{setTab('chat');$('#setup').open=true;$('#setup-form input').focus();};
}
function render(){
  renderMessages();renderConfirmation();
  $('#trip-label').textContent=trip?.details.destination||'A fresh start';
  const p=trip?.itinerary;
  $('#plan-actions').hidden=!p;
  $('#plan-title').textContent=p?p.destination:trip?'Your trip, taking shape.':'A little inspiration, to start.';
  if(!p){$('#plan-content').innerHTML=emptyPlan;return;}
  const c=p.currency,summary=p.costSummary;
  const current=trip.confirmedRevision===trip.intakeRevision;
  $('#plan-content').innerHTML=`${!current?'<div class="warning">This is the previous itinerary. Confirm your updated details to generate a matching plan.</div>':''}<p class="trip-subtitle">${dateLabel(p.startDate)} – ${dateLabel(p.endDate)} · ${p.travelers} travelers · ${escape(p.timeZone)}<br>DEMO · All named places are fictional · Revision ${p.revision}</p>
  <div class="budget-card"><div class="budget-top"><h3>YOUR BUDGET, IN VIEW · ENTIRE PARTY</h3><span class="budget-status">${summary.budgetStatus==='over'?'⚠ Over budget':summary.budgetStatus==='uncertain'?'? Costs incomplete':'✓ Within estimated budget'}</span></div><div class="budget-total">${money(summary.knownTotalMinor,c)} <small>known estimates / ${money(p.budgetMinor,c)} budget</small></div><div class="budget-track"><span></span></div><p>${summary.unknownCostCount} unknown cost${summary.unknownCostCount===1?'':'s'} · Excludes: ${escape(summary.exclusions.join(', ')||'nothing listed')}<br>Includes: ${escape(p.budgetIncludes.join(', '))}. Estimates are not confirmed quotes.</p></div>
  ${trip.changes.map(x=>`<div class="changes">✓ ${escape(x)}</div>`).join('')}
  ${p.warnings.map(x=>`<div class="warning">⚑ ${escape(x)}</div>`).join('')}
  ${p.days.map((day,i)=>`<article class="day-card"><div class="day-heading"><div><div class="day-number">DAY ${String(i+1).padStart(2,'0')} · ${dateLabel(day.date)}</div><h3>${escape(day.title)}</h3><p>A little discovery, a little breathing room.</p></div><div class="day-amount">${money(day.knownTotalMinor,c)}<small>known party total</small></div></div>${day.items.map(x=>`<div class="itinerary-item"><div class="item-time">${x.startTime||'Flexible'}<span>${x.endTime||'Unscheduled'}</span></div><div class="item-info"><div class="item-meta">${escape(x.kind)} · FICTIONAL SAMPLE</div><h4>${escape(x.title)}</h4>${x.location?`<p>⌖ ${escape(x.location)}</p>`:''}<p>${escape(x.notes)}</p><small>Source: demo-fixtures-v1 · suitability unverified</small>${x.kind==='activity'?`<button class="mini-button" data-action="replace" data-day="${i+1}" data-item="${escape(x.id)}">↻ Replace activity</button>`:''}</div><div class="item-cost">${money(x.cost.amountMinor,c)}<small>${escape(x.cost.status)}</small><button class="mini-button" data-action="cost" data-day="${i+1}" data-item="${escape(x.id)}" aria-label="Edit cost for ${escape(x.title)}">Edit cost</button></div></div>`).join('')}<div class="day-actions"><button data-action="break" data-day="${i+1}">＋ Add a break</button><button data-action="cheaper" data-day="${i+1}">↓ Make cheaper</button><button data-action="edit" data-day="${i+1}">✎ Edit day title</button></div></article>`).join('')}
  <details class="sources"><summary>Assumptions, sources & what to verify <span>＋</span></summary><ul>${p.assumptions.map(x=>`<li>${escape(x)}</li>`).join('')}</ul>${p.sources.map(s=>`<p>${escape(s.provider)} · ${escape(s.dataStatus)}<br>Fixture timestamp: ${escape(s.retrievedAt)}. No live information was retrieved.</p>`).join('')}<p>Open questions: arrival/departure times, real venue choices and costs, opening hours, weather, route feasibility, access, and dietary suitability. Check these before travel.</p></details>`;
  $('.budget-track span').style.width=Math.min(100,100*summary.knownTotalMinor/p.budgetMinor)+'%';
  $('#export-json').href=`/api/trips/${trip.id}/export?format=json`;
  $('#export-md').href=`/api/trips/${trip.id}/export?format=markdown`;
  $('#export-json').setAttribute('download','smarttrip.json');$('#export-md').setAttribute('download','smarttrip.md');
  $$('[data-action]').forEach(b=>b.onclick=()=>run(async()=>{
    const payload={action:b.dataset.action,day:Number(b.dataset.day),...(b.dataset.item?{itemId:b.dataset.item}:{})};
    if(payload.action==='edit'){const title=await editValue('Edit day title','Day title',p.days[payload.day-1].title,'Choose a title of 1–120 characters.');if(title===null)return;payload.title=title;}
    if(payload.action==='cost'){const item=p.days[payload.day-1].items.find(x=>x.id===payload.itemId);const value=await editValue('Edit party cost','Amount in '+c,item.cost.amountMinor===null?'':String(item.cost.amountMinor/unit(c)),'This amount is for the entire party. Leave blank to mark the cost unknown.');if(value===null)return;if(value.trim()!==''&&(!Number.isFinite(Number(value))||Number(value)<0))throw new Error('Enter a nonnegative cost or leave it blank for unknown.');payload.amountMinor=value.trim()===''?null:Math.round(Number(value)*unit(c));}
    await mutation('revise',{...payload,expectedRevision:p.revision});
  }));
}
async function refreshList(){
  trips=(await api('/api/trips')).trips;
  $('#saved-trips').innerHTML='<option value="">Saved trips ('+trips.length+')</option>'+trips.map(t=>`<option value="${t.id}">${escape(t.details.destination)} · ${escape(t.details.startDate)}</option>`).join('');
  if(trip)$('#saved-trips').value=trip.id;
}
async function mutation(action,payload){
  pending={url:`/api/trips/${trip.id}/${action}`,payload,key:crypto.randomUUID()};
  return submitPending();
}
async function submitPending(){
  if(!pending)return;
  announce('Updating your plan…');
  const result=await api(pending.url,'POST',pending.payload,pending.key);
  pending=null;trip=result;render();await refreshList();setTab('plan');announce('Saved · '+(trip.changes[0]||'Trip updated.'));
}
$('#setup-form').onsubmit=e=>{e.preventDefault();run(async()=>{
  clearErrors();const d=readForm();
  trip=trip?await api('/api/trips/'+trip.id,'PATCH',{details:d,expectedIntakeRevision:trip.intakeRevision}):await api('/api/trips','POST',d);
  trip.state='awaiting_confirmation';pending=null;render();await refreshList();setTab('plan');announce('Details saved. Review the summary, then confirm to generate.');$('#confirmation').scrollIntoView({behavior:'smooth',block:'start'});
});};
$('#try-demo').onclick=()=>{
  fillForm({destination:'Lisbon, Portugal',timeZone:'Europe/Lisbon',startDate:'2027-04-12',endDate:'2027-04-14',travelers:2,currency:'EUR',budgetMinor:90000,interests:['Food','culture','nature'],pace:'relaxed',transport:'public transit',accessibility:'',dietary:'',budgetIncludes:['activities','meals','local transport']});
  $('#setup').open=true;announce('Sample details filled. Review or edit them, then choose Review trip details.');$('#setup-form').scrollIntoView({behavior:'smooth',block:'start'});
};
$('#chat-form').onsubmit=e=>{e.preventDefault();run(async()=>{
  const input=$('#chat-input'), message=input.value.trim();if(!message)return;
  if(trip?.itinerary && /cheap|budget|replace|swap|break|rest|relax/i.test(message) && !/visa|book|pay|safe|medical|ignore|key/i.test(message)){
    await mutation('revise',{request:message,expectedRevision:trip.itinerary.revision});
  }else if(trip){trip=await api(`/api/trips/${trip.id}/messages`,'POST',{message});fillForm(trip.details);render();announce('Reply received. Review any updated trip details.');}
  else{
    const result=await api('/api/intake','POST',{message});
    draftMessages.push({role:'user',text:message},{role:'assistant',text:result.reply});
    const f=$('#setup-form').elements;for(const [k,v] of Object.entries(result.fields)){if(f[k])f[k].value=Array.isArray(v)?v.join(', '):v;}
    renderMessages();announce('Trip details updated from your message. Please review the form.');
  }
  input.value='';
});};
$('#saved-trips').onchange=()=>run(async()=>{const id=$('#saved-trips').value;if(!id)return;trip=await api('/api/trips/'+id);draftMessages=[{role:'assistant',text:initialMessage}];pending=null;fillForm(trip.details);render();announce('Saved trip restored.');if(trip.itinerary)setTab('plan');});
$('#new-trip').onclick=()=>{if(busy)return;trip=null;pending=null;draftMessages=[{role:'assistant',text:initialMessage}];$('#setup-form').reset();$('#saved-trips').value='';render();setTab('chat');announce('Ready for a new trip. Your previous trips are saved.');};
$('#save-trip').onclick=()=>run(async()=>{await refreshList();announce('Saved. Every successful change is stored automatically for this browser session.');});
$('#print-trip').onclick=()=>window.print();
async function confirmDeletion(all){
  const dialog=$('#confirm-delete');$('#delete-title').textContent=all?'Delete all your session data?':'Delete this trip?';dialog.showModal();
  return new Promise(resolve=>dialog.addEventListener('close',()=>resolve(dialog.returnValue==='delete'),{once:true}));
}
async function editValue(title,label,value,hint){
  const dialog=$('#edit-dialog');$('#edit-title').textContent=title;$('#edit-label').firstChild.textContent=label;$('#edit-value').value=value;$('#edit-hint').textContent=hint;
  // run() disables the workspace while submitting; dialog controls remain usable.
  dialog.querySelectorAll('button').forEach(b=>b.disabled=false);dialog.showModal();$('#edit-value').focus();
  return new Promise(resolve=>dialog.addEventListener('close',()=>resolve(dialog.returnValue==='save'?$('#edit-value').value:null),{once:true}));
}
$('#delete-trip').onclick=async()=>{if(!await confirmDeletion(false))return;run(async()=>{await api('/api/trips/'+trip.id,'DELETE');trip=null;pending=null;render();await refreshList();announce('Trip and related records deleted.');});};
$('#delete-session').onclick=async()=>{if(!await confirmDeletion(true))return;run(async()=>{await api('/api/session','DELETE');trip=null;pending=null;draftMessages=[{role:'assistant',text:initialMessage}];$('#setup-form').reset();await api('/api/session','POST',{});render();await refreshList();announce('All previous session data deleted. A fresh anonymous session is ready.');});};
$$('[data-tab]').forEach(b=>b.onclick=()=>setTab(b.dataset.tab));
run(async()=>{const session=await api('/api/session','POST',{});if(session.storage?.temporary){$('#storage-notice').textContent=session.storage.notice;$('#storage-notice').hidden=false;}await refreshList();if(trips.length){trip=trips[0];fillForm(trip.details);}render();announce(trip?'Restored your most recent saved trip.':'Demo ready. No API keys or external services required.');});
