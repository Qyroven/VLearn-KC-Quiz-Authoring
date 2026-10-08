import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SKILL = Path(__file__).resolve().parents[1] / "skills/vlearn-kc-quiz-authoring"
sys.path.insert(0, str(SKILL / "scripts"))
import package_day as p


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.raw = [(SKILL / "references/examples" / name).read_bytes() for name in ("kc.json", "quiz.json")]
        self.kc, self.quiz = [json.loads(raw) for raw in self.raw]
        self.target = {"course_id": "test-course", "mapping": {
            "course_id": "test-course", "intake": "K04", "level": "L34", "phase": 2, "track": 1},
            "target_day": {"day_code": "D01"}, "source_days": [{"course_id": "test-course",
            "source_day": "day01", "learning_day_number": 1, "target_day_code": "D01"}]}

    def validate(self, target=None):
        return p.validate(encoded(self.kc), encoded(self.quiz), target)

    def both_questions(self, change):
        for lang in ("vi", "en"):
            change(self.quiz["localizations"][lang]["questions"][0])

    def test_official_fixture_and_target_status(self):
        report = p.validate(*self.raw)
        self.assertEqual(report["counts"]["questions"], 2)
        self.assertEqual(report["checks"]["target_mapping"], "unverified")
        self.assertIn("live_backend_preview", report["not_verified"])
        self.assertEqual(self.validate(self.target)["checks"]["target_mapping"]["status"], "matched_supplied_evidence")

    def test_zip_determinism_lossless_prose_unknown_fields_and_exact_entries(self):
        self.kc["package"]["academic_note"] = {"custom": "Không cắt dữ liệu"}
        for lang in ("vi", "en"):
            self.quiz["localizations"][lang]["questions"][0]["hints"] = ["Một gợi ý" if lang == "vi" else "A hint"]
        raw = encoded(self.kc), encoded(self.quiz)
        p.validate(*raw)
        data = p.archive(*raw)
        self.assertEqual(data, p.archive(*raw))
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            self.assertEqual(zf.namelist(), ["kc.json", "quiz.json"])
            for name, original in zip(zf.namelist(), raw):
                self.assertEqual(zf.read(name), original)

    def test_output_no_clobber_and_external_report(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "delivery"
            report = p.deliver(*self.raw, out)
            original = (out / "package.zip").read_bytes()
            self.assertEqual(hashlib.sha256(original).hexdigest(), report["zip"]["sha256"])
            self.assertEqual({f.name for f in out.iterdir()}, {"package.zip", "validation-report.json"})
            with self.assertRaises(FileExistsError):
                p.deliver(*self.raw, out)
            self.assertEqual(original, (out / "package.zip").read_bytes())

    def test_failed_validation_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "delivery"
            with self.assertRaises(Exception):
                p.deliver(b"{}", self.raw[1], out)
            self.assertFalse(out.exists())

    def test_duplicate_json_keys_and_nonfinite_numbers(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'{"x":"\\ud800"}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                p.strict_json(raw)

    def test_root_extra_and_missing_language(self):
        self.kc["extra"] = "should reject"
        with self.assertRaises(p.pair.PairContractError):
            self.validate()
        del self.kc["extra"]
        del self.quiz["localizations"]["en"]
        with self.assertRaises(p.pair.PairContractError):
            self.validate()

    def test_locale_answer_drift(self):
        self.quiz["localizations"]["en"]["questions"][0]["answer_key_or_rubric"]["correct_choice_id"] = "b"
        with self.assertRaises(p.pair.PairContractError):
            self.validate()

    def test_unknown_answer_even_when_locales_agree(self):
        self.both_questions(lambda q: q["answer_key_or_rubric"].update(correct_choice_id="missing"))
        with self.assertRaises(p.errors.KcQuizContractError):
            self.validate()

    def test_broken_primary_kc(self):
        self.both_questions(lambda q: q.update(primary_kc_id="missing"))
        with self.assertRaises(p.errors.KcQuizContractError):
            self.validate()

    def test_blueprint_relationships_not_just_known_ids(self):
        for lang in ("vi", "en"):
            self.quiz["blueprint"][lang]["assessment_slots"][0]["variant_question_ids"] = ["q1"]
        with self.assertRaises(p.AuthoringError):
            self.validate()

    def test_group_membership_not_just_known_ids(self):
        for lang in ("vi", "en"):
            self.kc["localizations"][lang]["groups"][0]["leaf_kc_ids"] = []
        with self.assertRaises(p.AuthoringError):
            self.validate()

    def test_wrong_course_track_and_destination(self):
        for key, value in (("track", 2), ("course_id", "other-course")):
            with self.subTest(key=key):
                target = copy.deepcopy(self.target)
                target["mapping"][key] = value
                with self.assertRaises(p.pair.PairContractError):
                    self.validate(target)
        self.target["target_day"]["day_code"] = "D02"
        with self.assertRaises(p.pair.PairContractError):
            self.validate(self.target)

    def test_source_day_and_learning_day_are_distinct(self):
        self.kc["package"]["curriculum_identity"]["source_day"] = "day16"
        self.target["source_days"][0]["source_day"] = "day16"
        self.assertEqual(self.validate(self.target)["curriculum_identity"]["learning_day_number"], 1)

    def test_page_references_and_material_metadata(self):
        self.kc["package"]["materials"] = [{"material_id": "pdf", "page_count": 2, "sha256": "a" * 64}]
        self.kc["package"]["traceability"]["source_mappings"] = [{"extraction_path": "extraction/pdf.json", "material_id": "pdf"}]
        for lang in ("vi", "en"):
            self.kc["localizations"][lang]["leaf_kcs"][0]["source_refs"] = [{"extraction_path": "extraction/pdf.json", "page": 2}]
        self.validate()
        for lang in ("vi", "en"):
            self.kc["localizations"][lang]["leaf_kcs"][0]["source_refs"][0]["page"] = 3
        with self.assertRaises(p.errors.KcQuizContractError):
            self.validate()

    def test_reference_only_sources_are_retained(self):
        self.kc["package"]["traceability"]["unbundled_source_refs"] = [{"extraction_path": "external.json", "reason": "External lecturer context"}]
        for lang in ("vi", "en"):
            self.kc["localizations"][lang]["leaf_kcs"][0]["source_refs"] = [{"extraction_path": "external.json", "page": 1}]
        self.validate()

    def test_narrative_bullet_count_may_differ(self):
        for lang, notes in (("vi", ["a", "b"]), ("en", ["combined a and b"])):
            self.kc["localizations"][lang]["leaf_kcs"][0]["notes"] = notes
        self.validate()

    def test_missing_prompt_and_invalid_version(self):
        self.both_questions(lambda q: q["interaction"].update(prompt=""))
        with self.assertRaises(p.AuthoringError):
            self.validate()
        self.both_questions(lambda q: q["interaction"].update(prompt="A question"))
        self.both_questions(lambda q: q.update(question_version=True))
        with self.assertRaises(p.AuthoringError):
            self.validate()

    def test_all_supported_interaction_keys_and_short_text_scoring(self):
        cases = [
            ({"type": "multi_select", "choices": [{"choice_id": "a", "text": "A"}]}, {"correct_choice_ids": ["a"]}),
            ({"type": "matching", "left": [{"id": "a", "text": "A"}], "right": [{"id": "b", "text": "B"}]}, {"correct_pairs": {"a": "b"}}),
            ({"type": "ordering", "options": [{"option_id": "a", "text": "A"}]}, {"correct_order": ["a"]}),
            ({"type": "numeric_input", "required_unit": "m"}, {"value": 3, "tolerance": 0.1, "unit": "m"}),
            ({"type": "short_text"}, {"grading": "rubric", "exemplar_answer": "Answer", "criteria": [{"criterion_id": "c1", "description": "Evidence", "points": 1, "allowed_scores": [0, 1]}]}),
        ]
        for interaction, answer in cases:
            with self.subTest(type=interaction["type"]):
                self.both_questions(lambda q: q.update(interaction={**interaction, "prompt": "A prompt"}, answer_key_or_rubric=answer))
                self.validate()
        self.quiz["localizations"]["en"]["questions"][0]["answer_key_or_rubric"] = copy.deepcopy(cases[-1][1])
        self.quiz["localizations"]["en"]["questions"][0]["answer_key_or_rubric"]["criteria"][0]["allowed_scores"] = [0, 0.5, 1]
        with self.assertRaises(p.AuthoringError):
            self.validate()

    def test_cli_failed_input_returns_nonzero_json(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{}")
            result = subprocess.run([sys.executable, str(SKILL / "scripts/package_day.py"), "--kc", str(bad), "--quiz", str(bad)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)["status"], "failed")

    def test_vendor_integrity_matches_provenance(self):
        for record in p.PROVENANCE["files"]:
            filename = Path(record["path"]).name
            path = SKILL / ("scripts/vendor" if filename.endswith(".py") else "references/examples") / filename
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])


if __name__ == "__main__":
    unittest.main()
