// API integration + render smoke; not a browser layout/accessibility test.
// Start the demo first. Usage: node tests/test_demo_ui.cjs [base-url]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const base = process.argv[2] || 'http://127.0.0.1:18763';
const elements = new Map();
function element(selector) {
  if (!elements.has(selector)) elements.set(selector, {
    hidden:false,disabled:false,value:'',textContent:'',innerHTML:'',className:'',
    classList:{toggle(){}},addEventListener(){},append(){},
  });
  return elements.get(selector);
}
(async()=>{
  const get = async path => {const r=await fetch(base+path);assert.equal(r.status,200);return r.json();};
  const summary=await get('/api/summary');
  assert.deepEqual(summary.strategies,['A','B','C','D']);
  assert.equal(summary.holdout_questions.length,10);
  const rows=await get('/api/traces?id=q17');
  assert.deepEqual(rows.map(r=>[r.strategy,r.hit3]),[['A',true],['B',false],['C',false],['D',true]]);
  assert.equal((await get('/api/traces?id=q30')).length,4);
  assert.equal(summary.vietnamese.questions.length,20);
  assert.equal(summary.vietnamese.metrics['D/external_test'].hit3.hits,16);
  const viRows=await get('/api/vi/traces?id=vi10');
  assert.deepEqual(viRows.map(r=>[r.strategy,r.hit3]),[['A',false],['B',true],['C',true],['D',false]]);
  const viPage=await get('/api/page?id=14&document=nd13');
  assert.match(viPage.text,/Việc xóa dữ liệu được thực hiện trong 72 giờ/);
  const pdfResponse=await fetch(base+'/source/nd13.pdf');assert.equal(pdfResponse.status,200);
  assert.equal(pdfResponse.headers.get('content-type'),'application/pdf');
  const pdfBytes=Buffer.from(await pdfResponse.arrayBuffer());
  assert.equal(require('node:crypto').createHash('sha256').update(pdfBytes).digest('hex'),summary.vietnamese.manifest.sha256);

  assert.equal(summary.multidoc.questions.length,65);
  assert.equal(summary.multidoc.metrics['G/test'].hit3.hits,19);
  const mdRows=await get('/api/multidoc/traces?id=m4201');
  assert.deepEqual(mdRows.map(r=>r.strategy),['C','D','E','F','G']);
  for(const source of ['nd69','nd42']) {
    assert((await get('/api/page?id=1&document='+source)).text.length>0);
    const response=await fetch(base+'/source/'+source+'.pdf');assert.equal(response.status,200);
    const manifest=JSON.parse(fs.readFileSync('data/multidoc/'+source+'_manifest.json','utf8'));
    assert.equal(require('node:crypto').createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex'),manifest.sha256);
  }
  assert((await get('/api/page?id=1&document=sherlock')).text.length>0);

  const context=vm.createContext({console,fetch:(path,options)=>fetch(base+path,options),
    document:{querySelector:element,querySelectorAll:()=>[],createElement:()=>({})},
    mdRows,mdQuestion:summary.multidoc.questions.find(q=>q.id==='m4201'),
    viRows,viQuestion:summary.vietnamese.questions.find(q=>q.id==='vi10'),
    savedRows:rows,savedQuestion:summary.questions.find(q=>q.id==='q17')});
  await vm.runInContext(fs.readFileSync('starter/ui/app.js','utf8'),context);
  assert.equal(element('#search-button').disabled,false);
  assert.match(element('#metrics-table').innerHTML,/Hybrid/);
  assert.match(element('#holdout-table').innerHTML,/9\/10/);
  vm.runInContext('render(savedRows,savedQuestion)',context);
  const html=element('#results-grid').innerHTML;
  assert.equal((html.match(/class="strategy-column /g)||[]).length,4);
  assert.match(html,/reranker logit/);
  assert.match(html,/cosine/);
  assert.match(element('#vi-metrics-table').innerHTML,/16\/20/);
  vm.runInContext("render(viRows,viQuestion,'vi')",context);
  assert.match(element('#vi-results-grid').innerHTML,/data-document="nd13"/);
  assert.match(element('#vi-results-grid').innerHTML,/Trang PDF/);
  assert.match(element('#vi-result-mode').textContent,/EXTERNAL TEST/);

  vm.runInContext("render(mdRows,mdQuestion,'md')",context);
  assert.equal((element('#md-results-grid').innerHTML.match(/class="strategy-column /g)||[]).length,5);
  assert.match(element('#md-results-grid').innerHTML,/RRF|rrf/);
  assert.match(element('#md-metrics').innerHTML,/19\/30/);

  const query={question:'What did the cook claim tarts were mostly made of?',strategy:'all',chapter:''};
  const response=await fetch(base+'/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(query)});
  assert.equal(response.status,200);
  const live=await response.json();
  assert.deepEqual(live.results.map(r=>r.strategy),['A','B','C','D']);
  assert.match(live.results[3].hits[0].text,/Pepper, mostly/);
  assert.equal(live.results[3].hits[0].score_type,'reranker_logit');
  const filteredResponse=await fetch(base+'/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...query,strategy:'D',chapter:'XI'})});
  assert.equal(filteredResponse.status,200);
  const filtered=await filteredResponse.json();
  assert(filtered.results[0].hits.every(h=>h.metadata.chapter==='XI'));
  console.log('PASS: A/B/C/D saved/live, Vietnamese traces/metrics/source PDF hash/render labels, multi-document C/D/E/F/G metrics/traces/render, all source routes and PDF hashes, new holdout, score labels, D chapter filter; render smoke only (no visual browser).');
})().catch(error=>{console.error(error);process.exitCode=1;});
