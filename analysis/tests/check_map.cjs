// Run the generated explorer's own JavaScript against light DOM/Leaflet doubles.
// This checks behaviour and score reconciliation without fetching tiles.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..','..','streamlit_app');
const html=fs.readFileSync(path.join(root,'assets/competition_map.html'),'utf8');
const summary=JSON.parse(fs.readFileSync(path.join(root,'assets/analysis_summary.json'),'utf8'));
const script=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{value:'',checked:true,style:{},children:[],
    addEventListener(){},replaceChildren(){this.children=[]},append(x){this.children.push(x)}});return elements.get(id)}
element('view').value='relevant';element('evidence').value='core';
const chain=()=>({addTo(){return this},on(){return this},setView(){return this},fitBounds(){return this},
    clearLayers(){return this},addLayer(){return this},removeLayer(){return this},bindTooltip(){return this},
    bindPopup(){return this},getBounds(){return []}});
const context=vm.createContext({console,document:{getElementById:element,createElement:()=>({style:{}}),querySelectorAll:()=>[]},
    L:{map:chain,tileLayer:chain,control:{layers:chain,scale:chain},layerGroup:chain,divIcon:x=>x,marker:chain,geoJSON:chain,latLngBounds:x=>x},
    setTimeout,URL,Blob});
vm.runInContext(script,context);
const run=s=>vm.runInContext(s,context);
assert.equal(run('stores.length'),summary.party_stores);
run("$('view').value='cma';render()");assert.equal(run('visible.length'),19);
assert.equal(run("visible.filter(s=>category(s)==='both').length"),summary.cma_locations_flagged_core);
run("$('view').value='extra';render()");assert.equal(run('visible.length'),summary.additional_model_flags);
run("$('view').value='all';render()");assert.equal(run('visible.length'),summary.party_stores);
run(`for(const evidence of ['core','inclusive']){
  $('evidence').value=evidence;
  for(const store of stores)for(const method of store.methods){
    const total=grouped(method.catchment_id).reduce((value,group)=>value+group.weight,0);
    const expected=method['weighted_rival_fascias_'+evidence];
    if(expected!==null&&Math.abs(total-expected)>1e-7)throw Error('Map score mismatch: '+method.catchment_id);
    if((counterparts[method.catchment_id]||[]).length!==method.corporate_other_party_stores)throw Error('Overlap mismatch');
  }
}`);
run("$('evidence').value='core';select(stores.find(s=>s.name.includes('Middle Village')))");
assert.equal(run('result(selected)'),'Not flagged');
assert.equal(run("localEvidence(activeCatchment).filter(r=>r.sources.includes('GEO-1010005528')).length"),1);
assert.equal(run('grouped(activeCatchment).reduce((value,group)=>value+group.weight,0).toFixed(1)'),'3.8');
run("select(stores.find(s=>s.id==='CG-103698-0000'))");
assert.equal(run("localEvidence(activeCatchment).filter(r=>r.fascia==='Waitrose').length"),1);
run("focusRival(localEvidence(activeCatchment).find(isCounted).id)");assert(run('highlighted!==null'));
run("select(stores.find(s=>s.methods.length===0))");assert.equal(run('result(selected)'),'Not assessed');
run("$('search').value='no such location xyz';render()");assert.equal(run('visible.length'),0);
assert(!/__STORES__|__RIVALS__|__CATCHMENTS__/.test(html));
console.log('Deployment map checks passed: filters, source resolution, all catchment scores, overlap and empty states.');
