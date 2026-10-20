"""Read-only conversation export, without grades or evaluation evidence."""
import sqlite3,json,re,html
from pathlib import Path
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'exports/conversaciones_ansiedad';OUT.mkdir(parents=True,exist_ok=True)
c=sqlite3.connect((ROOT/'.evalia-private/luna_ui/application.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
rows=c.execute('''select e.id experiment,e.scenario_snapshot_json,s.code,s.title,s.category,m.name model,t.turn_number,t.user_message,r.response_text,r.id response_id
from experiments e join scenarios s on s.id=e.scenario_id join responses r on r.experiment_id=e.id
join ai_models m on m.id=r.ai_model_id join conversation_turns t on t.id=r.turn_id
order by e.id,m.id,t.turn_number,r.id''').fetchall();c.close()
groups=defaultdict(list)
for r in rows:
 r=dict(r);snap=json.loads(r.pop('scenario_snapshot_json')or'{}')
 category=snap.get('category',r['category'])
 if 'ansiedad' not in category.lower() and not r['code'].startswith('ANS-'):continue
 r['title']=snap.get('title',r['title']);r['code']=snap.get('scenario',r['code'])
 turns=snap.get('turns',[])
 if r['turn_number']<=len(turns):
  current=turns[r['turn_number']-1];r['user_message']=current.get('user',current.get('user_message',r['user_message']))
 groups[r['experiment']].append(r)
assert groups
fontdir=Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Transcript',str(fontdir/'arial.ttf')))
pdfmetrics.registerFont(TTFont('TranscriptBold',str(fontdir/'arialbd.ttf')))
styles=getSampleStyleSheet()
for name in ('Normal','Title','Heading1','Heading2','Heading3'):
 styles[name].fontName='TranscriptBold' if name!='Normal'else'Transcript';styles[name].textColor=colors.black
styles['Normal'].fontSize=10.5;styles['Normal'].leading=14;styles['Normal'].spaceAfter=7
styles['Title'].fontSize=23;styles['Title'].leading=28
styles['Heading1'].fontSize=16;styles['Heading1'].leading=21
styles['Heading2'].fontSize=13;styles['Heading2'].leading=17
styles.add(ParagraphStyle('Role',parent=styles['Normal'],fontName='TranscriptBold',spaceBefore=8,spaceAfter=4,keepWithNext=True))
story=[];source_text=[]
def p(text,style='Normal'):story.append(Paragraph(html.escape(str(text)),styles[style]))
def message(text):
 # Preserve original paragraph breaks, wording and Markdown characters literally.
 for line in text.split('\n'):
  if line:p(line)
  else:story.append(Spacer(1,5))
p('Conversaciones de ansiedad','Title')
p('Mensajes de usuario y respuestas de inteligencia artificial')
p(f'{len(groups)} experimentos y {sum(map(len,groups.values()))} respuestas guardadas. Incluye conversaciones completas y parciales disponibles al momento de la exportación. No contiene evaluaciones ni puntuaciones.')
p('Contenido','Heading1')
for eid,items in groups.items():p(f'Experimento {eid}   {items[0]["code"]}   {items[0]["title"]}')
for eid,items in groups.items():
 story.append(PageBreak());p(f'Experimento {eid}','Heading1');p(items[0]['code']+' '+items[0]['title'])
 previous=None
 for r in items:
  if r['model']!=previous:
   if previous is not None:story.append(PageBreak())
   p(r['model'],'Heading2');previous=r['model']
  p(f'Turno {r["turn_number"]}','Heading3');p('Usuario','Role');message(r['user_message']);p('Respuesta de la IA','Role');message(r['response_text'])
  source_text.extend([r['user_message'],r['response_text']])
def footer(canvas,doc):
 canvas.setFont('Transcript',8);canvas.setFillColor(colors.HexColor('#666666'));canvas.drawString(48,27,'EvalIA   Conversaciones de ansiedad');canvas.drawRightString(564,27,str(doc.page))
path=OUT/'Conversaciones_de_ansiedad.pdf'
SimpleDocTemplate(str(path),pagesize=(612,792),rightMargin=48,leftMargin=48,topMargin=45,bottomMargin=45,title='Conversaciones de ansiedad',author='EvalIA').build(story,onFirstPage=footer,onLaterPages=footer)
(OUT/'export_manifest.json').write_text(json.dumps(dict(experiments=list(groups),responses=sum(map(len,groups.values())),characters=sum(map(len,source_text)),response_ids=[r['response_id']for g in groups.values()for r in g],file=str(path)),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(experiments=len(groups),responses=sum(map(len,groups.values())),file=str(path)),ensure_ascii=False))
