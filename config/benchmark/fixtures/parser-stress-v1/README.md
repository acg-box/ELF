# Parser stress fixture v1

Six controlled synthetic PDFs contain 12 pages and 30 diagnostic questions.
All pages were rendered and visually reviewed before paid answer calls. The
checked-in PDF hashes and oracle are the frozen test inputs. Do not tune the
parser or exclude questions after inspecting its answers.

| Category | Documents | Pages | Questions | Features |
| --- | ---: | ---: | ---: | --- |
| Mixed | 2 | 6 | 10 | Digital page, full scan, live header over scanned body |
| Chinese | 2 | 2 | 10 | Digital and scanned simplified Chinese, names and conditions |
| Table | 2 | 4 | 10 | Spanning headers, merged region cells, continuation, dated footnote |

There are 24 supported questions, six absent-fact questions, and 58 key spans.
The scans use 180 DPI, 0.35-degree rotation, and slight blur. They are clean
synthetic scans, not handwriting, photographs, or damaged real-world documents.
The two table documents have related layouts with different values. This small
fixture cannot establish statistical significance or a general product ranking.

## Free extraction

`scripts/benchmark_deep/page_ocr.py` visits every page in numeric order.
Poppler `pdftotext -layout` handles text pages. Tesseract handles a page when
the extracted text is empty, contains the replacement character, or raster
images cover at least 20% of the page. The image threshold catches a scanned
body beneath a valid text header. Raster pages are rendered at 300 DPI and
processed with `eng+chi_sim` and page segmentation mode 3. Each output records
the decision, text, hashes, and tool versions.

This is a heuristic baseline. A small embedded scan can fall below the threshold;
a large decorative image can trigger unnecessary OCR. Displayed image areas
are summed, so overlap can overestimate coverage. A triggered page uses its
OCR text in full, without merging Poppler text or correcting names. Packaged
Tesseract models are used; this is not an evaluation of every free OCR model.
`--languages` exposes Tesseract's language selection; the frozen primary run
uses `eng+chi_sim`.

Build the parent image from `docker/benchmark/http.Dockerfile` if it is absent.
Run the following from the repository root with an existing writable `RUN`
directory. These operations do not install tools on the host.

```sh
docker build -t elf-parser-stress:task -f config/benchmark/fixtures/parser-stress-v1/Parser.Dockerfile .
docker run --rm -v "$PWD:/repo:ro" -v "$RUN:/experiment" -w /repo \
  elf-parser-stress:task /usr/bin/python3 scripts/benchmark_deep/page_ocr.py \
  --fixture-root config/benchmark/fixtures/parser-stress-v1 --output /experiment/free
```

`generate.py` creates the fixture with ReportLab and WenQuanYi Zen Hei. Use
`/usr/bin/python3` inside the parser image to access its packaged dependencies.
Do not regenerate frozen PDFs during a resumed comparison. Changing a PDF
requires a new fixture version.

## Matched comparison

Use `cargo make benchmark-document-ocr` with this directory as `--fixture-root`
to obtain Mistral annotations. Use `cargo make benchmark-ragflow-parsers` with
the same `--fixture-root` and run directory to test all three conditions.
The native runner requires the existing private RAGFlow Docker stack and
tokenizer/reranker sidecar. Run it through `cargo make benchmark-budget` with
the existing cumulative ledger and its USD 20 ceiling. Never put provider
credentials in the Docker stack.

DeepDOC receives the original PDFs. Free and Mistral conditions receive plain
text, so downstream chunking and PDF-coordinate support also differ. Both a
shared reader after retrieval and native RAGFlow chat answer all 30 questions.
The original OCR annotations, free page receipts, native chunks, and all answer
attempts must be retained. Key-span retention measures presence of selected
values, not full character error rate or table reconstruction accuracy.

## Output-limit profiles

The legacy runner and budget gateway default to 8,192 output tokens. For a
provider-maximum run, first obtain the model's current context and completion
limits from its provider catalog. Use a new artifact directory. Pass the same
completion limit as `--chat-max-tokens` to the budget gateway and
`--max-output-tokens` to the parser runner. Pass the catalog context limit as
`--model-context-tokens`. The gateway records the effective output limit in
each paid chat receipt and reserves the full possible charge before sending.
The cumulative monetary ceiling still applies. Use `--workers 1` when concurrent
worst-case reservations cannot fit the remaining budget. `--request-timeout`
controls the gateway transport timeout, not the token budget; retain failed or
uncertain requests in the ledger.

For the 2026-10-10 run, the catalog reported 943,718 completion tokens and a
1,048,576-token context. These are a dated snapshot, not permanent defaults.
A matched rerun can reuse the private auth, dataset-state, and parser-output
files from the original artifact directory while the owned runtime is alive.
Use fresh chat and case files. Do not copy completed case files into the new
profile or replace the old protocol. The formal capability run also passes
`--reasoning-effort max` to both the gateway and runner. It uses the highest
available reasoning setting and provider output limit. The original low-effort
run is a separate cohort; the comparison changes two settings and cannot
isolate which setting caused a difference. A single sample does not establish
the best result across repeated generations.
