"""Literal source references, resolved without paraphrasing or quote repair."""
import copy
import re


def catalog(request):
    original=request.get('original',{})
    if not all(isinstance(original.get(k),str) for k in ('user','response')):
        return []
    sources=[('user',None,original['user']),('response',None,original['response'])]
    sources.extend(('history',i,row['text']) for i,row in enumerate(original.get('prior_history',[])))
    rows=[]
    for source,index,text in sources:
        chunks=list(dict.fromkeys(part.strip() for line in text.splitlines()
            for part in re.split(r'(?<=[.!?])\s+',line) if part.strip()))
        for quote in chunks:
            rows.append({'quote_index':len(rows),'source':source,'history_index':index,'quote':quote})
    return rows


def schema_with_indices(schema,rows):
    result=copy.deepcopy(schema)
    def visit(node):
        if not isinstance(node,dict):return
        properties=node.get('properties',{})
        if set(properties)=={'source','quote','history_index'}:
            allowed_source=properties['source']['enum']
            allowed_history=properties['history_index'].get('enum',[None])
            indices=[r['quote_index'] for r in rows
                     if r['source'] in allowed_source and r['history_index'] in allowed_history]
            if not indices:raise ValueError('Fuente de evidencia sin fragmentos evaluables')
            del properties['quote']
            properties['quote_index']={'type':'integer','enum':indices}
            node['required']=['source','quote_index','history_index']
        for value in node.values():
            if isinstance(value,dict):visit(value)
            elif isinstance(value,list):
                for item in value:visit(item)
    visit(result)
    return result


def resolve_indices(reading,rows):
    result=copy.deepcopy(reading)
    def visit(node):
        if not isinstance(node,dict):return
        if 'quote_index' in node:
            if set(node)!={'source','quote_index','history_index'}:raise ValueError('Referencia literal mal formada')
            index=node['quote_index']
            if type(index) is not int or not 0<=index<len(rows):raise ValueError('Referencia literal fuera de rango')
            original=rows[index]
            if any(node[k]!=original[k] for k in ('source','history_index')):
                raise ValueError('Referencia literal de otra fuente o turno')
            del node['quote_index']
            node['quote']=original['quote']
        for value in node.values():
            if isinstance(value,dict):visit(value)
            elif isinstance(value,list):
                for item in value:visit(item)
    visit(result)
    return result
