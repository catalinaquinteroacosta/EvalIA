'use strict';
(async function(){
 const $=id=>document.getElementById(id),fmt=n=>n==null?'—':n.toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2});
 const order=['ChatGPT','Claude','Copilot','Gemini','Perplexity'],colors={ChatGPT:'#42b6f5',Claude:'#ed6d96',Copilot:'#f3a45a',Gemini:'#ebcd6e',Perplexity:'#55c9ca'};
 const node=(tag,text)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;return e;};
 const svgNode=(tag,attrs={},text)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!=null)e.textContent=text;return e;};
 let data,selected='ChatGPT';
 function badge(label){const e=node('span',label);e.className='badge '+(label||'').toLowerCase();return e;}
 function table(id,headers,rows){const t=node('table'),head=node('thead'),tr=node('tr');headers.forEach(h=>{const th=node('th',h);th.scope='col';tr.append(th);});head.append(tr);t.append(head);const b=node('tbody');rows.forEach(row=>{const r=node('tr');row.forEach(value=>{const td=node('td');td.append(value instanceof Node?value:document.createTextNode(String(value)));r.append(td);});b.append(r);});t.append(b);$(id).replaceChildren(t);}
 function chart(id,title,width=800,height=380){const s=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':title});s.append(svgNode('title',{},title));$(id).replaceChildren(s);return s;}
 function text(s,x,y,value,attrs={}){s.append(svgNode('text',{x,y,fill:'#bccbe0','font-size':12,'text-anchor':'middle',...attrs},value));}
 function legend(s,models,y=22){models.forEach((m,i)=>{const x=75+i*140;s.append(svgNode('rect',{x,y:y-10,width:22,height:10,fill:colors[m],opacity:.65}));text(s,x+28,y,m,{'text-anchor':'start','font-size':11});});}
 function bars(id,labels,series){const s=chart(id,'Comparación: '+labels.join(', '),900,390);legend(s,series.map(m=>m.model));const x0=65,y0=310,w=805,h=245;
  for(let v=0;v<=100;v+=20){const y=y0-v*h/100;s.append(svgNode('line',{x1:x0,x2:x0+w,y1:y,y2:y,stroke:'#29394f'}));text(s,53,y+4,v+'%',{'text-anchor':'end'});}
  const step=w/labels.length,bw=Math.min(80,step*.76/series.length);
  labels.forEach((label,i)=>{text(s,x0+step*(i+.5),337,label);series.forEach((m,j)=>{const value=m.values[i];if(value==null)return;const x=x0+step*(i+.5)+(j-series.length/2)*bw,y=y0-value*h/100;const rect=svgNode('rect',{x:x+1,y,width:bw-2,height:value*h/100,fill:colors[m.model],opacity:.65,stroke:colors[m.model]});rect.append(svgNode('title',{},`${m.model} · ${label}: ${fmt(value)} %`));s.append(rect);if(series.length===1)text(s,x+bw/2,y-9,fmt(value)+'%',{fill:'#f8fafc','font-weight':'bold'});});});
 }
 function ranking(g,target='ranking'){const sorted=[...g.models].sort((a,b)=>(b.percentage??-1)-(a.percentage??-1)),s=chart(target,target==='ranking'?'Resultado global por modelo':'Cumplimiento por indicador y modelo',800,390),x0=55,y0=315,h=250,w=720;
  for(let v=0;v<=100;v+=20){const y=y0-v*h/100;s.append(svgNode('line',{x1:x0,x2:x0+w,y1:y,y2:y,stroke:'#29394f'}));text(s,45,y+4,v+'%',{'text-anchor':'end'});}
  sorted.forEach((m,i)=>{const x=x0+i*w/5+30,value=m.percentage;text(s,x+40,342,m.model);if(value==null)return;const y=y0-value*h/100,r=svgNode('rect',{x,y,width:80,height:value*h/100,rx:4,fill:colors[m.model],opacity:.7});r.append(svgNode('title',{},`${m.model}: ${fmt(value)} % · ${m.classification}`));s.append(r);text(s,x+40,y-12,fmt(value)+'%',{fill:'#f8fafc','font-weight':'bold'});});
 }
 function radar(g){const s=chart('radar','Perfil comparativo de las cinco IA por turno',800,390);legend(s,order);const cx=400,cy=210,r=128,point=(i,v)=>[cx+Math.cos(-Math.PI/2+i*2*Math.PI/5)*r*v/100,cy+Math.sin(-Math.PI/2+i*2*Math.PI/5)*r*v/100];
  for(let level=20;level<=100;level+=20){s.append(svgNode('polygon',{points:Array.from({length:5},(_,i)=>point(i,level).join(',')).join(' '),fill:'none',stroke:'#29394f'}));text(s,cx+6,cy-r*level/100+4,level,{'text-anchor':'start','font-size':10});}
  for(let i=0;i<5;i++){const p=point(i,100);s.append(svgNode('line',{x1:cx,y1:cy,x2:p[0],y2:p[1],stroke:'#29394f'}));const l=point(i,123);text(s,l[0],l[1],`Turno ${i+1}`);}
  order.forEach(name=>{const m=g.models.find(m=>m.model===name);if(m.turns.some(t=>t.percentage==null))return;const points=m.turns.map((t,i)=>point(i,t.percentage));s.append(svgNode('polygon',{points:points.map(p=>p.join(',')).join(' '),stroke:colors[name],'stroke-width':2,fill:colors[name],'fill-opacity':.06}));points.forEach((p,i)=>{const c=svgNode('circle',{cx:p[0],cy:p[1],r:3,fill:colors[name]});c.append(svgNode('title',{},`${name} · Turno ${i+1}: ${fmt(m.turns[i].percentage)} %`));s.append(c);});});
 }
 function metrics(g){const m=g.models.find(m=>m.model===selected);$('highlights').replaceChildren(...[['Modelo',m.model,''],['Resultado global',fmt(m.percentage)+' %','Promedio de todos los escenarios'],['Clasificación',m.classification,'Descriptiva del porcentaje agregado'],['Decisiones válidas',`${m.numeric+m.na} de ${m.numeric+m.na+m.pending}`,fmt(m.coverage)+' % · incluye N/A']].map(([label,value,note])=>{const e=node('div');e.className='card metric';e.append(node('span',label),node('strong',value),node('small',note));return e;}));$('models').replaceChildren(...order.map(name=>{const b=node('button',name);b.type='button';b.className=name===selected?'active':'';b.setAttribute('aria-pressed',String(name===selected));b.onclick=()=>{selected=name;metrics(g);};return b;}));}
 function longitudinal(g){const s=chart('longitudinal-chart','Evolución consolidada T1 a T5 de las cinco IA',1000,400),x0=70,y0=320,w=850,h=245;legend(s,order);
  for(let value=0;value<=100;value+=20){const y=y0-value*h/100;s.append(svgNode('line',{x1:x0,x2:x0+w,y1:y,y2:y,stroke:'#29394f'}));text(s,57,y+4,value+'%',{'text-anchor':'end'});}
  for(let i=0;i<5;i++)text(s,x0+i*w/4,y0+28,'T'+(i+1));
  order.forEach(name=>{const m=g.models.find(m=>m.model===name);let prior=null;m.turns.forEach((turn,i)=>{if(turn.percentage==null){prior=null;return;}const p=[x0+i*w/4,y0-turn.percentage*h/100];if(prior)s.append(svgNode('line',{x1:prior[0],y1:prior[1],x2:p[0],y2:p[1],stroke:colors[name],'stroke-width':3}));const c=svgNode('circle',{cx:p[0],cy:p[1],r:5,fill:colors[name]});c.append(svgNode('title',{},`${name} · T${i+1}: ${fmt(turn.percentage)} % · ${turn.n}/${turn.expected} escenarios`));s.append(c);prior=p;});});
  table('safety-table',['Modelo','Alertas de seguridad','Escenarios afectados','Respuestas con alertas','Estado'],order.map(name=>{const m=g.safety.find(m=>m.model===name);return [node('strong',name),m.alerts,`${m.scenarios_affected}/${m.scenarios_total}`,`${m.responses_affected}/${m.responses_total}`,m.complete?'Completo':'Parcial: faltan notas'];}));
  $('safety-details').replaceChildren(...order.map(name=>{const m=g.safety.find(m=>m.model===name),section=node('div');section.append(node('h3',name));if(!m.scenarios.length)section.append(node('p',m.complete?'Sin escenarios con alertas registradas.':'Sin alertas registradas en las respuestas completas; faltan calificaciones.'));const list=node('ul');m.scenarios.forEach(e=>{const li=node('li'),a=node('a',`${e.code}: ${e.alerts} alertas`);a.href=e.url||'/resultados?experiment_id='+e.id;li.append(a);list.append(li);});section.append(list);return section;}));
 }
 function familyBars(families){
  const width=1400,height=540,s=chart('family-chart','Comparación por familia entre las cinco IA',width,height),x0=65,y0=330,w=1310,h=265;legend(s,order);
  for(let v=0;v<=100;v+=20){const y=y0-v*h/100;s.append(svgNode('line',{x1:x0,x2:x0+w,y1:y,y2:y,stroke:'#29394f'}));text(s,54,y+4,v+'%',{'text-anchor':'end'});}
  const step=w/families.length,bw=Math.min(22,step*.8/5);
  families.forEach((family,i)=>{const cx=x0+step*(i+.5);text(s,cx+7,y0+24,family.name,{transform:`rotate(-37 ${cx+7} ${y0+24})`,'text-anchor':'end','font-size':12});
   order.forEach((name,j)=>{const m=family.models.find(m=>m.model===name);if(m.percentage==null)return;const x=cx+(j-2.5)*bw,y=y0-m.percentage*h/100,r=svgNode('rect',{x,y,width:bw-2,height:m.percentage*h/100,fill:colors[name],opacity:.75});r.append(svgNode('title',{},`${family.name} · ${name}: ${fmt(m.percentage)} %`));s.append(r);});});
 }
 function comparisons(g){$('global-description').textContent=`Esta puntuación general considera los ${g.scenarios} escenarios de ${g.title.toLowerCase()} y los cinco turnos de cada conversación. Cada escenario tiene el mismo peso.`;
  const scenarios=data.experiments.filter(e=>g.categories.includes(e.category)),value=(e,name)=>{const local=data.responses.filter(r=>r.experiment===e.id&&r.model===name&&r.percentage!=null);return local.length===5?local.reduce((s,r)=>s+r.percentage,0)/5:null;};
  bars('scenario-chart',scenarios.map(e=>e.code),order.map(model=>({model,values:scenarios.map(e=>value(e,model))})));
  table('scenario-table',['Escenario',...order],scenarios.map(e=>{const a=node('a',e.code+' · '+e.title);a.href=e.url;a.className='scenario-label';return [a,...order.map(name=>fmt(value(e,name))+' %')];}));
  const families=g.family_summaries;
  $('family-description').textContent=`${families.length} familias · cinco modelos · todos los ${g.scenarios} escenarios de la categoría. Cada grupo de barras corresponde a una familia.`;
  familyBars(families);
  table('family-table',['Familia',...order],families.map(f=>{const label=node('div');label.className='indicator-label';label.append(node('strong',f.name),node('small',f.code));return [label,...order.map(name=>{const m=f.models.find(m=>m.model===name),e=node('div');e.append(node('strong',fmt(m.percentage)+' %'),node('small',`${m.scenarios_numeric}/${g.scenarios} escenarios con puntuación`));return e;})];}));
 }
 function render(){const g=data.groups.find(g=>g.id===$('group').value);if(!g)return;history.replaceState(null,'','?grupo='+g.id);$('title').textContent=g.title;$('scope').textContent=`${g.scenarios} escenarios · ${g.scenarios*25} respuestas · cinco turnos por conversación`;metrics(g);radar(g);ranking(g);bars('turn-chart',Array.from({length:5},(_,i)=>'Turno '+(i+1)),order.map(model=>({model,values:g.models.find(m=>m.model===model).turns.map(t=>t.percentage)})));
  table('summary',['Modelo','Resultado global','Clasificación','Cobertura evaluable','Escenarios completos'],[...g.models].sort((a,b)=>(b.percentage??-1)-(a.percentage??-1)).map(m=>[node('strong',m.model),node('strong',fmt(m.percentage)+' %'),badge(m.classification),`${fmt(m.coverage)} % · ${m.numeric+m.na}/${m.numeric+m.na+m.pending} decisiones válidas`,`${m.n_scenarios}/${m.expected_scenarios}`]));
  table('turn-table',['Modelo','T1','T2','T3','T4','T5'],order.map(name=>{const m=g.models.find(m=>m.model===name);return [node('strong',name),...m.turns.map(t=>fmt(t.percentage)+' %')];}));comparisons(g);longitudinal(g);
 }
 try{const response=await fetch('/api/results/global');if(!response.ok){const e=await response.json();throw Error(e.detail||'No se pudieron cargar los resultados.');}data=await response.json();
  $('group').replaceChildren(...data.groups.map(g=>{const o=node('option',g.title);o.value=g.id;return o;}));const requested=new URLSearchParams(location.search).get('grupo');if(data.groups.some(g=>g.id===requested))$('group').value=requested;
  const categories=['ansiedad','depresion','pareja','existencial','social'].map(id=>data.groups.find(g=>g.id===id)),labels=['Ansiedad','Depresión','Pareja','Existencial','Social'];
  table('synthesis-table',['Modelo',...labels],order.map(name=>[node('strong',name),...categories.map(g=>{const m=g.models.find(m=>m.model===name),e=node('div');e.append(node('strong',fmt(m.percentage)+' %'),node('br'),badge(m.classification));return e;})]));
  bars('synthesis-chart',labels,order.map(model=>({model,values:categories.map(g=>g.models.find(m=>m.model===model).percentage)})));
  $('method').replaceChildren(...data.method.map(t=>node('li',t)));$('provenance').textContent=`Banco: ${data.bank} · Captura: ${data.generated_at} · ${data.experiments.length} escenarios. Resultados descriptivos; no son una prueba de superioridad estadística.`;
  $('status').textContent=data.note||'';$('content').hidden=false;$('group').addEventListener('change',render);render();
 }catch(error){$('status').className='error';$('status').textContent=error.message;}
})();
