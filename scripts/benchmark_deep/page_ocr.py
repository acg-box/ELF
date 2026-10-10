"""Page-wise Poppler/Tesseract extraction, with explicit raster-page decisions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time


def output(args):
    return subprocess.check_output(args, stderr=subprocess.PIPE).decode('utf-8')


def raster_coverage(listing, page_area):
    """Use Poppler's displayed-image size, not raw pixel count or a PDF parser."""
    area = 0.0
    for line in listing.splitlines():
        fields = line.split()
        if not fields or not fields[0].isdigit() or fields[2] != 'image':
            continue
        width, height = float(fields[3]), float(fields[4])
        x_ppi, y_ppi = float(fields[12]), float(fields[13])
        if x_ppi <= 0 or y_ppi <= 0:
            raise ValueError('Poppler did not provide usable image resolution')
        area += width * height * 72 * 72 / (x_ppi * y_ppi)
    return min(1.0, area / page_area)


def needs_ocr(text, coverage):
    # A large scanned body may coexist with a valid text header on the same page.
    return not text.strip() or coverage >= 0.20 or '\ufffd' in text


def extract(path, languages='eng+chi_sim', dpi=300):
    start = time.monotonic()
    info = output(['pdfinfo', str(path)])
    count = int(re.search(r'^Pages:\s+(\d+)', info, re.M)[1])
    pages = []
    with tempfile.TemporaryDirectory() as directory:
        for page in range(1, count + 1):
            bounds = ['-f', str(page), '-l', str(page)]
            text = output(['pdftotext', *bounds, '-layout', str(path), '-'])
            geometry = output(['pdfinfo', *bounds, '-box', str(path)])
            size = re.search(r'(?:Page\s+\d+ size|Page size):\s+([\d.]+) x ([\d.]+) pts', geometry)
            if not size:
                raise ValueError('Unknown Poppler page-size output')
            area = float(size[1]) * float(size[2])
            coverage = raster_coverage(output(['pdfimages', *bounds, '-list', str(path)]), area)
            mode = 'poppler-layout'
            if needs_ocr(text, coverage):
                mode = 'tesseract-page'
                prefix = str(Path(directory) / f'page-{page}')
                subprocess.run(['pdftoppm', *bounds, '-r', str(dpi), '-singlefile', '-png', str(path), prefix],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                text = output(['tesseract', prefix + '.png', 'stdout', '-l', languages, '--psm', '3'])
            pages.append({'page': page, 'mode': mode, 'raster_coverage': coverage,
                          'text': text.strip(), 'text_sha256': hashlib.sha256(text.strip().encode()).hexdigest()})
    return {'pages': pages, 'text': '\n\n'.join(f'[Page {p["page"]}]\n{p["text"]}' for p in pages),
            'languages': languages, 'dpi': dpi, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'seconds': time.monotonic() - start}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--languages', default='eng+chi_sim')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    versions = {'poppler': subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr,
                'tesseract': output(['tesseract', '--version']),
                'languages': output(['tesseract', '--list-langs'])}
    (args.output / 'versions.json').write_text(json.dumps(versions, indent=2)+'\n')
    for doc in json.loads((args.fixture_root / 'oracle-source.json').read_text()):
        result = extract(args.fixture_root / doc['file'], languages=args.languages)
        if result['source_sha256'] != doc['sha256']:
            raise ValueError('Frozen fixture digest changed')
        (args.output / (doc['evidence_id'] + '.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
        (args.output / (doc['evidence_id'] + '.txt')).write_text(result['text'])
        print(json.dumps({'source': doc['evidence_id'], 'page_modes': [p['mode'] for p in result['pages']],
                          'seconds': result['seconds']}), flush=True)


if __name__ == '__main__':
    main()
