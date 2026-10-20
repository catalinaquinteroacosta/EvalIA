/* Read-only presentation of persisted indicators. Never computes a global score. */
function partialRows(payload, model) {
    return (payload.results || []).filter(t => !model || t.model.name === model)
        .flatMap(t => (t.evaluation?.indicators || []).map(i => ({...i,
            model: t.model.name, turn: t.turn_number, response_id: t.response_id,
            review_id: t.evaluation.review_id, evaluation_id: t.evaluation.evaluation_id})));
}
function partialCounts(rows) {
    const c = {SCORED:0, 'N/A':0, BLOCKED:0, pending:0};
    for (const i of rows) c[Object.hasOwn(c,i.status) ? i.status : 'pending']++;
    return c;
}
function renderPartialResults() {
    if (resultsPayload.hybrid_recovery) return renderHybridPartialResults();
    const rows = partialRows(resultsPayload, selectedModelName), c = partialCounts(rows);
    let panel = document.getElementById('partial-results');
    if (!panel) {
        panel = document.createElement('section'); panel.id='partial-results'; panel.className='card';
        document.getElementById('model-tabs').insertAdjacentElement('afterend',panel);
    }
    const families = [...new Set(rows.map(i=>i.criterion_code))].sort();
    const countCells = x => `<td>${x.SCORED}</td><td>${x['N/A']}</td><td>${x.BLOCKED}</td><td>${x.pending}</td>`;
    panel.innerHTML = `<h2>Resultados parciales persistidos · ${escapeHtml(selectedModelName)}</h2>
      <p>Estos son registros por indicador y turno, no una calificación global. BLOCKED requiere revisión; N/A no equivale a cero. Las lecturas completas no eliminan desacuerdos metodológicos.</p>
      <p id="partial-counts"><strong>${c.SCORED} SCORED · ${c['N/A']} N/A · ${c.BLOCKED} BLOCKED · ${c.pending} pendientes</strong> (${rows.length} registros)</p>
      <div style="overflow-x:auto"><table><thead><tr><th>Familia</th><th>SCORED</th><th>N/A</th><th>BLOCKED</th><th>Pendientes</th></tr></thead><tbody>${families.map(f=>`<tr><td>${escapeHtml(f)}</td>${countCells(partialCounts(rows.filter(i=>i.criterion_code===f)))}</tr>`).join('')}</tbody></table></div>
      <details><summary>Ver los ${rows.length} resultados originales por turno, con justificación</summary>
      <div style="overflow-x:auto;max-height:600px"><table><thead><tr><th>Turno</th><th>Familia</th><th>Indicador</th><th>Estado</th><th>Puntuación</th><th>Justificación persistida</th><th>Registro</th></tr></thead><tbody id="partial-indicator-rows">${rows.map(i=>`<tr><td>${Number(i.turn)}</td><td>${escapeHtml(i.criterion_code)}</td><td>${escapeHtml(i.indicator_code)}</td><td>${escapeHtml(i.status || 'Pendiente')}</td><td>${i.status==='SCORED' ? escapeHtml(i.score)+' / 3' : i.status==='N/A' ? 'N/A' : 'Sin puntuación definitiva'}</td><td>${escapeHtml(i.justification || 'Sin justificación publicada; consultar auditoría original.')}</td><td>${i.review_id!=null?'review '+Number(i.review_id):'evaluation '+Number(i.evaluation_id)}</td></tr>`).join('')}</tbody></table></div></details>
      <p>La auditoría y evidencia originales se conservan en la exportación JSON y en la trazabilidad de indicadores. No se han recalculado puntuaciones.</p>`;
    if (String(resultsPayload.experiment?.id)==='108') {
        fetch('/static/derived_108_v1.html', {method: 'HEAD'}).then(response => {
            if (response.ok && panel.isConnected) { const link=document.createElement('p'); link.innerHTML='<a href="/static/derived_108_v1.html">Ver versión derivada v1: 8 correcciones documentadas y 495 BLOCKED pendientes (histórico intacto)</a> · <a href="/static/double_resolution.html">Piloto de doble resolución: resultados y excepciones</a>'; panel.appendChild(link); }
        }).catch(() => {});
    }
    const conversation=resultsPayload.conversation_results.find(t=>t.model.name===selectedModelName);
    if (conversation?.presentation_only) {
        document.getElementById('metric-coverage').textContent=`${c.SCORED} puntuados · ${c['N/A']} N/A · ${c.BLOCKED} bloqueados`;
        document.getElementById('strengths-list').innerHTML='<li>Sin síntesis longitudinal validada. Consulte las puntuaciones individuales y sus justificaciones arriba.</li>';
        document.getElementById('improvements-list').innerHTML='<li>Sin síntesis longitudinal validada. Los desacuerdos pendientes se conservan como BLOCKED.</li>';
        document.getElementById('alerts-list').textContent='Seguridad sin consolidar: la ausencia de una alerta global no certifica ausencia de riesgo. Consulte critical_failure y los indicadores BLOCKED en la auditoría original.';
    }
}
function renderHybridPartialResults() {
    const rows=partialRows(resultsPayload,selectedModelName);
    const valid=rows.filter(r=>['SCORED','N/A'].includes(r.status));
    const missing=rows.filter(r=>!['SCORED','N/A'].includes(r.status));
    let panel=document.getElementById('partial-results');
    if(!panel){panel=document.createElement('section');panel.id='partial-results';panel.className='card';document.getElementById('indicator-traceability-panel').insertAdjacentElement('afterend',panel);}
    panel.innerHTML=`<h2>Calificaciones por indicador · ${escapeHtml(selectedModelName)}</h2><p>${valid.length} decisiones válidas de ${rows.length}. N/A no equivale a cero. Los porcentajes de las familias usan las notas numéricas disponibles.</p>
    <details><summary>Ver calificaciones disponibles</summary><div style="overflow:auto;max-height:600px"><table><thead><tr><th>Turno</th><th>Familia</th><th>Indicador</th><th>Nota</th><th>Justificación</th></tr></thead><tbody>${valid.map(r=>`<tr><td>${Number(r.turn)}</td><td>${escapeHtml(r.criterion_code)}</td><td>${escapeHtml(r.indicator_code)}</td><td>${r.status==='N/A'?'N/A':escapeHtml(r.score)+' / 3'}</td><td>${escapeHtml(r.justification)}</td></tr>`).join('')}</tbody></table></div></details>
    <div id="ungraded-indicators-note"><h3>No calificado: ${missing.length} indicadores</h3><p>Estos indicadores no aparecen en la tabla de calificaciones y no entran en los cálculos. Se conserva su estado técnico en JSON para trazabilidad.</p>${missing.length?'<ul>'+missing.map(r=>`<li>Turno ${Number(r.turn)} · ${escapeHtml(r.indicator_code)} — No calificado. ${escapeHtml(r.justification||'Pendiente de respuesta válida de Luna.')}</li>`).join('')+'</ul>':'<p>Todos los indicadores tienen una decisión válida.</p>'}</div>`;
    renderManualGrading(missing);
}
function renderManualGrading(missing) {
    const note=document.getElementById('ungraded-indicators-note');
    if(!note)return;
    if(!missing.length){note.remove();return;}
    note.style.cssText='margin-top:24px;padding:20px;border:1px solid #354963;border-radius:14px;background:rgba(64,109,164,.08)';
    note.innerHTML=`<h3 style="margin-top:0">Evaluación externa · No evaluado</h3><p class="muted">${missing.length} pendientes en este chat. Al guardar, la nota será definitiva y se integrará a los resultados.</p><div style="overflow:auto"><table><thead><tr><th>Indicador</th><th>Chat</th><th>Turno</th><th>Calificación</th><th></th></tr></thead><tbody>${missing.map((r,index)=>`<tr><td><strong>${escapeHtml(r.indicator_code)}</strong></td><td>${escapeHtml(r.model)}</td><td>${Number(r.turn)}</td><td><select data-manual-score="${index}" style="padding:10px;border-radius:8px"><option value="">Elegir nota</option>${['0','1','2','3','N/A'].map(v=>`<option value="${v}">${v}</option>`).join('')}</select></td><td><button type="button" data-manual-save="${index}" style="padding:10px 16px;border-radius:8px;cursor:pointer">Guardar definitiva</button></td></tr>`).join('')}</tbody></table></div><p id="manual-grade-message" role="status"></p>`;
    for(const button of note.querySelectorAll('[data-manual-save]'))button.addEventListener('click',async()=>{
        const index=Number(button.dataset.manualSave),row=missing[index],value=note.querySelector(`[data-manual-score="${index}"]`).value;
        const message=document.getElementById('manual-grade-message');
        if(!value){message.textContent='Seleccione una nota.';return;}
        if(!confirm(`${row.indicator_code} · ${row.model} · Turno ${row.turn}: ${value}. Esta calificación será definitiva y no podrá modificarse. ¿Guardar?`))return;
        button.disabled=true;message.textContent='Guardando calificación definitiva…';
        try{const response=await fetch(`/api/experiments/${encodeURIComponent(resultsPayload.experiment.id)}/manual-grade`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({response_id:row.response_id,indicator:row.indicator_code,score:value==='N/A'?'N/A':Number(value),evaluator:'Evaluacion externa manual',confirmation:'CONGELAR'})});const data=await response.json();if(!response.ok)throw Error(data.detail||'No se pudo guardar');await loadResults();}
        catch(error){message.textContent=error.message;button.disabled=false;}
    });
}
if (typeof module !== 'undefined') module.exports={partialRows,partialCounts};
