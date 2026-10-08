#!/usr/bin/env python3
"""Check declared lesson scope and propose a candidate pool without rewriting banks."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import package_day as p

PURPOSES = {"inline_check", "end_of_day", "weak_spots", "mixed_practice", "mock_exam"}


def obj(value, allowed, label):
    p.require(isinstance(value, dict), f"{label} must be an object")
    p.require(not set(value) - set(allowed), f"Unknown fields in {label}: {sorted(set(value) - set(allowed))}")
    return value


def ids(value, label):
    p.require(isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value), f"{label} must be an array of IDs")
    p.require(len(value) == len(set(value)), f"Duplicate ID in {label}")
    return set(value)


def index(rows, key, allowed, label):
    p.require(isinstance(rows, list), f"{label} must be an array")
    result = {}
    for row in rows:
        obj(row, allowed, label)
        p.text(row.get(key), f"{label}.{key}")
        p.require(row[key] not in result, f"Duplicate {key}: {row[key]}")
        result[row[key]] = row
    return result


def plan(kc_raw, quiz_raw, context_raw):
    p.validate(kc_raw, quiz_raw)
    kc, quiz, ctx = [p.strict_json(raw) for raw in (kc_raw, quiz_raw, context_raw)]
    obj(ctx, {"schema_version", "request", "units", "question_annotations", "open_source_gaps"}, "context")
    p.require(ctx.get("schema_version") == "authoring-context.v1", "Unsupported authoring context schema")
    request = obj(ctx.get("request"), {"purpose", "free_text", "position", "unit_ids", "target_kc_ids", "available_kc_ids", "excluded_kc_ids", "question_count", "time_minutes", "assumptions"}, "request")
    p.require(isinstance(request.get("purpose"), str) and request["purpose"] in PURPOSES, "Unknown purpose")
    if "free_text" in request:
        p.text(request["free_text"], "request.free_text")
    if "position" in request:
        p.require(isinstance(request["position"], dict), "request.position must be an object")
    if "assumptions" in request:
        p.require(isinstance(request["assumptions"], list) and all(isinstance(x, str) for x in request["assumptions"]), "assumptions must be a text array")
    for key in ("question_count", "time_minutes"):
        if key in request:
            p.require(type(request[key]) is int and request[key] > 0, f"{key} must be a positive integer")
    known_kcs = {row["kc_id"] for row in kc["localizations"]["vi"]["leaf_kcs"]}
    known_modules = {row["module_id"] for row in quiz["blueprint"]["vi"]["modules"]}
    questions = {row["question_id"]: row for row in quiz["localizations"]["vi"]["questions"]}
    units = index(ctx.get("units"), "unit_id", {"unit_id", "title", "goal", "kc_ids", "prerequisite_kc_ids", "source_windows", "blueprint_module_ids"}, "units")
    for uid, unit in units.items():
        for key in ("title", "goal"):
            p.text(unit.get(key), f"{uid}.{key}")
        kcs = ids(unit.get("kc_ids"), f"{uid}.kc_ids")
        p.require(kcs and kcs <= known_kcs, f"{uid}: empty or unknown KC scope")
        ids(unit.get("prerequisite_kc_ids"), f"{uid}.prerequisite_kc_ids")
        p.require(ids(unit.get("blueprint_module_ids", []), f"{uid}.blueprint_module_ids") <= known_modules, f"{uid}: unknown blueprint module")
        p.require(isinstance(unit.get("source_windows", []), list), f"{uid}: source_windows must be an array")
    selected = ids(request.get("unit_ids"), "request.unit_ids")
    p.require(selected and selected <= set(units), "Select at least one known learning unit")
    scope = set().union(*(set(units[uid]["kc_ids"]) for uid in selected))
    targets = ids(request.get("target_kc_ids", sorted(scope)), "request.target_kc_ids")
    p.require(targets and targets <= scope, "Target KCs must be inside selected units")
    available = ids(request.get("available_kc_ids"), "request.available_kc_ids")
    excluded = ids(request.get("excluded_kc_ids", []), "request.excluded_kc_ids")
    annotations = index(ctx.get("question_annotations"), "question_id", {"question_id", "unit_ids", "requires_kc_ids"}, "question_annotations")
    for qid, annotation in annotations.items():
        p.require(qid in questions, f"Unknown annotated question: {qid}")
        owners = ids(annotation.get("unit_ids"), f"{qid}.unit_ids")
        p.require(owners and owners <= set(units), f"{qid}: empty or unknown unit annotation")
        ids(annotation.get("requires_kc_ids"), f"{qid}.requires_kc_ids")
        assessed = {questions[qid]["primary_kc_id"], *questions[qid].get("contributing_kc_ids", [])}
        p.require(assessed <= set().union(*(set(units[uid]["kc_ids"]) for uid in owners)), f"{qid}: assessed KC outside annotated units")
    known_context_kcs = known_kcs | available
    for unit in units.values():
        known_context_kcs |= set(unit["prerequisite_kc_ids"])
    for annotation in annotations.values():
        known_context_kcs |= set(annotation["requires_kc_ids"])
    p.require(excluded <= known_context_kcs, "Unknown excluded knowledge ID")
    blocked_kcs, blocked_questions = set(), set()
    gaps = index(ctx.get("open_source_gaps", []), "issue_id", {"issue_id", "affected_kc_ids", "affected_question_ids"}, "open_source_gaps")
    for gid, gap in gaps.items():
        kcs = ids(gap.get("affected_kc_ids", []), f"{gid}.affected_kc_ids")
        qids = ids(gap.get("affected_question_ids", []), f"{gid}.affected_question_ids")
        p.require(qids <= set(questions), f"{gid}: unknown affected question")
        p.require(kcs <= known_context_kcs, f"{gid}: unknown affected KC")
        p.require(kcs or qids, f"{gid}: source gap needs explicit impact")
        blocked_kcs |= kcs
        blocked_questions |= qids
    candidates, decisions = [], []
    for qid, question in questions.items():
        reasons = []
        assessed = {question["primary_kc_id"], *question.get("contributing_kc_ids", [])}
        annotation = annotations.get(qid)
        required = set()
        if annotation is None:
            reasons.append("scope_annotation_missing")
        else:
            owners = set(annotation["unit_ids"])
            if not owners <= selected:
                reasons.append("unit_outside_request")
            required = set(annotation["requires_kc_ids"])
            for uid in owners:
                required |= set(units[uid]["prerequisite_kc_ids"])
        if not assessed <= targets:
            reasons.append("assessed_kc_outside_target")
        if (assessed | required) & excluded:
            reasons.append("excluded_knowledge")
        if not (assessed | required) <= available:
            reasons.append("knowledge_not_available")
        if qid in blocked_questions or (assessed | required) & blocked_kcs:
            reasons.append("source_gap_open")
        if not reasons:
            candidates.append(qid)
        decisions.append({"question_id": qid, "candidate": not reasons, "reasons": reasons})
    return {
        "status": "candidate_plan_needs_agent_review", "purpose": request["purpose"],
        "input_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in (("kc.json", kc_raw), ("quiz.json", quiz_raw), ("context.json", context_raw))},
        "target_kc_ids": sorted(targets), "candidate_question_ids": candidates,
        "requested_question_count": request.get("question_count"),
        "shortage": max(0, request.get("question_count", 0) - len(candidates)),
        "requested_time_minutes": request.get("time_minutes"), "time_fit": "not_verified",
        "decisions": decisions, "assumptions": request.get("assumptions", []),
        "not_verified": ["scope_annotations_semantics", "source_recovery_quality", "question_answer_quality", "translation_quality", "live_vlearn_inline_quiz_support"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("kc", "quiz", "context"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(plan(args.kc.read_bytes(), args.quiz.read_bytes(), args.context.read_bytes()), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError, p.errors.KcQuizContractError) as exc:
        print(json.dumps({"status": "failed", "code": getattr(exc, "code", type(exc).__name__), "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
