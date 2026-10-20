"""Final external grades, append-only and separate from original evaluations."""
import time
from pathlib import Path
from governed.direct_recovery import connect,digest,context,consolidated

def initialize(database):
 with connect(database) as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS manual_grades(experiment INTEGER,response_id INTEGER,code TEXT,source_hash TEXT,score INTEGER,status TEXT,evaluator TEXT,created REAL,PRIMARY KEY(experiment,response_id,code));
  CREATE TRIGGER IF NOT EXISTS manual_grades_no_update BEFORE UPDATE ON manual_grades BEGIN SELECT RAISE(ABORT,'Final grade is immutable'); END;
  CREATE TRIGGER IF NOT EXISTS manual_grades_no_delete BEFORE DELETE ON manual_grades BEGIN SELECT RAISE(ABORT,'Final grade is immutable'); END;''')

def save(config,database,experiment,response_id,code,value,evaluator):
 if not isinstance(evaluator,str) or not evaluator.strip() or len(evaluator)>200:raise ValueError('Indique el nombre o identificador de la evaluadora')
 if value!='N/A' and (type(value)is not int or value not in range(4)):raise ValueError('Seleccione 0, 1, 2, 3 o N/A')
 initialize(database)
 data=consolidated(config,experiment,database)
 row=next((r for r in data['rows']if r['response_id']==response_id and r['code']==code),None)
 if not row or row['status']in ('SCORED','N/A'):raise ValueError('El indicador ya tiene una calificación definitiva o no existe')
 with connect(config['coordinator'])as c:
  job=c.execute('select status,owner from jobs where experiment=?',(experiment,)).fetchone()
  if job and (job['owner'] or job['status']=='running'):raise ValueError('Espere a que termine la evaluación automática')
 source=digest(dict(response_id=response_id,code=code,sources=context(config,response_id),original_status=row['original_status'],original_score=row['original_score']))
 with connect(database)as c:
  c.execute('BEGIN IMMEDIATE')
  c.execute('insert into manual_grades values(?,?,?,?,?,?,?,?)',(experiment,response_id,code,source,None if value=='N/A'else value,'N/A'if value=='N/A'else'SCORED',evaluator.strip(),time.time()))
 return dict(saved=True,frozen=True)

def mount(main,config,database):
 from fastapi import Request,HTTPException
 import sqlite3
 from urllib.parse import urlsplit
 initialize(database)
 @main.app.post('/api/experiments/{experiment}/manual-grade')
 async def grade(experiment:int,request:Request):
  if request.headers.get('origin') and urlsplit(request.headers['origin']).hostname not in ('127.0.0.1','localhost','::1'):raise HTTPException(403,'Solo evaluación local')
  d=await request.json()
  if d.get('confirmation')!='CONGELAR':raise HTTPException(422,'Confirme la calificación definitiva')
  try:return save(config,database,experiment,int(d['response_id']),str(d['indicator']),d['score'],d.get('evaluator'))
  except (ValueError,KeyError,TypeError,sqlite3.IntegrityError)as e:raise HTTPException(409,str(e))
