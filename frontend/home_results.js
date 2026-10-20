'use strict';
(async function(){
 const select=document.getElementById('result-choice'),status=document.getElementById('result-status');
 try{const response=await fetch('/api/results/catalog');if(!response.ok)throw Error('No fue posible cargar el catálogo.');const data=await response.json();
  for(const [label,items] of [['Resultados globales',data.groups],['Resultados por escenario',data.experiments]]){
   const group=document.createElement('optgroup');group.label=label;
   for(const item of items){const option=document.createElement('option');option.value=item.url;option.textContent=item.code?`${item.code} · ${item.title}`:item.title;group.append(option);}select.append(group);
  }status.textContent=`${data.experiments.length} escenarios disponibles y siete comparaciones globales.`;
 }catch(error){status.textContent=error.message;}
 document.getElementById('result-form').addEventListener('submit',event=>{event.preventDefault();if(select.value)location.href=select.value;});
})();
