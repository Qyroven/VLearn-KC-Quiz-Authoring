import copy
import json
from pathlib import Path
import sys
import unittest

SKILL = Path(__file__).resolve().parents[1] / "skills/vlearn-kc-quiz-authoring"
sys.path.insert(0, str(SKILL / "scripts"))
import context_plan as c


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.kc, self.quiz, self.ctx = [json.loads((SKILL / "references/examples" / name).read_text()) for name in ("kc.json", "quiz.json", "context.json")]

    def plan(self):
        return c.plan(raw(self.kc), raw(self.quiz), raw(self.ctx))

    def test_candidate_pool_does_not_choose_variants_or_modify_bank(self):
        before = raw(self.quiz)
        report = self.plan()
        self.assertEqual(report["candidate_question_ids"], ["q1", "q2"])
        self.assertEqual(report["requested_question_count"], 1)
        self.assertEqual(report["status"], "candidate_plan_needs_agent_review")
        self.assertEqual(raw(self.quiz), before)

    def test_not_yet_learned_target_is_excluded(self):
        self.ctx["request"]["available_kc_ids"] = []
        report = self.plan()
        self.assertFalse(report["candidate_question_ids"])
        self.assertEqual(report["shortage"], 1)
        self.assertIn("knowledge_not_available", report["decisions"][0]["reasons"])

    def test_external_prerequisite_must_be_available(self):
        self.ctx["units"][0]["prerequisite_kc_ids"] = ["prior-day-embedding"]
        self.assertFalse(self.plan()["candidate_question_ids"])
        self.ctx["request"]["available_kc_ids"].append("prior-day-embedding")
        self.assertEqual(len(self.plan()["candidate_question_ids"]), 2)

    def test_question_specific_prerequisite(self):
        self.ctx["question_annotations"][0]["requires_kc_ids"] = ["reranking"]
        self.assertEqual(self.plan()["candidate_question_ids"], ["q2"])

    def test_exclusion_wins_even_when_available(self):
        self.ctx["request"]["excluded_kc_ids"] = ["kc1"]
        report = self.plan()
        self.assertFalse(report["candidate_question_ids"])
        self.assertIn("excluded_knowledge", report["decisions"][0]["reasons"])

    def test_same_kc_different_unit_respects_position(self):
        future = copy.deepcopy(self.ctx["units"][0])
        future["unit_id"] = "unit-later"
        self.ctx["units"].append(future)
        self.ctx["question_annotations"][1]["unit_ids"] = ["unit-later"]
        self.assertEqual(self.plan()["candidate_question_ids"], ["q1"])

    def test_missing_annotation_is_unverified(self):
        self.ctx["question_annotations"].pop()
        report = self.plan()
        self.assertEqual(report["candidate_question_ids"], ["q1"])
        self.assertIn("scope_annotation_missing", report["decisions"][1]["reasons"])

    def test_source_gap_blocks_only_affected_question_until_resolved(self):
        self.ctx["open_source_gaps"] = [{"issue_id": "figure-unreadable", "affected_question_ids": ["q1"]}]
        report = self.plan()
        self.assertEqual(report["candidate_question_ids"], ["q2"])
        self.assertIn("source_gap_open", report["decisions"][0]["reasons"])
        self.ctx["open_source_gaps"] = []
        self.assertEqual(len(self.plan()["candidate_question_ids"]), 2)

    def test_source_gap_can_affect_external_prerequisite(self):
        self.ctx["question_annotations"][0]["requires_kc_ids"] = ["prior-kc"]
        self.ctx["request"]["available_kc_ids"].append("prior-kc")
        self.ctx["open_source_gaps"] = [{"issue_id": "source-ambiguous", "affected_kc_ids": ["prior-kc"]}]
        self.assertEqual(self.plan()["candidate_question_ids"], ["q2"])

    def test_count_shortage_does_not_duplicate_or_broaden_scope(self):
        self.ctx["request"].update(question_count=10, time_minutes=3)
        report = self.plan()
        self.assertEqual(report["shortage"], 8)
        self.assertEqual(len(set(report["candidate_question_ids"])), 2)
        self.assertEqual(report["time_fit"], "not_verified")

    def test_bad_scope_and_unknown_field_fail_closed(self):
        original = copy.deepcopy(self.ctx)
        for mutate in (
            lambda: self.ctx["request"].update(unit_ids=["missing"]),
            lambda: self.ctx["request"].update(target_kc_ids=["missing"]),
            lambda: self.ctx["request"].update(excluded_kc_ids=["typo"]),
            lambda: self.ctx["request"].update(availble_kc_ids=["kc1"]),
            lambda: self.ctx["request"].update(question_count=True),
            lambda: self.ctx["question_annotations"].append(copy.deepcopy(self.ctx["question_annotations"][0])),
            lambda: self.ctx.update(open_source_gaps=[{"issue_id": "gap", "affected_kc_ids": ["typo"]}]),
        ):
            self.ctx = copy.deepcopy(original)
            mutate()
            with self.assertRaises(c.p.AuthoringError):
                self.plan()

    def test_integrated_question_requires_both_units_and_kcs(self):
        for lang in ("vi", "en"):
            leaf = copy.deepcopy(self.kc["localizations"][lang]["leaf_kcs"][0])
            leaf["kc_id"] = "kc2"
            self.kc["localizations"][lang]["leaf_kcs"].append(leaf)
            self.kc["localizations"][lang]["groups"][0]["leaf_kc_ids"].append("kc2")
            bp = self.quiz["blueprint"][lang]
            bp["modules"][0]["leaf_kc_ids"].append("kc2")
            bp["modules"][0]["assessment_slot_ids"].append("s2")
            bp["assessment_slots"].append({"slot_id": "s2", "module_id": "g1", "kc_id": "kc2", "variant_question_ids": ["q1"]})
            question = self.quiz["localizations"][lang]["questions"][0]
            question["contributing_kc_ids"] = ["kc2"]
            question["assessment_slot_ids"].append("s2")
        unit = copy.deepcopy(self.ctx["units"][0])
        unit.update(unit_id="unit-second", kc_ids=["kc2"])
        self.ctx["units"].append(unit)
        self.ctx["question_annotations"][0]["unit_ids"].append("unit-second")
        self.assertEqual(self.plan()["candidate_question_ids"], ["q2"])
        self.ctx["request"]["unit_ids"].append("unit-second")
        self.ctx["request"]["available_kc_ids"].append("kc2")
        self.assertEqual(self.plan()["candidate_question_ids"], ["q1", "q2"])


if __name__ == "__main__":
    unittest.main()
