"""Create six fixed mixed-page, Chinese, and merged-table diagnostic PDFs."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageFilter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).parent
pdfmetrics.registerFont(TTFont('CJK', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', subfontIndex=0))
records = []


def text(c, value, x=42, y=680, size=12, chinese=False):
    c.setFont('CJK' if chinese else 'Helvetica', size)
    c.drawString(x, y, value)


def heading(c, name, page, chinese=False):
    text(c, name, y=752, size=17, chinese=chinese)
    text(c, 'Controlled synthetic parser diagnostic / signed revision 7', y=729, size=9)
    text(c, f'{name} | Revision 7 | Page {page}', y=25, size=9, chinese=chinese)


def raster(c, painter, page_size=(612, 792), destination=(0, 0, 612, 792)):
    with tempfile.TemporaryDirectory() as directory:
        pdf = Path(directory) / 'page.pdf'
        src = canvas.Canvas(str(pdf), pagesize=page_size, invariant=1)
        painter(src)
        src.save()
        subprocess.run(['pdftoppm', '-r', '180', '-singlefile', '-png', str(pdf), directory+'/page'], check=True)
        im = Image.open(directory+'/page.png').convert('RGB').rotate(0.35, fillcolor='white').filter(ImageFilter.GaussianBlur(0.2))
        c.drawImage(ImageReader(im), *destination)


def make(kind, index):
    letter = 'AB'[index]
    name = {'mixed': 'Harbor mixed', 'chinese': '澄江验收', 'table': 'Cedar matrix'}[kind] + ' ' + letter
    identity = 'p_' + hashlib.sha256(name.encode()).hexdigest()[:20]
    path = ROOT / (identity + '.pdf')
    c = canvas.Canvas(str(path), pagesize=(612, 792), invariant=1)
    c.setTitle(name)
    questions, anchors = [], []

    def ask(lane, question, facts, forbidden=()):
        questions.append({'lane': lane, 'question': f'{name}: {question}', 'facts': list(facts), 'forbidden': list(forbidden)})

    def anchor(page, *values):
        anchors.extend({'page': page, 'text': value} for value in values)

    if kind == 'mixed':
        day, night, signed = f'DAY-{letter}-731', f'NIGHT-{letter}-864', f'SIGN-{letter}-529'
        person = ['Clara Lin', 'Nolan Wu'][index]
        deadline = ['2026-11-17', '2026-11-23'][index]
        heading(c, name, 1)
        for y, value in [(682, 'Signed dispatch policy. Pages 2 and 3 contain scanned operational records.'),
                         (645, f'Day dispatch queue: {day}.'),
                         (609, 'The day queue applies before 18:00 UTC.'),
                         (573, 'At and after 18:00 UTC, use the night queue on page 2.'),
                         (537, f'Retired queue OLD-{letter}-114 is not approved.'),
                         (501, 'The approval code and deadline are on the signed image on page 3.')]:
            text(c, value, y=y, size=11)
        anchor(1, day, f'OLD-{letter}-114', '18:00 UTC')
        c.showPage()

        def night_page(p):
            heading(p, name, 2)
            for y, value in [(680, 'NIGHT DISPATCH - SIGNED SCAN'), (625, f'Night dispatch queue: {night}.'),
                             (570, f'On-duty dispatcher: {person}.'), (515, 'Effective at and after 18:00 UTC.'),
                             (460, 'This signed record overrides the retired day-only draft.')]:
                text(p, value, y=y, size=14)
        raster(c, night_page)
        anchor(2, night, person, 'NIGHT DISPATCH')
        c.showPage()
        heading(c, name, 3)
        text(c, 'The title is real PDF text; the signed body below is a raster image.', y=705, size=10)

        def signed_body(p):
            for y, value in [(550, 'SIGNED APPROVAL RECORD'), (485, f'Approval code: {signed}.'),
                             (420, f'Approved deadline: {deadline}.'), (355, 'Only the approval code above authorizes execution.'),
                             (290, 'Previous unsigned drafts do not authorize deployment.')]:
                text(p, value, y=y, size=14)
        raster(c, signed_body, (612, 620), (0, 60, 612, 620))
        anchor(3, signed, deadline, 'SIGNED APPROVAL RECORD')
        ask('mixed_scan_page', 'Which queue applies at 19:00 UTC?', [night], [day])
        ask('mixed_image_body', 'What is the signed approval code?', [signed])
        ask('mixed_scan_name', 'Who is the on-duty dispatcher?', [person])
        ask('mixed_cross_page', 'Give the day dispatch queue and the approved deadline.', [day, deadline])
        ask('mixed_absent', 'What is the published dispatcher phone number?', [])
        pages = 3
    elif kind == 'chinese':
        owner, alternate = [('林悦', '陈浩'), ('周宁', '许岚')][index]
        budget, urgent, normal = [(4800, 24, 72), (6200, 36, 96)][index]
        place = ['上海市浦东新区', '苏州市工业园区'][index]

        def chinese_page(p):
            heading(p, name, 1, chinese=True)
            lines = ['工程验收通知（正式签署版）', f'当前负责人：{owner}', f'备用负责人：{alternate}（仅在负责人请假时代理）',
                     f'预算上限：人民币 {budget} 元', f'验收地点：{place}',
                     f'紧急事项处理时限：{urgent} 小时', f'普通事项处理时限：{normal} 小时',
                     '紧急事项与普通事项适用不同处理时限，请勿混用。', '本通知未公布联系电话。']
            for n, value in enumerate(lines):
                text(p, value, y=677-n*49, size=16, chinese=True)
        if index:
            raster(c, chinese_page)
        else:
            chinese_page(c)
        anchor(1, owner, alternate, str(budget), place, str(urgent), str(normal), '工程验收通知', '紧急事项')
        ask('chinese_name', '当前负责人是谁？请只给姓名。', [owner], [alternate])
        ask('chinese_amount', '人民币预算上限是多少？请只给数字。', [str(budget)])
        ask('chinese_place', '验收地点在哪里？', [place])
        ask('chinese_condition', '紧急事项的处理时限是多少小时？请只给数字。', [str(urgent)], [str(normal)])
        ask('chinese_absent', '负责人的联系电话是什么？未提供则回答 unknown。', [])
        pages = 1
    else:
        offset = index * 1000
        east, west_enterprise, revised = str(420+offset), str(930+offset), str(680+offset)
        xs = [42, 123, 223, 324, 405, 486, 570]

        def table_header(p, page):
            heading(p, name, page)
            text(p, 'Current signed values apply. Archived fees are historical references only.', y=703, size=10)
            for x in xs:
                p.line(x, 618, x, 681)
            for y in [618, 649, 681]:
                p.line(xs[0], y, xs[-1], y)
            # Remove the divider through the spanning Current signed header.
            p.setStrokeColorRGB(1, 1, 1);p.setLineWidth(2);p.line(xs[3], 651, xs[3], 679)
            p.setStrokeColorRGB(0, 0, 0);p.setLineWidth(1)
            for x, value in [(xs[0]+5, 'Region'), (xs[1]+5, 'Tier'), (xs[2]+17, 'Current signed'), (xs[4]+5, 'Archived'), (xs[5]+5, 'State')]:
                text(p, value, x=x, y=660, size=10)
            for x, value in [(xs[2]+5, 'Fee (CNY)'), (xs[3]+5, 'Limit'), (xs[4]+5, 'Old fee')]:
                text(p, value, x=x, y=629, size=10)

        def row(p, y, values, break_region=True):
            for x in xs:
                p.line(x, y-47, x, y)
            p.line(xs[0] if break_region else xs[1], y-47, xs[-1], y-47)
            for x, value in zip(xs, values):
                text(p, str(value), x=x+5, y=y-28, size=10)

        def first(p):
            table_header(p, 1)
            row(p, 618, ['East', 'Basic', 210+offset, 4, 21+offset, 'Signed'], False)
            row(p, 571, ['', 'Pro', 420+offset, 8, 42+offset, 'Signed'])
            row(p, 524, ['West', 'Basic', 310+offset, 6, 31+offset, 'Signed'], False)
            row(p, 477, ['', 'Pro *', 620+offset, 12, 62+offset, 'Signed'])
            text(p, 'The West region continues on page 2 with its Enterprise tier.', y=388, size=11)
            text(p, '* The dated fee adjustment is on page 2. Limits do not change.', y=351, size=11)
        def second(p):
            table_header(p, 2)
            text(p, 'Continuation: the first row below belongs to West.', y=590, size=11)
            row(p, 570, ['West', 'Enterprise', 930+offset, 18, 93+offset, 'Signed'])
            row(p, 523, ['South', 'Basic', 410+offset, 7, 41+offset, 'Draft'], False)
            row(p, 476, ['', 'Pro', 820+offset, 14, 82+offset, 'Draft'])
            text(p, f'* From 2026-11-01, West Pro uses fee {revised} CNY instead of {620+offset} CNY.', y=370, size=11)
            text(p, 'Its limit remains 12. This dated note overrides the main table fee.', y=335, size=11)
            text(p, 'Draft rows are not approved. No bank-routing number is published.', y=300, size=11)
        for n, painter in enumerate([first, second]):
            if n:
                c.showPage()
            raster(c, painter) if index else painter(c)
        anchor(1, 'Current signed', 'Fee (CNY)', 'Archived', east, str(42+offset), str(620+offset))
        anchor(2, 'Enterprise', west_enterprise, revised, '2026-11-01', 'Draft', 'limit remains 12')
        ask('table_merged_header', 'What is the current signed East Pro fee in CNY before the dated adjustment? Return the number only.', [east], [str(42+offset)])
        ask('table_merged_region', 'What is the current signed East Pro limit? Return the number only.', ['8'])
        ask('table_continuation', 'What is the signed West Enterprise fee in CNY? Return the number only.', [west_enterprise], [str(93+offset)])
        ask('table_footnote', 'What West Pro fee in CNY applies on 2026-11-02? Return the number only.', [revised], [str(620+offset)])
        ask('table_absent', 'What is the published bank-routing number?', [])
        pages = 2
    c.save()
    records.append({'evidence_id': identity, 'name': name, 'kind': kind, 'file': path.name, 'pages': pages,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'anchors': anchors, 'questions': questions})


for kind in ['mixed', 'chinese', 'table']:
    for index in range(2):
        make(kind, index)
(ROOT / 'oracle-source.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'documents': len(records), 'pages': sum(d['pages'] for d in records),
                  'questions': sum(len(d['questions']) for d in records)}))
