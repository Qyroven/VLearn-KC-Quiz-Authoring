"""Cross-file structural contract checks for a canonical KC + Quiz package."""

from __future__ import annotations

from typing import Any

from src.modules.content.service_kc_quiz_contract_error import KcQuizContractError


def _objects(value: Any, *, code: str, ref: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise KcQuizContractError(code, f"{ref} must be an array of objects.", ref)
    return value


def _ids(rows: list[dict[str, Any]], key: str, *, ref: str) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise KcQuizContractError("missing_id", f"Every {ref} needs {key}.", ref)
        values.append(value)
    if len(values) != len(set(values)):
        raise KcQuizContractError("duplicate_id", f"{ref} contains a duplicate {key}.", ref)
    return values


def _string_refs(value: Any, *, ref: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise KcQuizContractError("invalid_reference_list", f"{ref} must be a string array.", ref)
    return value


def _require_known(values: list[str], known: set[str], *, code: str, ref: str) -> None:
    unknown = sorted(set(values) - known)
    if unknown:
        raise KcQuizContractError(code, f"Unknown reference: {unknown[0]}.", ref)


def _answer_error(code: str, message: str, question_id: str) -> None:
    raise KcQuizContractError(code, message, question_id)


def _interaction_ids(
    interaction: dict[str, Any],
    key: str,
    id_key: str,
    *,
    question_id: str,
) -> list[str]:
    try:
        rows = _objects(
            interaction.get(key),
            code="invalid_question_interaction",
            ref=question_id,
        )
        return _ids(rows, id_key, ref=question_id)
    except KcQuizContractError as exc:
        _answer_error("invalid_question_interaction", exc.message, question_id)


def validate_question_answer(question: dict[str, Any]) -> None:
    """Prove that a question's scoring key addresses its interaction by stable IDs."""

    question_id = str(question["question_id"])
    interaction = question.get("interaction")
    answer = question.get("answer_key_or_rubric")
    if not isinstance(interaction, dict):
        _answer_error(
            "invalid_question_interaction",
            "Question interaction must be an object.",
            question_id,
        )
    if not isinstance(answer, dict):
        _answer_error(
            "invalid_question_answer",
            "Question answer_key_or_rubric must be an object.",
            question_id,
        )
    question_type = interaction.get("type")
    if question_type not in {
        "single_select",
        "multi_select",
        "matching",
        "ordering",
        "numeric_input",
        "short_text",
    }:
        _answer_error(
            "unsupported_question_type",
            f"Unsupported question interaction type: {question_type}.",
            question_id,
        )

    if question_type in {"single_select", "multi_select"}:
        choice_ids = _interaction_ids(
            interaction,
            "choices",
            "choice_id",
            question_id=question_id,
        )
        known_choices = set(choice_ids)
        if question_type == "single_select":
            correct = answer.get("correct_choice_id")
            if not isinstance(correct, str) or correct not in known_choices:
                _answer_error(
                    "unknown_correct_choice",
                    "Single-select answer must name one choice_id present in interaction.choices.",
                    question_id,
                )
        else:
            correct = answer.get("correct_choice_ids")
            if (
                not isinstance(correct, list)
                or not correct
                or any(not isinstance(item, str) for item in correct)
                or len(correct) != len(set(correct))
                or not set(correct).issubset(known_choices)
            ):
                _answer_error(
                    "unknown_correct_choice",
                    "Multi-select answer must name unique choice_ids "
                    "present in interaction.choices.",
                    question_id,
                )
        return

    if question_type == "matching":
        left_ids = _interaction_ids(interaction, "left", "id", question_id=question_id)
        right_ids = set(_interaction_ids(interaction, "right", "id", question_id=question_id))
        pairs = answer.get("correct_pairs")
        if (
            not isinstance(pairs, dict)
            or set(pairs) != set(left_ids)
            or any(not isinstance(value, str) or value not in right_ids for value in pairs.values())
        ):
            _answer_error(
                "invalid_matching_answer",
                "Matching answer must map every left ID to a declared right ID.",
                question_id,
            )
        return

    if question_type == "ordering":
        option_ids = _interaction_ids(
            interaction,
            "options",
            "option_id",
            question_id=question_id,
        )
        correct_order = answer.get("correct_order")
        if (
            not isinstance(correct_order, list)
            or any(not isinstance(item, str) for item in correct_order)
            or len(correct_order) != len(set(correct_order))
            or set(correct_order) != set(option_ids)
        ):
            _answer_error(
                "invalid_ordering_answer",
                "Ordering answer must be an exact permutation of interaction option IDs.",
                question_id,
            )
        return

    if question_type == "numeric_input":
        value = answer.get("value")
        tolerance = answer.get("tolerance")
        unit = answer.get("unit")
        required_unit = interaction.get("required_unit")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or isinstance(tolerance, bool)
            or not isinstance(tolerance, (int, float))
            or tolerance < 0
            or not isinstance(unit, str)
            or (isinstance(required_unit, str) and required_unit and required_unit != unit)
        ):
            _answer_error(
                "invalid_numeric_answer",
                "Numeric answer needs a number, non-negative tolerance and matching unit.",
                question_id,
            )
        return

    criteria = answer.get("criteria")
    if not isinstance(answer.get("exemplar_answer"), str) or not answer["exemplar_answer"].strip():
        _answer_error(
            "invalid_short_text_rubric",
            "Short-text rubric needs a non-empty exemplar_answer.",
            question_id,
        )
    if not isinstance(criteria, list) or not criteria:
        _answer_error(
            "invalid_short_text_rubric",
            "Short-text rubric needs at least one scoring criterion.",
            question_id,
        )
    criterion_ids: list[str] = []
    total_points = 0.0
    for criterion in criteria:
        if not isinstance(criterion, dict):
            _answer_error(
                "invalid_short_text_rubric",
                "Each short-text criterion must be an object.",
                question_id,
            )
        criterion_id = criterion.get("criterion_id")
        description = criterion.get("description")
        points = criterion.get("points")
        if (
            not isinstance(criterion_id, str)
            or not criterion_id
            or not isinstance(description, str)
            or not description.strip()
            or isinstance(points, bool)
            or not isinstance(points, (int, float))
            or points <= 0
        ):
            _answer_error(
                "invalid_short_text_rubric",
                "Each short-text criterion needs an ID, description and positive points.",
                question_id,
            )
        criterion_ids.append(criterion_id)
        total_points += float(points)
    if len(criterion_ids) != len(set(criterion_ids)):
        _answer_error(
            "invalid_short_text_rubric",
            "Short-text criterion IDs must be unique.",
            question_id,
        )
    max_points = question.get("max_points")
    if (
        isinstance(max_points, bool)
        or not isinstance(max_points, (int, float))
        or float(max_points) != total_points
    ):
        _answer_error(
            "invalid_short_text_rubric",
            "Short-text max_points must equal the sum of rubric criterion points.",
            question_id,
        )


def _source_inventory(
    manifest: dict[str, Any], actual_material_pages: dict[str, int]
) -> tuple[dict[str, str], set[str], dict[str, int]]:
    traceability = manifest.get("traceability")
    if not isinstance(traceability, dict):
        raise KcQuizContractError("missing_traceability", "Traceability metadata is required.")
    mappings = _objects(
        traceability.get("source_mappings", []),
        code="invalid_traceability",
        ref="traceability.source_mappings",
    )
    unbundled = _objects(
        traceability.get("unbundled_source_refs", []),
        code="invalid_traceability",
        ref="traceability.unbundled_source_refs",
    )
    mapped_paths: dict[str, str] = {}
    for row in mappings:
        path = row.get("extraction_path")
        material_id = row.get("material_id")
        if not isinstance(path, str) or not isinstance(material_id, str):
            raise KcQuizContractError(
                "invalid_source_mapping",
                "Each source mapping needs extraction_path and material_id.",
            )
        if material_id not in actual_material_pages:
            raise KcQuizContractError(
                "unknown_material_reference",
                f"Source mapping names unknown material {material_id}.",
                path,
            )
        mapped_paths[path] = material_id
    external_paths = {
        row["extraction_path"] for row in unbundled if isinstance(row.get("extraction_path"), str)
    }
    pages_by_path = {
        path: actual_material_pages[material_id] for path, material_id in mapped_paths.items()
    }
    return mapped_paths, external_paths, pages_by_path


def _validate_source_refs(
    owners: list[dict[str, Any]],
    *,
    owner_id: str,
    mapped_paths: dict[str, str],
    external_paths: set[str],
    pages_by_path: dict[str, int],
) -> int:
    checked = 0
    known_paths = set(mapped_paths) | external_paths
    for owner in owners:
        source_refs = _objects(
            owner.get("source_refs", []),
            code="invalid_source_refs",
            ref=f"{owner_id}.source_refs",
        )
        for source_ref in source_refs:
            path = source_ref.get("extraction_path")
            if not isinstance(path, str) or path not in known_paths:
                raise KcQuizContractError(
                    "unknown_source_reference",
                    "A source reference is not declared in package traceability.",
                    str(path),
                )
            page = source_ref.get("page")
            if page is not None:
                if not isinstance(page, int) or page < 1:
                    raise KcQuizContractError(
                        "invalid_source_page", "Source page must be a positive integer.", path
                    )
                maximum = pages_by_path.get(path)
                if maximum is not None and page > maximum:
                    raise KcQuizContractError(
                        "source_page_out_of_range",
                        f"Source page {page} exceeds the packaged PDF's {maximum} pages.",
                        path,
                    )
            checked += 1
    return checked


def validate_content_graph(
    *,
    manifest: dict[str, Any],
    kc_documents: list[dict[str, Any]],
    blueprint: dict[str, Any],
    banks: list[dict[str, Any]],
    actual_material_pages: dict[str, int],
) -> dict[str, int]:
    """Reject broken IDs, relationships, lineage paths and source pages."""

    if not kc_documents or not banks:
        raise KcQuizContractError("incomplete_content", "KC and quiz documents are required.")

    canonical_groups: set[str] | None = None
    canonical_kcs: set[str] | None = None
    kc_source_owners: list[dict[str, Any]] = []
    for document in kc_documents:
        groups = _objects(document.get("groups"), code="invalid_kc", ref="groups")
        leaf_kcs = _objects(document.get("leaf_kcs"), code="invalid_kc", ref="leaf_kcs")
        activities = _objects(
            document.get("integrated_activities", []),
            code="invalid_kc",
            ref="integrated_activities",
        )
        group_ids = set(_ids(groups, "group_id", ref="groups"))
        kc_ids = set(_ids(leaf_kcs, "kc_id", ref="leaf_kcs"))
        if canonical_groups is not None and group_ids != canonical_groups:
            raise KcQuizContractError(
                "localized_kc_mismatch", "Localized KC files must contain the same group IDs."
            )
        if canonical_kcs is not None and kc_ids != canonical_kcs:
            raise KcQuizContractError(
                "localized_kc_mismatch", "Localized KC files must contain the same KC IDs."
            )
        canonical_groups, canonical_kcs = group_ids, kc_ids
        for group in groups:
            _require_known(
                _string_refs(group.get("leaf_kc_ids"), ref="group.leaf_kc_ids"),
                kc_ids,
                code="unknown_group_kc",
                ref=str(group["group_id"]),
            )
        for kc in leaf_kcs:
            if kc.get("group_id") not in group_ids:
                raise KcQuizContractError(
                    "unknown_kc_group", "A KC points to an unknown group.", str(kc["kc_id"])
                )
        for activity in activities:
            _require_known(
                _string_refs(activity.get("component_kc_ids"), ref="activity.component_kc_ids"),
                kc_ids,
                code="unknown_activity_kc",
                ref=str(activity.get("activity", "integrated_activity")),
            )
        kc_source_owners.extend(leaf_kcs)
        kc_source_owners.extend(activities)
    assert canonical_groups is not None and canonical_kcs is not None
    modules = _objects(blueprint.get("modules", []), code="invalid_blueprint", ref="modules")
    slots = _objects(
        blueprint.get("assessment_slots"), code="invalid_blueprint", ref="assessment_slots"
    )
    module_ids = set(_ids(modules, "module_id", ref="modules"))
    slot_ids = set(_ids(slots, "slot_id", ref="assessment_slots"))
    for module in modules:
        _require_known(
            _string_refs(module.get("leaf_kc_ids"), ref="module.leaf_kc_ids"),
            canonical_kcs,
            code="unknown_module_kc",
            ref=str(module["module_id"]),
        )
        _require_known(
            _string_refs(module.get("assessment_slot_ids"), ref="module.assessment_slot_ids"),
            slot_ids,
            code="unknown_module_slot",
            ref=str(module["module_id"]),
        )
        _require_known(
            _string_refs(
                module.get("initial_representative_slot_ids"),
                ref="module.initial_representative_slot_ids",
            ),
            slot_ids,
            code="unknown_representative_slot",
            ref=str(module["module_id"]),
        )
    for slot in slots:
        if slot.get("kc_id") not in canonical_kcs:
            raise KcQuizContractError(
                "unknown_slot_kc", "A slot points to an unknown KC.", str(slot["slot_id"])
            )
        if module_ids and slot.get("module_id") not in module_ids:
            raise KcQuizContractError(
                "unknown_slot_module", "A slot points to an unknown module.", str(slot["slot_id"])
            )

    question_source_owners: list[dict[str, Any]] = []
    canonical_question_ids: set[str] | None = None
    for bank in banks:
        questions = _objects(bank.get("questions"), code="invalid_quiz_bank", ref="questions")
        question_ids = set(_ids(questions, "question_id", ref="questions"))
        if canonical_question_ids is not None and question_ids != canonical_question_ids:
            raise KcQuizContractError(
                "localized_quiz_mismatch",
                "Localized quiz banks must contain the same question IDs.",
            )
        canonical_question_ids = question_ids
        for question in questions:
            question_id = str(question["question_id"])
            validate_question_answer(question)
            question_slots = _string_refs(
                question.get("assessment_slot_ids"), ref="question.assessment_slot_ids"
            )
            if not question_slots:
                raise KcQuizContractError(
                    "question_without_slot",
                    "Every question must reference an assessment slot.",
                    question_id,
                )
            _require_known(question_slots, slot_ids, code="unknown_question_slot", ref=question_id)
            if question.get("primary_kc_id") not in canonical_kcs:
                raise KcQuizContractError(
                    "unknown_question_kc",
                    "A question points to an unknown primary KC.",
                    question_id,
                )
            _require_known(
                _string_refs(
                    question.get("contributing_kc_ids"), ref="question.contributing_kc_ids"
                ),
                canonical_kcs,
                code="unknown_question_kc",
                ref=question_id,
            )
            if module_ids and question.get("module_id") not in module_ids:
                raise KcQuizContractError(
                    "unknown_question_module",
                    "A question points to an unknown module.",
                    question_id,
                )
        question_source_owners.extend(questions)

    assert canonical_question_ids is not None
    for slot in slots:
        _require_known(
            _string_refs(slot.get("variant_question_ids"), ref="slot.variant_question_ids"),
            canonical_question_ids,
            code="unknown_slot_question",
            ref=str(slot["slot_id"]),
        )
    mapped_paths, external_paths, pages_by_path = _source_inventory(manifest, actual_material_pages)
    checked_refs = _validate_source_refs(
        kc_source_owners,
        owner_id="kc",
        mapped_paths=mapped_paths,
        external_paths=external_paths,
        pages_by_path=pages_by_path,
    )
    checked_refs += _validate_source_refs(
        question_source_owners,
        owner_id="question",
        mapped_paths=mapped_paths,
        external_paths=external_paths,
        pages_by_path=pages_by_path,
    )
    return {
        "kc_ids": len(canonical_kcs),
        "slot_ids": len(slot_ids),
        "question_ids": len(canonical_question_ids),
        "source_references": checked_refs,
    }
