#!/usr/bin/env python3
"""Create/check revision-bound source, coverage and academic review work records."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import context_plan as context
import package_day as p


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(kc_raw, quiz_raw, context_raw, extraction_raw):
    return {name: digest(raw) for name, raw in (("kc", kc_raw), ("quiz", quiz_raw), ("context", context_raw), ("extraction", extraction_raw))}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def read_inputs(kc_raw, quiz_raw, context_raw, extraction_raw):
    plan = context.plan(kc_raw, quiz_raw, context_raw)
    kc, quiz, ctx, extraction = [p.strict_json(raw) for raw in (kc_raw, quiz_raw, context_raw, extraction_raw)]
    p.require(isinstance(extraction, dict) and extraction.get("schema_version") == "source-extraction.v1", "Expected source-extraction.v1")
    sources = context.index(extraction.get("sources"), "source_id", {"source_id", "sha256", "page_count"}, "extraction.sources")
    p.require(sources, "Extraction needs actual source inventory")
    for sid, source in sources.items():
        p.require(isinstance(source.get("sha256"), str) and len(source["sha256"]) == 64 and all(c in "0123456789abcdef" for c in source["sha256"]), f"{sid}: invalid SHA-256")
        p.require(type(source.get("page_count")) is int and source["page_count"] > 0, f"{sid}: invalid page count")
    pages = extraction.get("pages")
    p.require(isinstance(pages, list), "extraction.pages must be an array")
    seen = set()
    for page in pages:
        context.obj(page, {"source_id", "page", "page_label", "raw_text", "blocks", "page_note", "status", "exclusion_reason"}, "extraction.page")
        sid, number = page.get("source_id"), page.get("page")
        p.require(sid in sources and type(number) is int and 1 <= number <= sources[sid]["page_count"], "Extraction page outside source inventory")
        p.require((sid, number) not in seen, "Duplicate extraction page")
        seen.add((sid, number))
        p.require(page.get("status") in {"pending", "reviewed", "excluded"}, "Unknown extraction page status")
        p.require(isinstance(page.get("blocks"), list), "Page blocks must be an array")
    expected = {(sid, n) for sid, source in sources.items() for n in range(1, source["page_count"] + 1)}
    p.require(seen == expected, "Extraction must inventory every physical PDF page, including explicitly excluded pages")
    return kc, quiz, ctx, extraction, plan


def scaffold(kc_raw, quiz_raw, context_raw, extraction_raw):
    kc, quiz, ctx, extraction, _ = read_inputs(kc_raw, quiz_raw, context_raw, extraction_raw)
    return {
        "schema_version": "authoring-evidence.v1", "inputs_sha256": fingerprint(kc_raw, quiz_raw, context_raw, extraction_raw),
        "reviewer": "", "reviewed_at": "", "review_kind": "self_review",
        "source_recovery": [],
        "coverage": [{"kc_id": leaf["kc_id"], "unit_ids": [u["unit_id"] for u in ctx["units"] if leaf["kc_id"] in u["kc_ids"]],
                      "status": "pending", "question_ids": [], "rationale": ""} for leaf in kc["localizations"]["vi"]["leaf_kcs"]],
        "questions": [{"question_id": question["question_id"], "source_refs": [], "solution_work": "", "alternatives_checked": "",
                       "scope_check": "", "hint_check": "", "rubric_trials": [], "translation_check": "",
                       "status": "pending", "findings": []} for question in quiz["localizations"]["vi"]["questions"]],
        "not_verified": ["semantic_correctness", "independent_approval", "live_backend_preview"]}


def check(kc_raw, quiz_raw, context_raw, extraction_raw, evidence_raw):
    kc, quiz, ctx, extraction, plan = read_inputs(kc_raw, quiz_raw, context_raw, extraction_raw)
    evidence = p.strict_json(evidence_raw)
    context.obj(evidence, {"schema_version", "inputs_sha256", "reviewer", "reviewed_at", "review_kind", "source_recovery", "coverage", "questions", "not_verified"}, "evidence")
    p.require(evidence.get("schema_version") == "authoring-evidence.v1", "Expected authoring-evidence.v1")
    p.require(evidence.get("review_kind") == "self_review", "This helper records self-review; independent approval requires separately attributed reviewer evidence")
    blockers = []
    def block(code, record, detail):
        blockers.append({"code": code, "record": record, "detail": detail})
    if evidence.get("inputs_sha256") != fingerprint(kc_raw, quiz_raw, context_raw, extraction_raw):
        block("review_stale", "inputs_sha256", "One or more source/extraction/bank/context inputs changed; re-review affected work and rebind explicitly")
    if not nonempty(evidence.get("reviewer")) or not nonempty(evidence.get("reviewed_at")):
        block("review_attribution_missing", "evidence", "Record the actual reviewer and ISO date/time")
    else:
        from datetime import datetime
        try:
            timestamp = datetime.fromisoformat(evidence["reviewed_at"].replace("Z", "+00:00"))
            if "T" not in evidence["reviewed_at"] or timestamp.tzinfo is None:
                raise ValueError("Review timestamp needs time and timezone")
        except ValueError:
            block("review_timestamp_invalid", "reviewed_at", "Use an ISO date/time")
    sources = {s["source_id"]: s for s in extraction["sources"]}
    for page in extraction["pages"]:
        key = f"{page['source_id']}:{page['page']}"
        if page["status"] == "pending":
            block("page_unreviewed", key, "Read the full rendered page, including meaningful visuals")
        elif page["status"] == "excluded":
            if not nonempty(page.get("exclusion_reason")):
                block("page_exclusion_unexplained", key, "Explain why this source page is outside the requested authoring scope")
        elif not nonempty(page.get("page_note")) or not page["blocks"]:
            block("page_evidence_missing", key, "Reviewed pages need meaningful extracted blocks and an agent-authored page note")
        else:
            for n, item in enumerate(page["blocks"]):
                p.require(isinstance(item, dict), "Extraction block must be an object")
                if item.get("kind") not in {"text", "table", "figure", "diagram", "code", "formula"} or not nonempty(item.get("content")):
                    block("extraction_block_incomplete", f"{key}:{n}", "Block needs kind and content; preserve qualifier, relationships, numbers and units")
    page_status = {(row["source_id"], row["page"]): row["status"] for row in extraction["pages"]}
    def refs_ok(refs, require_reviewed=False):
        return isinstance(refs, list) and bool(refs) and all(isinstance(ref, dict) and ref.get("source_id") in sources and type(ref.get("page")) is int and 1 <= ref["page"] <= sources[ref["source_id"]]["page_count"] and (not require_reviewed or page_status.get((ref["source_id"], ref["page"])) == "reviewed") for ref in refs)
    questions = {q["question_id"]: q for q in quiz["localizations"]["vi"]["questions"]}
    kcs = {leaf["kc_id"] for leaf in kc["localizations"]["vi"]["leaf_kcs"]}
    external_kcs = set(ctx["request"]["available_kc_ids"])
    for unit in ctx["units"]:
        external_kcs.update(unit["prerequisite_kc_ids"])
    for row in ctx["question_annotations"]:
        external_kcs.update(row["requires_kc_ids"])
    gaps = context.index(evidence.get("source_recovery"), "issue_id", {"issue_id", "source_id", "page", "missing_fact", "attempts", "status", "recovered_fact", "verification", "affected_kc_ids", "affected_question_ids", "next_action"}, "source_recovery")
    open_gaps = {}
    for gid, gap in gaps.items():
        p.require(refs_ok([{"source_id": gap.get("source_id"), "page": gap.get("page")}]), f"{gid}: source/page outside extraction inventory")
        p.text(gap.get("missing_fact"), f"{gid}.missing_fact")
        p.require(gap.get("status") in {"recovered_verified", "partially_recovered", "needs_source", "needs_lecturer_confirmation"}, f"{gid}: unknown recovery status")
        affected_kcs = context.ids(gap.get("affected_kc_ids", []), f"{gid}.affected_kc_ids")
        affected_questions = context.ids(gap.get("affected_question_ids", []), f"{gid}.affected_question_ids")
        p.require(affected_kcs <= kcs | external_kcs and affected_questions <= set(questions), f"{gid}: unknown recovery impact IDs")
        p.require(affected_kcs or affected_questions, f"{gid}: recovery impact must be explicit")
        attempts = gap.get("attempts")
        p.require(isinstance(attempts, list), f"{gid}: attempts must be an array")
        if not attempts:
            block("recovery_attempt_missing", gid, "Record attempted recovery or explicit dependency/source blocker")
        for attempt in attempts:
            p.require(isinstance(attempt, dict), f"{gid}: attempt must be an object")
            if not all(nonempty(attempt.get(key)) for key in ("method", "artifact", "result")):
                block("recovery_attempt_incomplete", gid, "Attempt needs method, artifact and actual result")
        if gap["status"] == "recovered_verified":
            if not nonempty(gap.get("recovered_fact")) or not nonempty(gap.get("verification")):
                block("recovery_verification_missing", gid, "Recovered status needs the fact and comparison evidence")
        else:
            open_gaps[gid] = gap
            block("source_gap_open", gid, gap.get("missing_fact"))
            if not nonempty(gap.get("next_action")):
                block("recovery_next_action_missing", gid, "Request the specific missing evidence or lecturer confirmation")
    declared_gaps = {g["issue_id"]: g for g in ctx.get("open_source_gaps", [])}
    if set(open_gaps) != set(declared_gaps):
        block("context_recovery_out_of_sync", "open_source_gaps", "Context open gap IDs must match unresolved recovery records")
    for gid in set(open_gaps) & set(declared_gaps):
        for field in ("affected_kc_ids", "affected_question_ids"):
            if set(open_gaps[gid].get(field, [])) != set(declared_gaps[gid].get(field, [])):
                block("context_recovery_impact_mismatch", gid, field)
    coverage = context.index(evidence.get("coverage"), "kc_id", {"kc_id", "unit_ids", "status", "question_ids", "rationale"}, "coverage")
    p.require(set(coverage) == kcs, "Coverage must record every KC exactly once")
    units = {u["unit_id"]: u for u in ctx["units"]}
    for kid, record in coverage.items():
        p.require(record.get("status") in {"pending", "assessed", "unmeasured", "excluded"}, f"{kid}: unknown coverage status")
        owners = context.ids(record.get("unit_ids"), f"{kid}.unit_ids")
        p.require(owners and owners <= set(units) and all(kid in units[uid]["kc_ids"] for uid in owners), f"{kid}: coverage unit linkage invalid")
        qids = context.ids(record.get("question_ids"), f"{kid}.question_ids")
        p.require(qids <= set(questions), f"{kid}: unknown coverage question")
        p.require(all(kid in {questions[qid]["primary_kc_id"], *questions[qid].get("contributing_kc_ids", [])} for qid in qids), f"{kid}: coverage question does not assess KC")
        if record["status"] == "pending" or not nonempty(record.get("rationale")):
            block("coverage_unreviewed", kid, "Record represented capability, assessment intent and any omission rationale")
        if record["status"] == "assessed" and not qids:
            block("coverage_assessment_missing", kid, "Assessed coverage needs linked questions")
        if record["status"] in {"unmeasured", "excluded"} and qids:
            block("coverage_status_contradiction", kid, "Unmeasured/excluded records cannot also claim assessed questions")
    reviews = context.index(evidence.get("questions"), "question_id", {"question_id", "source_refs", "solution_work", "alternatives_checked", "scope_check", "hint_check", "rubric_trials", "translation_check", "status", "findings"}, "questions")
    p.require(set(reviews) == set(questions), "Review must record every bank question exactly once")
    annotated_questions = {row["question_id"] for row in ctx["question_annotations"]}
    for qid, record in reviews.items():
        if qid not in annotated_questions:
            block("question_scope_annotation_missing", qid, "Record learning-unit ownership and required prior knowledge")
        p.require(record.get("status") in {"pending", "needs_revision", "self_reviewed"}, f"{qid}: unknown review status")
        if record["status"] != "self_reviewed":
            block("question_review_open", qid, record["status"])
        if not refs_ok(record.get("source_refs"), require_reviewed=True):
            block("question_source_evidence_missing", qid, "Cite physical source pages for the assessed claim and necessary givens")
        for field in ("solution_work", "alternatives_checked", "scope_check", "hint_check", "translation_check"):
            if not nonempty(record.get(field)):
                block("question_review_evidence_missing", qid, field)
        trials = record.get("rubric_trials")
        p.require(isinstance(trials, list), f"{qid}: rubric_trials must be an array")
        if questions[qid]["interaction"]["type"] == "short_text":
            kinds = set()
            for trial in trials:
                p.require(isinstance(trial, dict), f"{qid}: rubric trial must be an object")
                kinds.add(trial.get("case"))
                if not nonempty(trial.get("response")) or not nonempty(trial.get("rationale")) or type(trial.get("score")) not in (int, float) or not 0 <= trial["score"] <= questions[qid]["max_points"]:
                    block("rubric_trial_incomplete", qid, "Trial needs response, in-range score and criterion rationale")
            if not {"correct", "partial", "incorrect"} <= kinds:
                block("rubric_trials_missing", qid, "Try correct, partial and plausible incorrect responses")
        findings = record.get("findings")
        p.require(isinstance(findings, list), f"{qid}: findings must be an array")
        for finding in findings:
            p.require(isinstance(finding, dict) and finding.get("status") in {"open", "resolved"} and nonempty(finding.get("detail")), f"{qid}: invalid finding")
            if finding["status"] == "open":
                block("academic_finding_open", qid, finding["detail"])
            elif not nonempty(finding.get("resolution")):
                block("finding_resolution_missing", qid, finding["detail"])
    return {"status": "work_records_complete_needs_semantic_review" if not blockers else "incomplete_or_blocked",
            "blockers": blockers, "counts": {"sources": len(sources), "pages": len(extraction["pages"]), "kcs": len(kcs), "questions": len(questions)},
            "context_plan": plan, "review_kind": "self_review",
            "not_verified": ["truth_of_review_claims", "semantic_correctness", "source_file_bytes_against_inventory", "recovery_artifact_content", "independent_approval", "live_backend_preview"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "check"))
    for key in ("kc", "quiz", "context", "extraction"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = [getattr(args, key).read_bytes() for key in ("kc", "quiz", "context", "extraction")]
        if args.command == "init":
            report = scaffold(*raw)
            with args.evidence.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"status": "pending_work_records_created", "evidence": str(args.evidence)}, ensure_ascii=False))
            return 0
        report = check(*raw, args.evidence.read_bytes())
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not report["blockers"] else 2
    except (ValueError, OSError, TypeError, KeyError, AttributeError, p.errors.KcQuizContractError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
