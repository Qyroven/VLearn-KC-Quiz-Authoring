#!/usr/bin/env python3
"""Prepare local PDF evidence or run a reproducible render/crop/OCR recovery attempt."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import tempfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    result = subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError(f"{Path(str(argv[0])).name} failed: {result.stderr[-2000:]}")
    return result.stdout


def tool(name):
    found = shutil.which(name)
    if not found:
        raise ValueError(f"Missing local dependency: {name}; provide/install it before this operation")
    return found


def pages_arg(value, count):
    if value == "all":
        return list(range(1, count + 1))
    pages = set()
    for part in value.split(","):
        ends = part.split("-")
        if not 1 <= len(ends) <= 2 or not all(x.isdigit() for x in ends):
            raise ValueError("Pages must be all or comma-separated one-based pages/ranges")
        start, end = int(ends[0]), int(ends[-1])
        if not 1 <= start <= end <= count:
            raise ValueError(f"Page range outside 1..{count}")
        pages.update(range(start, end + 1))
    return sorted(pages)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(output, action):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".source-work-", dir=output.parent))
    try:
        result = action(work)
        if output.exists():
            raise ValueError(f"Output appeared during operation: {output}")
        work.rename(output)
        return result
    finally:
        if work.exists():
            shutil.rmtree(work)


def render(pdf, page, output, dpi, crop=None):
    args = [tool("pdftoppm"), "-f", page, "-l", page, "-r", dpi, "-singlefile", "-png"]
    if crop:
        for flag, value in zip(("-x", "-y", "-W", "-H"), crop):
            args += [flag, value]
    run(args + [pdf, output])
    result = output.with_suffix(".png")
    if not result.is_file():
        raise ValueError("Renderer returned without the expected PNG")
    return result


def prepare(pdf, source_id, output, pages="all", dpi=150, text_python=None):
    pdf = Path(pdf).resolve()
    if not source_id.strip():
        raise ValueError("source_id must be non-empty")
    info = run([tool("pdfinfo"), pdf])
    match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.M)
    if not match:
        raise ValueError("pdfinfo did not report a page count")
    count = int(match.group(1))
    selected = pages_arg(pages, count)
    source_sha = sha(pdf)

    def action(work):
        (work / "pdfinfo.txt").write_text(info, encoding="utf-8")
        extractor = shutil.which("pdftotext")
        extraction_status = "unavailable_pdftotext"
        text_pages = [""] * count
        if extractor:
            text = run([extractor, "-layout", pdf, "-"])
            text_pages = text.split("\f")
            if text_pages and not text_pages[-1].strip():
                text_pages.pop()
            if len(text_pages) != count:
                raise ValueError("Text extractor page boundaries differ from PDF inventory")
            extraction_status = "extracted_unverified"
        elif text_python:
            # A caller-selected local runtime with pdfplumber; never installs dependencies.
            code = "import json,sys,pdfplumber; p=pdfplumber.open(sys.argv[1]); print(json.dumps([(x.extract_text() or '') for x in p.pages])); p.close()"
            text_pages = json.loads(run([text_python, "-c", code, pdf]))
            if not isinstance(text_pages, list) or len(text_pages) != count or not all(isinstance(x, str) for x in text_pages):
                raise ValueError("pdfplumber result differs from PDF inventory")
            extraction_status = "pdfplumber_extracted_unverified"
        rendered = {}
        for page in selected:
            image = render(pdf, page, work / f"page-{page:04d}", dpi)
            rendered[str(page)] = {"artifact": image.name, "sha256": sha(image), "dpi": dpi}
        if sha(pdf) != source_sha:
            raise ValueError("Source PDF changed during preparation")
        manifest = {"schema_version": "source-workspace.v1", "source_id": source_id,
                    "path": str(pdf), "sha256": source_sha, "page_count": count,
                    "rendered_pages": rendered, "text_extraction": extraction_status,
                    "tools": {name: shutil.which(name) for name in ("pdfinfo", "pdftoppm", "pdftotext")},
                    "text_python": str(text_python) if text_python else None, "review_status": "unreviewed"}
        write_json(work / "source.json", manifest)
        draft = {"schema_version": "source-extraction.v1", "sources": [{"source_id": source_id, "sha256": source_sha, "page_count": count}],
                 "pages": [{"source_id": source_id, "page": n,
                            "raw_text": text_pages[n - 1], "blocks": [], "page_note": "",
                            "status": "pending", "exclusion_reason": ""} for n in range(1, count + 1)]}
        write_json(work / "extraction-draft.json", draft)
        return manifest
    return publish(output, action)


def recover(workspace, page, output, dpi=300, crop=None, ocr_language=None):
    workspace = Path(workspace)
    manifest = json.loads((workspace / "source.json").read_text(encoding="utf-8"))
    pdf = Path(manifest["path"])
    if sha(pdf) != manifest["sha256"]:
        raise ValueError("Source changed; create a new workspace and invalidate downstream review")
    if type(page) is not int or not 1 <= page <= manifest["page_count"]:
        raise ValueError("Recovery page outside source inventory")
    if crop and (len(crop) != 4 or any(type(x) is not int for x in crop) or min(crop[:2]) < 0 or min(crop[2:]) <= 0):
        raise ValueError("Crop requires nonnegative x/y and positive width/height in rendered pixels")

    def action(work):
        full = render(pdf, page, work / "full-page", dpi)
        if crop:
            header = full.read_bytes()[:24]
            if header[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("Renderer did not produce a valid PNG header")
            width, height = struct.unpack(">II", header[16:24])
            if crop[0] + crop[2] > width or crop[1] + crop[3] > height:
                raise ValueError(f"Crop outside full render bounds {width}x{height} at {dpi} DPI")
        image = render(pdf, page, work / "crop", dpi, crop) if crop else full
        artifacts = [{"file": name.name, "sha256": sha(name)} for name in dict.fromkeys((full, image))]
        ocr = {"status": "not_requested"}
        if ocr_language:
            executable = shutil.which("tesseract")
            if not executable:
                ocr = {"status": "unavailable_tesseract", "language": ocr_language,
                       "next_action": "Provide local tesseract and its requested language data, or inspect the render manually"}
            else:
                text = run([executable, image, "stdout", "-l", ocr_language])
                (work / "ocr-unverified.txt").write_text(text, encoding="utf-8")
                artifacts.append({"file": "ocr-unverified.txt", "sha256": sha(work / "ocr-unverified.txt")})
                ocr = {"status": "extracted_unverified", "language": ocr_language}
        if sha(pdf) != manifest["sha256"]:
            raise ValueError("Source changed during recovery")
        result = {"schema_version": "source-recovery-attempt.v1", "source_id": manifest["source_id"],
                  "source_sha256": manifest["sha256"], "page": page, "dpi": dpi,
                  "crop_pixels": crop, "artifacts": artifacts, "ocr": ocr,
                  "status": "needs_visual_verification",
                  "not_verified": ["recovered_fact_correctness", "source_quality", "downstream_question_validity"]}
        write_json(work / "attempt.json", result)
        return result
    return publish(output, action)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--pdf", type=Path, required=True)
    prep.add_argument("--source-id", required=True)
    prep.add_argument("--pages", default="all")
    prep.add_argument("--text-python", type=Path, help="Optional local Python runtime with pdfplumber when pdftotext is unavailable")
    prep.add_argument("--dpi", type=int, default=150)
    prep.add_argument("--out", type=Path, required=True)
    rec = commands.add_parser("recover")
    rec.add_argument("--workspace", type=Path, required=True)
    rec.add_argument("--page", type=int, required=True)
    rec.add_argument("--dpi", type=int, default=300)
    rec.add_argument("--crop", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    rec.add_argument("--ocr-language")
    rec.add_argument("--out", type=Path, required=True)
    args = vars(parser.parse_args())
    command, output = args.pop("command"), args.pop("out")
    if not 36 <= args["dpi"] <= 600:
        parser.error("DPI must be between 36 and 600")
    try:
        report = prepare(output=output, **args) if command == "prepare" else recover(output=output, **args)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, KeyError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
