'use strict';
const $ = s => document.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names = {A:'Fixed-size', B:'Theo đoạn', C:'Theo đoạn + filter', D:'Hybrid + reranker', E:'BGE + RRF', F:'E5 đa ngữ dense', G:'E5 + RRF'};
let data, mode = 'live', requestId = 0;
const questions = new Map();
function notice(message='', kind='') { $('#notice').textContent = message; $('#notice').className = message ? `notice ${kind}` : ''; }
async function api(path, options={}) {
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Không kết nối được máy chủ.');
  return value;
}
function view(name) {
  document.querySelectorAll('.view').forEach(el => el.hidden = el.id !== name);
  document.querySelectorAll('.nav').forEach(el => el.classList.toggle('active', el.dataset.view === name));
  $('#breadcrumb').textContent = {explore:'Khám phá tri thức',benchmark:'So sánh benchmark',pipeline:'Pipeline & phương pháp',vietnamese:'Kiểm tra tiếng Việt',multidoc:'Nhiều tài liệu'}[name];
}
function setMode(value) {
  requestId++;
  mode = value;
  $('#live-mode').classList.toggle('active', mode === 'live');
  $('#saved-mode').classList.toggle('active', mode === 'saved');
  $('#saved-controls').hidden = mode !== 'saved';
  $('#live-controls').hidden = mode !== 'live';
  $('#question').readOnly = mode === 'saved';
  $('#search-button').disabled = false;
  $('#search-button').innerHTML = mode === 'saved' ? 'Xem trace đã lưu <span>↗</span>' : 'Tìm bằng chứng <span>↗</span>';
  $('#results-section').hidden = true;
  $('#empty-state').hidden = false;
  notice(mode === 'saved' ? 'Chế độ phát lại kết quả benchmark đã lưu, không chạy model mới.' : 'Truy vấn mới qua model local. Lần đầu có thể cần thời gian nạp hoặc tải model.');
  if (mode === 'saved') syncQuestion();
}
function syncQuestion() { const q = questions.get($('#benchmark-question').value); if(q) $('#question').value = q.question; }
function highlight(text, quote) {
  if (!quote) return esc(text);
  const at = text.indexOf(quote);
  return at < 0 ? esc(text) : esc(text.slice(0,at)) + '<mark>' + esc(quote) + '</mark>' + esc(text.slice(at+quote.length));
}
function render(results, savedQuestion=null,scope='') {
  const target=id=>$('#'+(scope?scope+'-':'')+id);
  target('empty-state').hidden = true;
  target('results-section').hidden = false;
  target('result-mode').textContent = savedQuestion ? (scope==='vi'?'SAVED EXTERNAL TEST · TIẾNG VIỆT':scope==='md'?'SAVED MULTI-DOCUMENT TEST':'SAVED BENCHMARK · KHÔNG PHẢI TRUY VẤN MỚI') : 'LIVE RETRIEVAL · TRUY VẤN MỚI';
  target('gold-panel').hidden = !savedQuestion;
  if (savedQuestion) {
    target('gold-panel').innerHTML = `<strong>${esc(savedQuestion.id.toUpperCase())} · ${esc(savedQuestion.split.toUpperCase())} · Gold evidence</strong><div>Đáp án: ${esc(savedQuestion.expected_answer)}</div><blockquote>${esc(savedQuestion.evidence_quote)}</blockquote><small>Gold ${esc(savedQuestion.gold_source_id)}: ${['nd13','nd69','nd42'].includes(savedQuestion.gold_source_id)?'trang PDF':'unit'} ${esc(savedQuestion.gold_page)} · Filter input: ${esc(JSON.stringify(savedQuestion.filter))} · Hit yêu cầu đủ evidence trong một chunk.</small>`;
  }
  const grid = target('results-grid');
  grid.classList.toggle('single', results.length === 1);
  grid.classList.toggle('four', results.length === 4);
  grid.classList.toggle('many', results.length > 4);
  grid.innerHTML = results.map(r => `<div class="strategy-column strategy-${esc(r.strategy)}"><div class="strategy-heading"><span class="strategy-letter">${esc(r.strategy)}</span><div><strong>${esc(names[r.strategy])}${r.strategy==='D'?(scope?' · cấu hình giữ nguyên':' · bổ sung sau test'):''}</strong><small>${savedQuestion ? `Hit@1: ${r.hit1?'✓':'✕'} · Hit@3: ${r.hit3?'✓':'✕'}` : Object.keys(r.applied_filter).length ? 'Filter: chapter '+esc(r.applied_filter.chapter) : 'Không filter'}</small></div></div>${r.hits.length ? r.hits.map((h,i) => `<article class="hit-card ${h.evidence_hit?'evidence-found':''}"><div class="hit-top"><span>TOP ${i+1}</span><span class="score">${h.score_type==='reranker_logit'?'reranker logit':h.score_type==='rrf_score'?'RRF':'cosine'} ${Number(h.score).toFixed(h.score_type==='rrf_score'?5:3)}</span></div>${h.evidence_hit ? '<span class="evidence-badge">✓ Chứa đủ gold evidence</span>' : ''}<div class="chunk-text">${highlight(h.text,savedQuestion?.evidence_quote)}</div><div class="chunk-meta"><span>${['nd13','nd69','nd42'].includes(h.metadata.document_id)?'Trang PDF':'Unit'} ${esc(h.metadata.page)}</span><span>${h.metadata.chapter?'Chương '+esc(h.metadata.chapter):'Ngôn ngữ '+esc(h.metadata.language)}</span><span>${esc(h.metadata.document_id)}</span><span>${h.text.length} ký tự</span></div><button class="source-button" data-document="${esc(h.metadata.document_id)}" data-page="${Number(h.metadata.page)}" data-start="${Number(h.metadata.start)}" data-end="${Number(h.metadata.end)}">Xem nguồn & vị trí ↗</button></article>`).join('') : '<div class="hit-card muted">Không tìm thấy chunk trong phạm vi đã chọn.</div>'}</div>`).join('');
}
async function search(event) {
  event?.preventDefault();
  if (!data) return;
  const current = ++requestId;
  $('#search-button').disabled = true;
  $('#search-button').textContent = 'Đang truy xuất…';
  $('#results-section').hidden = true;
  notice(mode === 'live' ? 'Đang nạp model và tìm vector trong Qdrant…' : 'Đang đọc trace benchmark…', 'loading');
  try {
    if (mode === 'saved') {
      const question = questions.get($('#benchmark-question').value);
      const rows = await api('/api/traces?id='+encodeURIComponent(question.id));
      if (current !== requestId) return;
      render(rows, question);
      $('#result-query').textContent = question.question;
      $('#result-time').textContent = 'Snapshot · '+new Date(data.run.utc).toLocaleDateString('vi-VN');
      notice('Đang xem trace đã chạy. Màu xanh đánh dấu nguyên văn gold evidence.');
    } else {
      const response = await api('/api/search', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('#question').value,strategy:$('#strategy').value,chapter:$('#chapter').value})});
      if (current !== requestId) return;
      render(response.results);
      $('#result-query').textContent = response.question;
      $('#result-time').textContent = response.elapsed_ms+' ms · gồm rerank nếu chọn D';
      notice('Truy xuất trực tiếp thành công. Cosine/logit là điểm xếp hạng, không phải xác suất đúng. Câu hỏi tự do không có gold để chấm Hit.');
    }
  } catch (error) {
    if (current === requestId) notice(error.message, 'error');
  } finally {
    if (current === requestId) {
      $('#search-button').disabled = false;
      $('#search-button').innerHTML = mode === 'saved' ? 'Xem trace đã lưu <span>↗</span>' : 'Tìm bằng chứng <span>↗</span>';
    }
  }
}
function renderBenchmark() {
  const metrics={...data.metrics,...data.extension_metrics};
  const strategies=data.strategies;
  const ratio = (strategy, split, metric) => { const m=metrics[`${strategy}/${split}`]; return `${m[metric].hits}/${m.n}`; };
  $('#metrics-table').innerHTML = strategies.map(s=>`<tr class="${s===data.selection.strategy?'chosen':''}"><td><strong>${s}</strong> · ${esc(names[s])}${s===data.selection.strategy?' ✓':''}${s==='D'?' (sau test)':''}</td><td>${ratio(s,'dev','hit1')}</td><td>${ratio(s,'dev','hit3')}</td><td>${ratio(s,'test','hit1')}</td><td>${ratio(s,'test','hit3')}</td><td>${data.statistics[s==='D'?'B':s].chunks}</td></tr>`).join('');
  $('#benchmark-bars').innerHTML = strategies.map(s=>`<div class="chart-row"><span class="chart-label"><strong>${s}</strong> · ${esc(names[s])}</span><div class="bar-pair">${['dev','test'].map(split=>`<div class="bar-track"><div class="bar-fill ${split==='test'?'test':''}" style="width:${100*metrics[`${s}/${split}`].hit3.rate}%">${ratio(s,split,'hit3')} · ${Math.round(100*metrics[`${s}/${split}`].hit3.rate)}%</div></div>`).join('')}</div></div>`).join('');
}

function renderHoldout() {
  const metrics=data.extension_metrics;
  $('#holdout-panel').hidden=!metrics['D/holdout'];
  if(!metrics['D/holdout'])return;
  $('#holdout-table').innerHTML=data.strategies.map(s=>{
    const m=metrics[`${s}/holdout`];
    return `<tr><td>${esc(s)} · ${esc(names[s])}</td><td>${m.hit1.hits}/${m.n}</td><td>${m.hit3.hits}/${m.n}</td></tr>`;
  }).join('');
}

document.querySelectorAll('.nav').forEach(button => button.addEventListener('click',()=>view(button.dataset.view)));
$('#live-mode').addEventListener('click',()=>setMode('live'));
$('#saved-mode').addEventListener('click',()=>setMode('saved'));
$('#benchmark-question').addEventListener('change',()=>{requestId++;syncQuestion();$('#results-section').hidden=true;$('#empty-state').hidden=false;$('#search-button').disabled=false;$('#search-button').innerHTML='Xem trace đã lưu <span>↗</span>';notice('Nhấn Xem trace đã lưu để đối chiếu câu hỏi vừa chọn.');});
$('#search-form').addEventListener('submit',search);
document.querySelectorAll('[data-example]').forEach(button=>button.addEventListener('click',()=>{
  if (!data) return;
  view('explore'); setMode('saved'); $('#benchmark-question').value=button.dataset.example; syncQuestion(); search();
}));
async function openSource(event){
  const button = event.target.closest('[data-page]');
  if (!button) return;
  button.disabled=true;
  try {
    const page = await api('/api/page?id='+button.dataset.page+'&document='+encodeURIComponent(button.dataset.document||'alice'));
    $('#source-title').textContent = `${button.dataset.document} · ${['nd13','nd69','nd42'].includes(button.dataset.document)?'Trang PDF':'Unit'} ${page.page}${page.metadata.chapter?' · Chương '+page.metadata.chapter:''}`;
    $('#source-meta').textContent = `${page.metadata.chapter_title} · ${page.text.length} ký tự · offset ${button.dataset.start}–${button.dataset.end}`;
    const start=Number(button.dataset.start), end=Number(button.dataset.end);
    $('#source-text').innerHTML=esc(page.text.slice(0,start))+'<mark>'+esc(page.text.slice(start,end))+'</mark>'+esc(page.text.slice(end));
    const isVi=['nd13','nd69','nd42'].includes(button.dataset.document);
    $('#source-pdf').hidden=!isVi;$('#source-pdf').href='/source/'+encodeURIComponent(button.dataset.document)+'.pdf#page='+page.page;
    $('#source-credit').textContent=isVi?'Nguồn: '+button.dataset.document+' · OCR từ PDF snapshot; đối chiếu scan gốc.':'Nguồn: Project Gutenberg · '+(button.dataset.document==='sherlock'?'Sherlock Holmes':'Alice’s Adventures in Wonderland')+' · Unit ≠ trang in.';
    $('#source-dialog').showModal();
    $('#source-text mark')?.scrollIntoView({block:'center'});
  } catch(error) { if(!$('#vietnamese').hidden){$('#vi-notice').className='notice error';$('#vi-notice').textContent=error.message;}else notice(error.message,'error'); }
  finally {button.disabled=false;}
}
['#results-grid','#vi-results-grid','#md-results-grid'].forEach(id=>$(id).addEventListener('click',openSource));
$('#close-source').addEventListener('click',()=>$('#source-dialog').close());
$('#source-dialog').addEventListener('click',event=>{if(event.target===$('#source-dialog')) {const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}});
function renderVietnamese() {
  if(!data.vietnamese){$('#vi-show').disabled=true;$('#vi-notice').textContent='Chưa có kết quả tiếng Việt. Chạy python -m starter.src.run_vietnamese trước.';return;}
  const v=data.vietnamese;
  $('#vi-metrics-table').innerHTML=['A','B','C','D'].map(s=>{
    const m=v.metrics[`${s}/external_test`];
    return `<tr><td>${s} · ${esc(names[s])}</td><td>${m.hit1.hits}/${m.n}</td><td>${m.hit3.hits}/${m.n}</td><td>${v.statistics[s].chunks}</td></tr>`;
  }).join('');
  $('#vi-question').innerHTML=v.questions.map(q=>`<option value="${esc(q.id)}">${esc(q.id.toUpperCase())} · ${esc(q.question)}</option>`).join('');
}
$('#vi-question').addEventListener('change',()=>{$('#vi-results-section').hidden=true;$('#vi-empty-state').hidden=false;});
$('#vi-show').addEventListener('click',async()=>{
  const button=$('#vi-show');button.disabled=true;$('#vi-question').disabled=true;
  const id=$('#vi-question').value;
  $('#vi-notice').className='notice loading';$('#vi-notice').textContent='Đang đọc trace kiểm tra tiếng Việt…';
  try {
    const rows=await api('/api/vi/traces?id='+encodeURIComponent(id));
    if(id!==$('#vi-question').value)return;
    const q=data.vietnamese.questions.find(q=>q.id===id);
    render(rows,q,'vi');$('#vi-result-query').textContent=q.question;
    $('#vi-result-time').textContent='PDF 2023 · OCR vie';
    $('#vi-notice').className='notice';$('#vi-notice').textContent='Kết quả đã lưu trên nguồn mới, không phải truy vấn mới. Mở nguồn để đối chiếu trang scan.';
  } catch(error){$('#vi-notice').className='notice error';$('#vi-notice').textContent=error.message;}
  finally{button.disabled=false;$('#vi-question').disabled=false;}
});

function renderMultidoc() {
  const m=data.multidoc;
  if(!m){$('#md-show').disabled=true;$('#md-notice').textContent='Chưa có kết quả; chạy python -m starter.src.run_multidoc.';return;}
  const strategies=['C','D','E','F','G'];
  const ratio=(s,split,key)=>{const row=m.metrics[`${s}/${split}`];return `${row[key].hits}/${row.n}`;};
  $('#md-selected').textContent='CHỌN TRÊN DEV: '+m.selection.strategy;
  $('#md-metrics').innerHTML=strategies.map(s=>`<tr class="${s===m.selection.strategy?'chosen':''}"><td>${s} · ${esc(names[s])}</td><td>${ratio(s,'dev','hit1')}</td><td>${ratio(s,'dev','hit3')}</td><td>${ratio(s,'test','hit1')}</td><td>${ratio(s,'test','hit3')}</td><td>${(1000*m.run.mean_retrieval_seconds[s]).toFixed(1)}</td></tr>`).join('');
  $('#md-sources').innerHTML=Object.entries(m.by_source).map(([id,groups])=>{const split=id==='nd69'?'dev':id==='nd13'?'diagnostic':'test';return `<tr><td>${esc(id)} / ${split}</td>${strategies.map(s=>{const r=groups[`${s}/${split}`];return `<td>${r.hit3.hits}/${r.n}</td>`;}).join('')}</tr>`;}).join('');
  $('#md-question').innerHTML=m.questions.map(q=>`<option value="${esc(q.id)}">${esc(q.id)} · ${esc(q.split)} · ${esc(q.kind||'diagnostic')} · ${esc(q.question)}</option>`).join('');
}
$('#md-question').addEventListener('change',()=>{$('#md-results-section').hidden=true;$('#md-empty-state').hidden=false;});
$('#md-show').addEventListener('click',async()=>{
  const button=$('#md-show');button.disabled=true;$('#md-question').disabled=true;
  const id=$('#md-question').value;
  $('#md-notice').className='notice loading';$('#md-notice').textContent='Đang đọc trace đa tài liệu…';
  try{
    const rows=await api('/api/multidoc/traces?id='+encodeURIComponent(id));
    const q=data.multidoc.questions.find(q=>q.id===id);
    render(rows,q,'md');$('#md-result-query').textContent=q.question;
    $('#md-result-time').textContent=q.split==='diagnostic'?'Câu cũ · chỉ diagnostic':'Câu mới · '+q.split;
    $('#md-notice').className='notice';$('#md-notice').textContent='Trace đã lưu trên cùng kho 5 tài liệu. Mở nguồn để đối chiếu PDF hoặc đoạn văn gốc.';
  }catch(error){$('#md-notice').className='notice error';$('#md-notice').textContent=error.message;}
  finally{button.disabled=false;$('#md-question').disabled=false;}
});

async function init() {
  try {
    data=await api('/api/summary');
    for(const q of [...data.questions,...data.holdout_questions])questions.set(q.id,q);
    $('#unit-count').innerHTML=Number(data.manifest.content_units)+' <small>đơn vị</small>';
    $('#benchmark-question').innerHTML=[...data.questions,...data.holdout_questions].map(q=>`<option value="${esc(q.id)}">${esc(q.id.toUpperCase())} · ${esc(q.split)} · ${esc(q.question)}</option>`).join('');
    $('#benchmark-question').value='q17';
    const chapters=[...new Set(data.manifest.pages.map(p=>p.chapter))];
    chapters.forEach(chapter=>{const option=document.createElement('option');option.value=chapter;option.textContent='Chương '+chapter;$('#chapter').append(option);});
    renderBenchmark();
    renderHoldout();
    renderVietnamese();
    renderMultidoc();
    if(data.strategies.includes('D')) {
      $('#compare-option').textContent='So sánh cả A / B / C / D';
      const option=document.createElement('option');option.value='D';option.textContent='D · Hybrid + reranker';$('#strategy').append(option);
    }
    notice(data.live_index_exists?'Sẵn sàng demo. Truy vấn trực tiếp dùng model local; các ví dụ mở trace benchmark đã lưu.':'Chưa có index local. Bạn có thể demo bằng benchmark đã lưu hoặc chạy pipeline để bật truy vấn trực tiếp.');
  } catch(error) {notice('Không tải được dữ liệu: '+error.message,'error');$('#search-button').disabled=true;}
}
init();
