(()=>{
 const id=new URLSearchParams(location.search).get('experiment_id');if(!id||id==='72')return;
 const box=document.createElement('aside');box.style.cssText='padding:16px;margin:16px;border:1px solid #b9c8da;background:#f1f6ff';
 async function refresh(){try{const response=await fetch(`/api/experiments/${encodeURIComponent(id)}/hybrid-results`,{cache:'no-store'});if(!response.ok)return;const d=await response.json();if(!d.progress||!Object.keys(d.progress).length)return;if(!box.isConnected)document.body.prepend(box);const s=d.summary.states;
 box.textContent=`Resultados híbridos · ${d.summary.total} indicadores · ${s.SCORED||0} notas · ${s['N/A']||0} N/A · ${s.BLOCKED||0} pendientes de Luna · ${s.EXCEPTION||0} EXCEPTION. Consumo acumulado: US$${d.budget.spent_usd}. Disponible bajo el límite: US$${d.budget.remaining_usd}. Las tablas se actualizan durante la recuperación. Los resúmenes por modelo son promedios descriptivos de turnos disponibles.`;
 if(s.BLOCKED>0)setTimeout(refresh,10000);
 }catch(error){console.error(error)}}refresh();
})();
