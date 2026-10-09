# Executable workbench for stages 3–5

These commands perform local mechanics and expose unfinished work. They never generate academic content, silently translate, call an AI provider, or publish. Keep their artifacts outside the two-file ZIP.

## 3. Prepare and recover actual source

```sh
python3 <skill>/scripts/source_workbench.py prepare \
  --pdf /absolute/path/slides.pdf --source-id material-id \
  --pages all --out /work/new-source-workspace
```

Requires local `pdfinfo` and `pdftoppm`. It inventories the entire PDF, hashes the original bytes, renders the requested physical pages, and creates `source.json` plus `extraction-draft.json` with all pages **pending**. `--pages 12-18` limits renders, not the source inventory or proof of coverage. With `pdftotext` it stores unverified raw text; if absent, `--text-python /path/to/local/python-with-pdfplumber` can extract text locally. Otherwise it explicitly reports unavailable text extraction while still rendering. No dependency is installed by the script.

Inspect every relevant full-page PNG. Author `blocks` with `kind` (`text`, `table`, `figure`, `diagram`, `code`, `formula`) and `content`, preserving qualifiers, conditions, labels, relationships and units. Write a distinct `page_note` explaining the teaching contribution. Preserve `raw_text` unchanged; it is not verified extraction. Use `page` for the one-based **physical PDF page** and optional `page_label` for its printed slide number. Never substitute a printed footer for a PDF source locator.

For a difficult region:

```sh
python3 <skill>/scripts/source_workbench.py recover \
  --workspace /work/new-source-workspace --page 14 --dpi 300 \
  --crop 120 240 900 600 --ocr-language vie+eng \
  --out /work/new-recovery-attempt
```

Crop coordinates refer to rendered pixels at the selected DPI; outside-page regions fail. The command saves the full-page render, crop and hashed `attempt.json`. OCR is optional and marked unverified. Missing Tesseract is reported with the next dependency action. The command checks the original PDF SHA before and after work and rejects changed sources or existing output directories.

Compare the result visually; write the recovered fact and verification in the review evidence. If still ambiguous, keep the gap open, record what each attempt actually achieved and request the specific source/lecturer clarification. Do not infer resolution from command success. See [recovery.md](recovery.md).

## 4. Build learning units and context-specific banks

Create units from independently teachable/checkable goals, not page quotas. For each unit, record source windows, KC IDs and prerequisite IDs in `authoring-context.v1`. One unit can span pages, and one KC can recur in several units. Preserve a capability/assessment-intent rationale in coverage; a tag match alone is insufficient.

Author native bilingual `kc.json` and `quiz.json`, including the full slot/variant graph. Annotate each question's unit owners and required prior knowledge. Run `context_plan.py` before selecting a session. A candidate is not a final set: choose across assessment intents/slots, avoid equivalent variants in one round, and solve the selected questions. If the candidate pool is short, author a genuinely new in-scope question or report the shortfall. A context plan does not modify a bank or prove source interpretation.

## 5. Create revision-bound review records

```sh
python3 <skill>/scripts/authoring_evidence.py init \
  --kc /work/day/kc.json --quiz /work/day/quiz.json \
  --context /work/day/authoring-context.json \
  --extraction /work/day/extraction.json --evidence /work/day/review.json
```

This creates **pending** records, not pre-approved checkmarks. It never overwrites an existing file. `extraction.json` follows `source-extraction.v1` from the workbench: combine source inventories/pages if there are multiple PDFs. Inventory every physical page; explicitly explain excluded pages rather than deleting them. Source hashes bind to the actual PDFs inventoried by the workbench.

Populate these records with actual work:

- `reviewer`, `reviewed_at`: actual author/reviewer and ISO date/time; helper output is `self_review` only.
- `source_recovery`: gap IDs, physical source/page, missing fact, attempts (`method`, `artifact`, `result`), recovery state and impact IDs. A recovered record needs `recovered_fact` plus `verification`. Open gaps must match `context.open_source_gaps` exactly in IDs and impact. Existing work can continue around an open gap, but the complete-bank report stays blocked.
- `coverage`: every KC's unit IDs, assessed question IDs and rationale about capability/assessment intent. State `unmeasured` or `excluded` with a reason where appropriate; do not fabricate question coverage. Completeness of records does not mean all source capabilities are measured.
- `questions`: every question's physical `source_refs`, independent `solution_work`, `alternatives_checked`, `scope_check`, `hint_check`, `translation_check`, `findings`, and `status`. A question cannot cite an excluded/pending page as verified evidence. For short text, `rubric_trials` contains correct/partial/plausible incorrect `response`, in-range `score`, and criterion `rationale`.
- Findings need `status: open|resolved` and `detail`; resolved findings also need the actual `resolution`. Any open finding blocks complete-record status.

```sh
python3 <skill>/scripts/authoring_evidence.py check \
  --kc /work/day/kc.json --quiz /work/day/quiz.json \
  --context /work/day/authoring-context.json \
  --extraction /work/day/extraction.json --evidence /work/day/review.json
```

Exit `1`: malformed/contradictory inputs. Exit `2`: pending work, stale SHA, unresolved gap/finding or missing evidence. Exit `0`: `work_records_complete_needs_semantic_review` — the required records are populated and internally linked. **It is not an academic pass or import approval.** The script cannot verify truthful reasoning, meaningful text, visual reading, actual source/artifact bytes from a free-form citation, or independent approval. A reviewer must inspect those artifacts and work. Do not replace this report status with “quality passed”.

When source interpretation, bank, context or Extraction bytes change, `review_stale` blocks the report. Read affected work again; update evidence and deliberately refresh `inputs_sha256` only after that re-review. Creating a new scaffold can obtain current fingerprints, but does not carry prior review assertions forward. Keep prior review artifacts for traceability.

Finally run `package_day.py` for backend structure and, when supplied, target mapping. Actual environment preview, runtime grading and full-Day academic validation remain separate acceptance steps in [acceptance.md](acceptance.md).
