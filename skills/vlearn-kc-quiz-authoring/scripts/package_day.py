#!/usr/bin/env python3
"""Validate native bilingual documents and produce a lossless, two-file ZIP."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import sys
import zipfile

from backend_contract import PROVENANCE, errors, graph, pair


class AuthoringError(ValueError):
    pass


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise AuthoringError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def bad_constant(value):
        raise AuthoringError(f"Non-finite JSON number: {value}")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)

    def check(item):
        if isinstance(item, float) and not math.isfinite(item):
            raise AuthoringError("Non-finite JSON number")
        if isinstance(item, str):
            item.encode("utf-8")  # Reject unpaired surrogate escapes.
        if isinstance(item, dict):
            for key, child in item.items():
                check(key)
                check(child)
        if isinstance(item, list):
            for child in item:
                check(child)

    check(value)
    return value


def require(condition, message):
    if not condition:
        raise AuthoringError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"Missing text: {label}")


def authoring_checks(kc, quiz):
    """Additional authoring safeguards, explicitly separate from backend gates."""
    for lang in ("vi", "en"):
        doc = kc["localizations"][lang]
        require(doc.get("schema_version") == "knowledge-components.day.v2", "Wrong localized KC schema")
        require(quiz["localizations"][lang].get("schema_version") == "quiz-bank.day.v2", "Wrong localized quiz schema")
        require(doc["leaf_kcs"] and quiz["localizations"][lang]["questions"], "Empty authored KC/Quiz bank")
        members = {row["group_id"]: set(row.get("leaf_kc_ids", [])) for row in doc["groups"]}
        expected = {key: set() for key in members}
        for leaf in doc["leaf_kcs"]:
            expected[leaf["group_id"]].add(leaf["kc_id"])
            text(leaf.get("name"), f"{lang}.{leaf['kc_id']}.name")
            text(leaf.get("observable_claim"), f"{lang}.{leaf['kc_id']}.observable_claim")
        require(members == expected, f"{lang}: group membership contradicts KC lineage")
        bp = quiz["blueprint"][lang]
        slots = {row["slot_id"]: row for row in bp["assessment_slots"]}
        modules = {row["module_id"]: row for row in bp["modules"]}
        questions = {row["question_id"]: row for row in quiz["localizations"][lang]["questions"]}
        for module_id, module in modules.items():
            actual = {sid for sid, slot in slots.items() if slot.get("module_id") == module_id}
            require(set(module.get("assessment_slot_ids", [])) == actual, f"{module_id}: slot membership mismatch")
            require(set(module.get("initial_representative_slot_ids", [])) <= actual, f"{module_id}: representative slot belongs elsewhere")
        for sid, slot in slots.items():
            require(slot.get("kc_id") in modules.get(slot.get("module_id"), {}).get("leaf_kc_ids", []), f"{sid}: KC outside module")
            actual = {qid for qid, q in questions.items() if sid in q["assessment_slot_ids"]}
            require(set(slot.get("variant_question_ids", [])) == actual, f"{sid}: question membership mismatch")
        for qid, question in questions.items():
            text(question["interaction"].get("prompt"), f"{lang}.{qid}.prompt")
            points = question.get("max_points")
            require(type(points) in (int, float) and points > 0, f"{qid}: max_points must be positive")
            require(type(question.get("question_version")) is int and question["question_version"] > 0, f"{qid}: question_version must be positive integer")
            for sid in question["assessment_slot_ids"]:
                slot = slots[sid]
                require(slot.get("module_id") == question.get("module_id"), f"{qid}: slot module mismatch")
                require(slot["kc_id"] in [question["primary_kc_id"], *question.get("contributing_kc_ids", [])], f"{qid}: slot KC is not assessed")
    vi = {row["kc_id"]: row["group_id"] for row in kc["localizations"]["vi"]["leaf_kcs"]}
    en = {row["kc_id"]: row["group_id"] for row in kc["localizations"]["en"]["leaf_kcs"]}
    require(vi == en, "VI/EN KC group lineage differs")
    en_questions = {q["question_id"]: q for q in quiz["localizations"]["en"]["questions"]}
    for question in quiz["localizations"]["vi"]["questions"]:
        peer = en_questions[question["question_id"]]
        left, right = question["answer_key_or_rubric"], peer["answer_key_or_rubric"]
        for key in ("allowed_scores", "score_policy"):
            require(left.get(key) == right.get(key), f"VI/EN {key} differs for {question['question_id']}")
        if question["interaction"]["type"] == "short_text":
            right_criteria = {row["criterion_id"]: row for row in right["criteria"]}
            for criterion in left["criteria"]:
                require(criterion.get("allowed_scores") == right_criteria[criterion["criterion_id"]].get("allowed_scores"), "VI/EN criterion score steps differ")


def validate(kc_raw, quiz_raw, target=None):
    kc, quiz = strict_json(kc_raw), strict_json(quiz_raw)
    manifest, _ = pair.expand_pair(kc_raw, quiz_raw)
    materials = manifest.get("materials", [])
    pages = {}
    for row in materials:
        mid, count = row.get("material_id"), row.get("page_count")
        require(isinstance(mid, str) and mid not in pages, "Materials need unique material_id")
        require(type(count) is int and count > 0, f"{mid}: materials.page_count must be positive integer")
        require(isinstance(row.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None,
                f"{mid}: materials.sha256 must be a lowercase SHA-256 digest")
        pages[mid] = count
    graph_results = {}
    for lang in ("vi", "en"):
        graph_results[lang] = graph.validate_content_graph(
            manifest=manifest, kc_documents=[kc["localizations"][lang]],
            blueprint=quiz["blueprint"][lang], banks=[quiz["localizations"][lang]],
            actual_material_pages=pages,
        )
    authoring_checks(kc, quiz)
    target_check = "unverified"
    if target is not None:
        require(isinstance(target, dict), "Target evidence must be an object")
        pair.verify_pair_target(kc["package"]["curriculum_identity"], **{
            key: target.get(key) for key in ("course_id", "mapping", "target_day", "source_days")
        })
        target_check = {
            "status": "matched_supplied_evidence",
            "environment": target.get("environment"), "observed_at": target.get("observed_at"),
            "course_id": target.get("course_id"),
            "evidence_sha256": hashlib.sha256(json.dumps(target, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        }
    return {
        "status": "local_preflight_passed",
        "backend_repository": PROVENANCE["repository"], "backend_commit": PROVENANCE["commit"],
        "checks": {"backend_pair_adapter": "passed", "backend_content_graph": graph_results,
                   "additional_authoring_structure": "passed",
                   "target_mapping": target_check},
        "counts": manifest["counts"], "curriculum_identity": kc["package"]["curriculum_identity"],
        "inputs": {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                   for name, raw in (("kc.json", kc_raw), ("quiz.json", quiz_raw))},
        "not_verified": ["live_backend_preview", "deployed_contract_revision", "source_file_integrity_and_visual_coverage",
                         "translation_and_academic_review", "runtime_grader_and_feature_flags"],
    }


def archive(kc_raw, quiz_raw):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, raw in (("kc.json", kc_raw), ("quiz.json", quiz_raw)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            zf.writestr(info, raw)
    return buffer.getvalue()


def deliver(kc_raw, quiz_raw, output, target=None):
    report = validate(kc_raw, quiz_raw, target)
    data = archive(kc_raw, quiz_raw)
    report["zip"] = {"file": "package.zip", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "package.zip").write_bytes(data)
        (output / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(output)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kc", required=True, type=Path)
    parser.add_argument("--quiz", required=True, type=Path)
    parser.add_argument("--target", type=Path, help="Read-only exported mapping evidence, never inferred from UI ordinals")
    parser.add_argument("--out", type=Path, help="New output directory; omit for validation only")
    args = parser.parse_args()
    try:
        raw = args.kc.read_bytes(), args.quiz.read_bytes()
        target = strict_json(args.target.read_bytes()) if args.target else None
        report = deliver(*raw, args.out, target) if args.out else validate(*raw, target)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError, errors.KcQuizContractError) as exc:
        print(json.dumps({"status": "failed", "code": getattr(exc, "code", type(exc).__name__), "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
