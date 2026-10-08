"""Lossless boundary adapter for the two-document bilingual KC + Quiz ZIP.

The authored documents stay intact inside their language maps.  The adapter
only expands them into the existing preview/workspace representation; it does
not select questions, translate content, or discard unknown authored fields.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import zipfile
from collections.abc import Callable
from typing import Any

from src.core.config import Settings

PAIR_SCHEMA = "kc-quiz-pair.v2"
KC_SCHEMA = "kc-quiz-kc.v2"
QUIZ_SCHEMA = "kc-quiz-quiz.v2"
KC_NAME = "kc.json"
QUIZ_NAME = "quiz.json"
LANGUAGES = ("vi", "en")
_INTAKE_RE = re.compile(r"K[0-9]{2}\Z")
_LEVEL_RE = re.compile(r"L[0-9]{2}\Z")
_DAY_RE = re.compile(r"day\d{2}\Z")


def question_contract_signature(question: dict[str, Any]) -> tuple[Any, ...]:
    """Language-independent scoring and KC lineage for a bilingual question."""
    interaction = question.get("interaction", {})
    answer = question.get("answer_key_or_rubric", {})
    question_type = interaction.get("type")
    if question_type in {"single_select", "multi_select"}:
        interaction_shape = tuple(row.get("choice_id") for row in interaction.get("choices", []))
    elif question_type == "matching":
        interaction_shape = (
            tuple(row.get("id") for row in interaction.get("left", [])),
            tuple(row.get("id") for row in interaction.get("right", [])),
        )
    elif question_type == "ordering":
        interaction_shape = tuple(row.get("option_id") for row in interaction.get("options", []))
    elif question_type == "numeric_input":
        interaction_shape = interaction.get("required_unit")
    else:
        interaction_shape = None

    if question_type == "single_select":
        answer_shape = answer.get("correct_choice_id")
    elif question_type == "multi_select":
        answer_shape = tuple(sorted(answer.get("correct_choice_ids", [])))
    elif question_type == "matching":
        answer_shape = tuple(sorted(answer.get("correct_pairs", {}).items()))
    elif question_type == "ordering":
        answer_shape = tuple(answer.get("correct_order", []))
    elif question_type == "numeric_input":
        answer_shape = (answer.get("value"), answer.get("tolerance"), answer.get("unit"))
    else:
        criteria = answer.get("criteria", [])
        criteria_shape = tuple((row.get("criterion_id"), row.get("points")) for row in criteria)
        answer_shape = (
            answer.get("grading"),
            criteria_shape,
            answer.get("accept_equivalent_wording"),
        )
    return (
        question.get("module_id"),
        question.get("primary_kc_id"),
        tuple(sorted(question.get("contributing_kc_ids", []))),
        tuple(sorted(question.get("assessment_slot_ids", []))),
        question.get("variant_family_id"),
        question.get("role"),
        question.get("grading_method"),
        question.get("cognitive_operation"),
        question.get("estimated_difficulty"),
        question.get("max_points"),
        question.get("question_version"),
        question_type,
        interaction_shape,
        answer_shape,
    )


class PairContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def verify_pair_target(
    identity: Any,
    *,
    course_id: str | None,
    mapping: dict[str, Any] | None,
    target_day: dict[str, Any] | None,
    source_days: list[dict[str, Any]] | None,
) -> None:
    """Compare the ZIP with the course's canonical programme position and Day."""
    if target_day is None:
        raise PairContractError(
            "destination_day_required", "Choose a VLearn course Day before importing KC + Quiz."
        )
    if mapping is None or course_id is None:
        raise PairContractError(
            "curriculum_mapping_missing",
            "This course has no structured programme position for KC + Quiz imports.",
        )
    if (
        not isinstance(identity, dict)
        or any(
            identity.get(key) != mapping.get(key) for key in ("intake", "level", "phase", "track")
        )
        or str(mapping.get("course_id", "")).lower() != course_id.lower()
    ):
        raise PairContractError(
            "curriculum_track_course_mismatch",
            "Package programme position does not match the VLearn destination course.",
        )
    day_mapping = next(
        (row for row in source_days or [] if row.get("source_day") == identity.get("source_day")),
        None,
    )
    if day_mapping is None:
        raise PairContractError(
            "curriculum_day_mapping_missing", "Source Day has no approved VLearn destination."
        )
    if (
        day_mapping.get("learning_day_number") != identity.get("learning_day_number")
        or day_mapping.get("target_day_code") != target_day.get("day_code")
        or str(day_mapping.get("course_id", "")).lower() != course_id.lower()
    ):
        raise PairContractError(
            "curriculum_source_day_mismatch", "Source Day does not map to this VLearn Day."
        )


def expand_pair_archive(
    zf: zipfile.ZipFile,
    entries: dict[str, zipfile.ZipInfo],
    settings: Settings,
    read_entry: Callable[[zipfile.ZipFile, zipfile.ZipInfo, Settings, list[int]], bytes],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Read only the two allowed entries under the ingest layer's size caps."""
    if set(entries) != {KC_NAME, QUIZ_NAME}:
        message = "Two-file KC + Quiz ZIP must contain exactly kc.json and quiz.json"
        raise PairContractError("reject_pair_entries", message)
    expanded_total = [0]
    kc_data = read_entry(zf, entries[KC_NAME], settings, expanded_total)
    quiz_data = read_entry(zf, entries[QUIZ_NAME], settings, expanded_total)
    manifest, files = expand_pair(kc_data, quiz_data)
    if sum(len(data) for data in files.values()) > settings.zip_max_expanded_mb * 1024 * 1024:
        raise PairContractError(
            "reject_expanded_total_too_large",
            "Expanded KC + Quiz documents exceed the archive cap",
        )
    return manifest, files


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PairContractError("invalid_pair_document", f"{label} must be a JSON object")
    return value


def _decode(raw: bytes, label: str) -> dict[str, Any]:
    try:
        return _object(json.loads(raw), label)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PairContractError("invalid_pair_json", f"{label} is not UTF-8 JSON") from exc


def _encoded(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _same_shape(vi: Any, en: Any, path: str) -> None:
    """Keep field parity without forcing localized prose into matching bullet counts.

    Root collections are shared graph structure. Nested lists may split an
    academic explanation differently by language and are preserved verbatim.
    IDs, assessment links, and scoring are checked separately below and by the
    cross-file contract validator.
    """
    if type(vi) is not type(en):  # noqa: E721 -- exact JSON type parity, not isinstance(bool, int)
        raise PairContractError("localized_shape_mismatch", f"VI/EN type differs at {path}")
    if isinstance(vi, dict):
        # Editing one localization invalidates only that localization's
        # imported content hash. Its unchanged peer can keep its source hash.
        optional = (
            {"content_sha256"} if re.fullmatch(r"quiz\.json\.questions\[\d+\]", path) else set()
        )
        if set(vi) - optional != set(en) - optional:
            raise PairContractError("localized_shape_mismatch", f"VI/EN fields differ at {path}")
        for key in vi:
            if key not in optional:
                _same_shape(vi[key], en[key], f"{path}.{key}")
    elif isinstance(vi, list):
        if len(vi) != len(en):
            if path in {
                "kc.json.groups",
                "kc.json.leaf_kcs",
                "kc.json.integrated_activities",
                "quiz.json.questions",
                "quiz.blueprint.modules",
                "quiz.blueprint.assessment_slots",
            }:
                raise PairContractError(
                    "localized_shape_mismatch", f"VI/EN item counts differ at {path}"
                )
            return
        for index, (vi_item, en_item) in enumerate(zip(vi, en, strict=True)):
            _same_shape(vi_item, en_item, f"{path}[{index}]")
    elif isinstance(vi, str) and bool(vi.strip()) != bool(en.strip()):
        raise PairContractError("missing_localized_text", f"VI/EN text is missing at {path}")


def _languages(document: dict[str, Any], label: str, day: str) -> dict[str, dict[str, Any]]:
    rows = _object(document.get("localizations"), f"{label}.localizations")
    if set(rows) != set(LANGUAGES):
        raise PairContractError("missing_bilingual_content", f"{label} needs both vi and en")
    result: dict[str, dict[str, Any]] = {}
    for language in LANGUAGES:
        payload = _object(rows[language], f"{label}.{language}")
        if payload.get("day") != day or payload.get("language") != language:
            raise PairContractError(
                "pair_day_language_mismatch", f"{label}.{language} has a wrong Day or language"
            )
        result[language] = payload
    _same_shape(result["vi"], result["en"], label)
    return result


def _blueprint_structure(blueprint: dict[str, Any]) -> tuple[Any, Any]:
    modules = [
        (
            _object(row, "blueprint.modules item").get("module_id"),
            row.get("leaf_kc_ids"),
            row.get("assessment_slot_ids"),
            row.get("initial_representative_slot_ids"),
        )
        for row in blueprint["modules"]
    ]
    slots = [
        (
            _object(row, "blueprint.assessment_slots item").get("slot_id"),
            row.get("module_id"),
            row.get("kc_id"),
            row.get("variant_question_ids"),
        )
        for row in blueprint["assessment_slots"]
    ]
    return modules, slots


def expand_pair(kc_raw: bytes, quiz_raw: bytes) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Return a generated v1 manifest and full localized documents for v1 internals."""
    kc = _decode(kc_raw, KC_NAME)
    quiz = _decode(quiz_raw, QUIZ_NAME)
    if set(kc) != {"schema_version", "day", "package", "localizations"} or set(quiz) != {
        "schema_version",
        "day",
        "blueprint",
        "localizations",
    }:
        raise PairContractError(
            "unknown_pair_field", "Pair document has missing or unsupported top-level fields"
        )
    if kc["schema_version"] != KC_SCHEMA or quiz["schema_version"] != QUIZ_SCHEMA:
        raise PairContractError("unsupported_pair_schema", "Two-file package schema is unsupported")
    day = kc["day"]
    if not isinstance(day, str) or quiz["day"] != day:
        raise PairContractError("pair_day_mismatch", "KC and Quiz must target the same Day")
    metadata = copy.deepcopy(_object(kc["package"], "kc.package"))
    reserved = {
        "schema_version",
        "source_format",
        "pair_blueprint_en",
        "day",
        "languages",
        "content",
        "counts",
        "files",
    }
    if reserved.intersection(metadata):
        raise PairContractError("reserved_package_field", "kc.package contains a generated field")
    if not isinstance(metadata.get("traceability"), dict) or not isinstance(
        metadata.get("revisions"), dict
    ):
        raise PairContractError("missing_pair_metadata", "Traceability and revisions are required")
    if not isinstance(metadata.get("curriculum_decisions"), dict):
        raise PairContractError("missing_pair_metadata", "Curriculum decisions are required")
    identity = metadata.get("curriculum_identity")
    if not isinstance(identity, dict):
        raise PairContractError(
            "invalid_curriculum_identity", "KC package needs a curriculum identity"
        )
    if set(identity) != {
        "intake",
        "level",
        "phase",
        "track",
        "source_day",
        "learning_day_number",
    }:
        raise PairContractError(
            "invalid_curriculum_identity",
            "Curriculum identity needs programme position and both Days",
        )
    if (
        not isinstance(identity["intake"], str)
        or _INTAKE_RE.fullmatch(identity["intake"]) is None
        or not isinstance(identity["level"], str)
        or _LEVEL_RE.fullmatch(identity["level"]) is None
        or type(identity["phase"]) is not int
        or not 1 <= identity["phase"] <= 9
        or type(identity["track"]) is not int
        or not 0 <= identity["track"] <= 9
        or not isinstance(identity["source_day"], str)
        or _DAY_RE.fullmatch(identity["source_day"]) is None
    ):
        raise PairContractError(
            "invalid_curriculum_identity", "Curriculum position or source Day is invalid"
        )
    number = identity["learning_day_number"]
    if type(number) is not int or not 1 <= number <= 99 or day != f"day{number:02d}":
        raise PairContractError(
            "curriculum_day_mismatch", "Curriculum Day must equal the KC/Quiz package Day"
        )
    materials = metadata.get("materials", [])
    if not isinstance(materials, list) or any(
        not isinstance(row, dict) or "file" in row for row in materials
    ):
        raise PairContractError(
            "invalid_pair_materials", "Pair ZIP can only reference external materials"
        )
    kc_local = _languages(kc, KC_NAME, day)
    quiz_local = _languages(quiz, QUIZ_NAME, day)
    vi_activities = kc_local["vi"].get("integrated_activities", [])
    en_activities = kc_local["en"].get("integrated_activities", [])
    if not isinstance(vi_activities, list) or not isinstance(en_activities, list):
        raise PairContractError("invalid_pair_content", "Integrated activities must be lists")
    for vi_activity, en_activity in zip(vi_activities, en_activities, strict=True):
        vi_row = _object(vi_activity, "kc.vi.integrated_activity")
        en_row = _object(en_activity, "kc.en.integrated_activity")
        if vi_row.get("classification") != en_row.get("classification") or vi_row.get(
            "component_kc_ids"
        ) != en_row.get("component_kc_ids"):
            raise PairContractError(
                "localized_kc_structure_mismatch",
                "VI/EN integrated activities disagree on classification or KC links",
            )
    questions_by_language: dict[str, dict[str, dict[str, Any]]] = {}
    for language in LANGUAGES:
        rows = quiz_local[language].get("questions")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise PairContractError(
                "invalid_pair_content", f"quiz.{language}.questions must be objects"
            )
        questions_by_language[language] = {
            row["question_id"]: row for row in rows if isinstance(row.get("question_id"), str)
        }
        if len(questions_by_language[language]) != len(rows):
            raise PairContractError(
                "invalid_pair_content", f"quiz.{language}.questions need unique IDs"
            )
    if set(questions_by_language["vi"]) != set(questions_by_language["en"]):
        raise PairContractError("localized_question_mismatch", "VI/EN question IDs differ")
    for question_id, vi_question in questions_by_language["vi"].items():
        en_question = questions_by_language["en"][question_id]
        try:
            vi_signature = question_contract_signature(vi_question)
            en_signature = question_contract_signature(en_question)
        except (AttributeError, TypeError) as exc:
            raise PairContractError(
                "invalid_pair_content", f"Question {question_id} has an invalid answer structure"
            ) from exc
        if vi_signature != en_signature:
            raise PairContractError(
                "localized_question_contract_drift",
                f"VI/EN scoring or lineage differs for {question_id}",
            )
    blueprints = _object(quiz["blueprint"], "quiz.blueprint")
    if set(blueprints) != set(LANGUAGES):
        raise PairContractError("missing_bilingual_content", "Blueprint needs both vi and en")
    blueprint = _object(blueprints["vi"], "quiz.blueprint.vi")
    blueprint_en = _object(blueprints["en"], "quiz.blueprint.en")
    if blueprint.get("day") != day or blueprint_en.get("day") != day:
        raise PairContractError("pair_day_mismatch", "Blueprint targets a different Day")
    _same_shape(blueprint, blueprint_en, "quiz.blueprint")
    for key, id_key in (("modules", "module_id"), ("assessment_slots", "slot_id")):
        vi_rows, en_rows = blueprint.get(key), blueprint_en.get(key)
        if not isinstance(vi_rows, list) or not isinstance(en_rows, list):
            raise PairContractError("invalid_pair_blueprint", f"Blueprint {key} must be a list")
        if [_object(row, f"blueprint.{key} item").get(id_key) for row in vi_rows] != [
            _object(row, f"blueprint.{key} item").get(id_key) for row in en_rows
        ]:
            raise PairContractError(
                "localized_blueprint_mismatch", f"VI/EN blueprint {key} IDs differ"
            )
    if _blueprint_structure(blueprint) != _blueprint_structure(blueprint_en):
        raise PairContractError(
            "localized_blueprint_mismatch", "VI/EN blueprint relationships differ"
        )
    files: dict[str, bytes] = {}
    kc_paths = []
    bank_paths = []
    for language in LANGUAGES:
        kc_path = f"kc/knowledge-components.{language}.json"
        bank_path = f"quiz/quiz-bank.{language}.json"
        files[kc_path] = _encoded(kc_local[language])
        files[bank_path] = _encoded(quiz_local[language])
        kc_paths.append({"language": language, "file": kc_path})
        bank_paths.append({"language": language, "file": bank_path})
    files["quiz/blueprint.json"] = _encoded(blueprint)
    vi_kc = kc_local["vi"]
    vi_bank = quiz_local["vi"]
    count_sources = {
        "kc_groups": vi_kc.get("groups", []),
        "leaf_kcs": vi_kc.get("leaf_kcs", []),
        "integrated_activities": vi_kc.get("integrated_activities", []),
        "assessment_slots": blueprint.get("assessment_slots", []),
        "questions": vi_bank.get("questions", []),
        "materials": materials,
    }
    for key, rows in count_sources.items():
        if not isinstance(rows, list):
            raise PairContractError("invalid_pair_content", f"{key} must be a list")
    counts = {key: len(rows) for key, rows in count_sources.items()}
    manifest = {
        **metadata,
        "schema_version": "kc-quiz-package.v1",
        "source_format": PAIR_SCHEMA,
        "pair_blueprint_en": blueprint_en,
        "day": day,
        "languages": list(LANGUAGES),
        "content": {
            "knowledge_components": kc_paths,
            "quiz_blueprint": "quiz/blueprint.json",
            "quiz_banks": bank_paths,
        },
        "counts": counts,
        "files": [
            {"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            for path, data in files.items()
        ],
    }
    return manifest, files


def pack_pair(manifest: dict[str, Any], snapshot: dict[str, Any]) -> tuple[bytes, bytes]:
    """Rebuild the two authored JSON documents from a full workspace snapshot."""
    metadata = copy.deepcopy(manifest)
    blueprint_en = snapshot.get("pair_blueprint_en", metadata.pop("pair_blueprint_en", None))
    for key in (
        "schema_version",
        "source_format",
        "day",
        "languages",
        "content",
        "counts",
        "files",
    ):
        metadata.pop(key, None)
    metadata["materials"] = [
        {key: value for key, value in row.items() if key != "file"}
        for row in snapshot.get("materials", [])
    ]
    day = manifest["day"]
    kc_local = {row["language"]: row["payload"] for row in snapshot["knowledge_components"]}
    quiz_local = {row["language"]: row["payload"] for row in snapshot["quiz_banks"]}
    kc = {"schema_version": KC_SCHEMA, "day": day, "package": metadata, "localizations": kc_local}
    quiz = {
        "schema_version": QUIZ_SCHEMA,
        "day": day,
        "blueprint": {"vi": snapshot["quiz_blueprint"]["payload"], "en": blueprint_en},
        "localizations": quiz_local,
    }
    kc_raw, quiz_raw = _encoded(kc), _encoded(quiz)
    expand_pair(kc_raw, quiz_raw)
    return kc_raw, quiz_raw
