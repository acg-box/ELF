# Complex document fixture v1

Eight synthetic PDF sources contain 24 questions: 16 supported and eight
unsupported. Two independent sources exercise each layout: a ruled routing table
with a footnote and missing cell, adjacent signed and archived columns, clauses
continued across two pages, and an image-only scan of a table. Scan sources have
unique answers, so a digital sibling cannot answer an OCR question.

`oracle-source.json` holds the evaluator's questions and expected values. Only
PDF bytes or extracted source text enter each native product. The adapter gives
RAGFlow the original PDF with an opaque evidence filename. ELF and Hindsight
receive text from Poppler `pdftotext -layout`, with Tesseract `--psm 3` at 200 DPI
for image-only sources. This is a comparison of complete retrieval pipelines,
not a claim that ELF or Hindsight has a built-in PDF parser.

Generate files with `generate.py` using ReportLab, Pillow, and Poppler. Rasterize
scan inputs at 1,500 pixels, rotate 0.4 degrees, and apply a 0.25-pixel Gaussian
blur. No hidden PDF text layer is present in scan inputs. Run `extract.py` in
`Parser.Dockerfile` to obtain the baseline text. Record exact tool versions and
extraction times in `extraction.json`. The committed PDFs and text are the fixed
inputs for measurements; regeneration can change file hashes with tool versions.

The native test command is `cargo make benchmark-deep --workload-group
complex-documents` with the target, manifest, and artifact arguments documented
in the RAGFlow runbook. Execute it inside the cumulative budget gateway. RAGFlow
also requires its native Docker server and `cargo make benchmark-ragflow` to
provision a separate user and embedding model instance.

The fixture is a controlled screening test. It does not cover handwriting,
photographed pages, dense financial statements, charts, multilingual documents,
or large real-world corpora. Compare returned contexts and parsed chunks before
attributing an answer failure to parsing. Do not infer production latency from
AMD64 emulation or from a single small run.
