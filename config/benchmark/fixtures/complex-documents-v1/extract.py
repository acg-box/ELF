"""Run a free layout-preserving PDF/OCR baseline inside the parser container."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

root=Path(__file__).parent
rows=json.loads((root/'oracle-source.json').read_text())
receipts=[]
for row in rows:
    start=time.monotonic(); path=root/row['file']
    text=subprocess.check_output(['pdftotext','-layout',str(path),'-']).decode()
    mode='poppler-layout'
    if not text.strip():
        mode='tesseract-5-psm3'
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['pdftoppm','-r','200','-png',str(path),d+'/page'],check=True)
            text='\n\n'.join(subprocess.check_output(['tesseract',str(p),'stdout','--psm','3'],stderr=subprocess.PIPE).decode() for p in sorted(Path(d).glob('*.png')))
    (root/(row['evidence_id']+'.txt')).write_text(text)
    receipts.append({'evidence_id':row['evidence_id'],'mode':mode,'duration_seconds':time.monotonic()-start,'sha256':hashlib.sha256(text.encode()).hexdigest()})
(root/'extraction.json').write_text(json.dumps({'documents':receipts,'poppler':subprocess.run(['pdftotext','-v'],capture_output=True,text=True).stderr,'tesseract':subprocess.check_output(['tesseract','--version']).decode()},indent=2)+'\n')
