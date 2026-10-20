'use strict';
(async()=>{
 try{
  const response=await fetch('/api/deployment');if(!response.ok)return;
  const mode=await response.json();if(!mode.temporary_experiments)return;
  const note=document.createElement('aside');note.setAttribute('role','note');
  note.style.cssText='padding:12px 24px;background:#18243a;color:#e3eafb;border-bottom:1px solid #405474;font:14px/1.5 system-ui,sans-serif';
  note.textContent='Los resultados originales son de consulta y se conservan. Los experimentos nuevos son temporales: guarda o descarga los resultados que quieras conservar antes de salir.';
  document.body.prepend(note);
 }catch(_){}
})();
