"""Generate controlled layout/OCR fixtures; requires reportlab and Poppler."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageFilter

ROOT = Path(__file__).parent
records = []

def lines(c, text, x, y, width=84):
    c.setFont('Helvetica', 10)
    for line in textwrap.wrap(text, width):
        c.drawString(x, y, line)
        y -= 15
    return y - 12

def header(c, name, page):
    c.setFont('Helvetica-Bold', 16)
    c.drawString(42, 752, name)
    c.setFont('Helvetica', 9)
    c.drawString(42, 730, 'Approved operations manual / controlled synthetic benchmark')
    c.drawString(42, 28, f'{name} | Revision 4 | Page {page}')

def add(case, i):
    name = f'Juniper {case} {i}'
    key = 'e_' + hashlib.sha256(name.encode()).hexdigest()[:24]
    path = ROOT / (key + '.pdf')
    c = canvas.Canvas(str(path), pagesize=(612,792), invariant=1)
    c.setTitle(name)
    header(c,name,1)
    questions=[]
    def ask(lane,q,facts,forbidden=()):
        questions.append(dict(lane=lane,question=f'For {name}, {q}',facts=list(facts),forbidden=list(forbidden)))
    if case in ('table','scan'):
        lines(c,'Regional escalation matrix. Only the approved columns may be used. A dash indicates no published value. The footnote changes the South overflow rule.',42,696)
        xs=[42,124,234,352,465,570]
        ys=[626,596,548,500,452,404]
        c.setFont('Helvetica-Bold',9)
        c.drawString(135,642,'Approved routing');c.drawString(370,642,'Historical - do not use')
        for x in xs:c.line(x,404,x,626)
        for y in ys:c.line(42,y,570,y)
        rows=[['Region','Primary queue','Overflow queue','Old queue','Hours'],
              ['North',f'NORTH-{i}-731',f'NBACK-{i}-428',f'OLDN-{i}-154','4'],
              ['South',f'SOUTH-{i}-862',f'SBACK-{i}-593 *',f'OLDS-{i}-267','12'],
              ['East',f'EAST-{i}-915',f'EBACK-{i}-346',f'OLDE-{i}-782','8'],
              ['West',f'WEST-{i}-624','-',f'OLDW-{i}-853','24']]
        c.setFont('Helvetica',9)
        for y,row in zip([607,573,525,477,429],rows):
            for x,value in zip(xs,row): c.drawString(x+4,y,value)
        lines(c,f'* For the South region, use overflow only after 18:00 UTC. Before that time, use the South primary queue.',42,377)
        lines(c,'The Hours column specifies the response window. It does not specify the overflow activation time.',42,326)
        ask(case+'_row','what is the approved South primary queue?',[f'SOUTH-{i}-862'],[f'OLDS-{i}-267',f'NORTH-{i}-731'])
        ask(case+'_footnote','which South queue applies at 19:00 UTC?',[f'SBACK-{i}-593'],[f'SOUTH-{i}-862'])
        ask(case+'_missing','what is the approved West overflow queue?',[])
    elif case=='columns':
        c.setFont('Helvetica-Bold',12);c.drawString(42,691,'CURRENT - SIGNED');c.drawString(323,691,'ARCHIVED - DO NOT APPLY')
        left=[f'The Atlas migration uses release ALPHA-{i}-472.',f'The Boreal migration uses release BETA-{i}-683.',
              f'An Atlas rollback must first complete inspection CHECK-{i}-925.',
              'These signed instructions override the archived material in the adjacent column.',
              'After inspection, the operator must record the result and notify the service owner.']
        right=[f'An old Atlas draft used release OLD-{i}-351.',f'The old Boreal draft used release STALE-{i}-746.',
               f'The retired Atlas inspection was SKIP-{i}-268.',
               'This column exists for historical reference. It is not authorization for current operations.',
               'Draft values cannot override signed instructions.']
        for x,paras in [(42,left),(323,right)]:
            y=662
            for p in paras:y=lines(c,p,x,y,36)
        c.line(305,345,305,696)
        ask('columns_binding','what is the current signed Atlas release?',[f'ALPHA-{i}-472'],[f'OLD-{i}-351',f'BETA-{i}-683'])
        ask('columns_complete','give both the current Boreal release and the required Atlas rollback inspection.',[f'BETA-{i}-683',f'CHECK-{i}-925'],[f'STALE-{i}-746',f'SKIP-{i}-268'])
        ask('columns_absent','what is the signed launch date?',[])
    else:
        y=690
        for n in range(1,9):
            y=lines(c,f'{n}. Operating requirement: record the request, verify the product identity, and retain the signed receipt. These procedural requirements do not add exceptions to the return policy.',42,y)
        lines(c,'12. Return policy: standard goods have a 7-day limit. The complete exception list has exactly two entries. The first is custom goods, identified by',42,162)
        lines(c,f'CUSTOM-{i}-837. The second exception continues on the next page.',42,99)
        c.showPage();header(c,name,2)
        lines(c,f'12. Return policy (continued): quality defects use DEFECT-{i}-462 and are exempt from the 7-day limit. Both identifiers are required for a complete exception list.',42,690)
        lines(c,f'13. The revised escalation queue is FINAL-{i}-759. Earlier revision 3 used RETIRED-{i}-283, which is no longer valid.',42,615)
        for n in range(14,20):lines(c,f'{n}. Administrative note: keep this record with the signed receipt and make it available to the operations owner.',42,540-(n-14)*62)
        ask('cross_page_list','list the complete two-entry return exception identifiers.',[f'CUSTOM-{i}-837',f'DEFECT-{i}-462'])
        ask('cross_page_revision','what is the revision 4 escalation queue?',[f'FINAL-{i}-759'],[f'RETIRED-{i}-283'])
        ask('cross_page_absent','what is the signed extended-warranty code?',[])
    c.save()
    if case=='scan':
        with tempfile.TemporaryDirectory() as d:
            prefix=Path(d)/'scan'
            subprocess.run([os.environ.get('PDFTOPPM','pdftoppm'),'-scale-to','1500','-gray','-png',str(path),str(prefix)],check=True,stdout=subprocess.DEVNULL)
            c=canvas.Canvas(str(path),pagesize=(612,792),invariant=1)
            for image in sorted(Path(d).glob('scan-*.png')):
                im=Image.open(image).convert('RGB').rotate(0.4,fillcolor='white').filter(ImageFilter.GaussianBlur(0.25))
                c.drawImage(ImageReader(im),0,0,612,792);c.showPage()
            c.save()
    records.append(dict(evidence_id=key,name=name,kind=case,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),questions=questions))

for kind in ('table','columns','crosspage','scan'):
    for i in (range(2,4) if kind == 'scan' else range(2)):add(kind,i)
(ROOT/'oracle-source.json').write_text(json.dumps(records,indent=2)+'\n')
print(f'Generated {len(records)} PDFs / {sum(len(r["questions"]) for r in records)} questions')
