# Project report — ENTROPY: Ransomware Shield

Technical project report describing the ENTROPY ransomware-defence system:
entropy-based detection, campaign escalation, verified containment,
hash-verified recovery and auditable (blockchain) response.

| Artefact | What it is |
|----------|------------|
| `ENTROPY_Project_Report.docx` | The report — A4, ~20 pages, 9 chapters, 8 figures, 10 tables |
| `report_content.py` | All report text and the exhibit definitions (edit the report here) |
| `build_report.py` | Renders the content module to Word, with page estimation for the contents page |
| `figures/make_figures.py` | Regenerates every figure deterministically with matplotlib |
| `figures/*.png` | The rendered figures at 300 dpi (print quality) |

## Rebuilding

```bash
pip install python-docx matplotlib pillow

python report/figures/make_figures.py   # regenerate all figures
python report/build_report.py           # rebuild the .docx
```

`build_report.py` prints its own layout estimate, for example:

```
estimated length : 23 pages (title 1 + contents 1 + body 21)
chapter start pages:
  p.  3  1. Introduction
  p.  5  2. Background and Design Rationale
  ...
```

The estimate is deliberately conservative (it assumes ~100 characters per
line and never splits a table or figure across a page), so the document as
rendered by Word is typically one to two pages shorter than the printed
estimate.

## Editing the report

The report is written as a flat list of blocks in `report_content.py`:

```python
("h1", "1. Introduction")                      # chapter — starts a new page
("h2", "1.1 Motivation")                       # section
("p", "Body paragraph ...")                    # paragraph
("bullets", ["item one", "item two"])          # bullet list
("numbers", ["item one"])                      # numbered list
("refs", ["Author, Title, Venue, Year."])      # hanging-indent reference list
("table", {"caption": ..., "header": [...], "rows": [[...]], "widths": [...]})
("figure", {"path": "figures/fig01_....png", "caption": ..., "width_in": 6.4})
("code", "listing text with \n line breaks")
```

Add, remove or reorder blocks and rebuild — the contents page, page numbers
and the length estimate are recomputed automatically.

## Filling in the title page

The title page carries placeholders in square brackets for the submitter:
student/team names, roll numbers, department, institution, guide, academic
year and submission date. Replace them in the rendered document (or in
`build_report.py` → `render_title_page`).

## Numbers in the report

Every figure and table in the report is derived from the repository's own
measurements, which can be regenerated end to end:

```bash
python -m benchmark                     # detection battery (8 attacks x seeds + 7 workloads)
python -m benchmark.recovery_drill      # byte-for-byte recovery and RTO
python -m benchmark.exchange_simulation # four-tenant federated sharing
python -m ai.train_rf                   # optional Random Forest retrain
```

The results quoted in Chapters 6 and 7 are the measured values recorded in
`docs/`; the image blind spot, the Random Forest false quarantines and the
no-baseline recovery losses are reported as limitations rather than omitted.

## Note on figures

`figures/make_figures.py` also produces four alternates that are not used by
the current page budget — `fig06_restore_states.png`,
`fig09_workloads.png`, `fig11_latency.png` and `fig12_defence_layers.png`.
They illustrate material now covered in text and can be re-inserted by
adding the corresponding `("figure", {...})` block if the report is allowed
to grow.
