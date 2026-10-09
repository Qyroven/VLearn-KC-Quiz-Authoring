import copy
import json
from pathlib import Path
import sys
import unittest

SKILL = Path(__file__).resolve().parents[1] / 'skills/vlearn-kc-quiz-authoring'
sys.path.insert(0, str(SKILL / 'scripts'))
import authoring_evidence as a


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.kc, self.quiz, self.ctx = [json.loads((SKILL / 'references/examples' / n).read_text()) for n in ('kc.json', 'quiz.json', 'context.json')]
        self.ext = {'schema_version': 'source-extraction.v1', 'sources': [{'source_id': 'source-a', 'sha256': 'a' * 64, 'page_count': 1}],
                    'pages': [{'source_id': 'source-a', 'page': 1, 'page_label': 'slide 2', 'raw_text': 'Synthetic arithmetic fixture',
                               'blocks': [{'kind': 'text', 'content': 'Technical test fixture: add small integers.'}], 'page_note': 'Only the synthetic addition claim is used.',
                               'status': 'reviewed', 'exclusion_reason': ''}]}
        self.evidence = a.scaffold(*self.inputs())
        self.evidence.update(reviewer='test-fixture-author', reviewed_at='2026-10-09T10:00:00+07:00')
        self.evidence['coverage'][0].update(status='assessed', question_ids=['q1', 'q2'], rationale='Two arithmetic variants assess addition.')
        for q in self.evidence['questions']:
            q.update(source_refs=[{'source_id': 'source-a', 'page': 1}], solution_work='Calculate the sum independently.',
                     alternatives_checked='The other value differs from the computed sum.', scope_check='Only addition is needed.',
                     hint_check='No hints supplied; no hidden givens.', translation_check='Both languages retain operands and answer choices.', status='self_reviewed')

    def inputs(self):
        return [raw(x) for x in (self.kc, self.quiz, self.ctx, self.ext)]

    def report(self):
        return a.check(*self.inputs(), raw(self.evidence))

    def codes(self):
        return {x['code'] for x in self.report()['blockers']}

    def test_complete_records_are_not_semantic_or_independent_approval(self):
        result = self.report()
        self.assertEqual(result['status'], 'work_records_complete_needs_semantic_review')
        self.assertIn('semantic_correctness', result['not_verified'])
        self.assertIn('independent_approval', result['not_verified'])

    def test_scaffold_cannot_pass_as_review(self):
        self.evidence = a.scaffold(*self.inputs())
        self.assertIn('question_review_open', self.codes())
        self.assertIn('coverage_unreviewed', self.codes())

    def test_edit_invalidates_bound_review(self):
        for obj, mutate in (
            (self.ext, lambda: self.ext['pages'][0].update(page_note='Changed source interpretation')),
            (self.ctx, lambda: self.ctx['request'].update(question_count=2)),
            (self.quiz, lambda: self.quiz['localizations']['vi']['questions'][0]['interaction'].update(prompt='Changed prompt')),
        ):
            old = copy.deepcopy(obj)
            mutate()
            self.assertIn('review_stale', self.codes())
            obj.clear(); obj.update(old)

    def test_missing_page_inventory_fails(self):
        self.ext['sources'][0]['page_count'] = 2
        with self.assertRaises(ValueError): self.report()

    def test_pending_page_and_exclusion_without_reason_block(self):
        self.ext['pages'][0]['status'] = 'pending'
        self.assertIn('page_unreviewed', self.codes())
        self.ext['pages'][0]['status'] = 'excluded'
        self.assertIn('page_exclusion_unexplained', self.codes())

    def test_sources_refs_use_physical_page_numbers(self):
        self.evidence['questions'][0]['source_refs'][0]['page'] = 2
        self.assertIn('question_source_evidence_missing', self.codes())

    def test_cannot_cite_excluded_page_as_question_evidence(self):
        self.ext['pages'][0].update(status='excluded', exclusion_reason='Outside scope')
        self.assertIn('question_source_evidence_missing', self.codes())

    def test_open_academic_finding_blocks_even_with_self_reviewed_label(self):
        self.evidence['questions'][0]['findings'] = [{'status': 'open', 'detail': 'A second answer is defensible.'}]
        self.assertIn('academic_finding_open', self.codes())
        self.evidence['questions'][0]['findings'][0]['status'] = 'resolved'
        self.assertIn('finding_resolution_missing', self.codes())

    def test_coverage_wrong_question_link_fails(self):
        self.evidence['coverage'][0]['question_ids'] = ['not-in-bank']
        with self.assertRaises(ValueError): self.report()

    def test_recovery_open_and_context_sync_required(self):
        gap = {'issue_id': 'gap-1', 'source_id': 'source-a', 'page': 1, 'missing_fact': 'Operand unreadable',
               'attempts': [{'method': 'render_crop', 'artifact': 'attempt/attempt.json', 'result': 'Still ambiguous'}],
               'status': 'needs_source', 'affected_question_ids': ['q1'], 'next_action': 'Request original page 1'}
        self.evidence['source_recovery'] = [gap]
        self.assertIn('source_gap_open', self.codes())
        self.assertIn('context_recovery_out_of_sync', self.codes())
        self.ctx['open_source_gaps'] = [{'issue_id': 'gap-1', 'affected_question_ids': ['q1']}]
        result = self.report()
        self.assertNotIn('context_recovery_out_of_sync', {x['code'] for x in result['blockers']})
        self.assertNotIn('q1', result['context_plan']['candidate_question_ids'])

    def test_recovered_label_needs_fact_and_verification(self):
        self.evidence['source_recovery'] = [{'issue_id': 'gap-1', 'source_id': 'source-a', 'page': 1, 'missing_fact': 'Operand',
                                            'attempts': [], 'status': 'recovered_verified', 'affected_question_ids': ['q1']}]
        self.assertIn('recovery_attempt_missing', self.codes())
        self.assertIn('recovery_verification_missing', self.codes())

    def test_short_text_requires_score_trials_and_rejects_out_of_range_score(self):
        for lang in ('vi', 'en'):
            q = self.quiz['localizations'][lang]['questions'][0]
            q.update(interaction={'type': 'short_text', 'prompt': 'Explain addition.'},
                     answer_key_or_rubric={'grading': 'rubric', 'exemplar_answer': 'Sum the operands',
                                          'criteria': [{'criterion_id': 'c1', 'description': 'Method', 'points': 1, 'allowed_scores': [0, 1]}]})
        self.assertIn('rubric_trials_missing', self.codes())
        self.evidence['questions'][0]['rubric_trials'] = [{'case': case, 'response': 'Example ' + case, 'score': score, 'rationale': 'Applied criterion c1.'} for case, score in [('correct', 1), ('partial', 0), ('incorrect', 0)]]
        self.assertNotIn('rubric_trials_missing', self.codes())
        self.evidence['questions'][0]['rubric_trials'][0]['score'] = 2
        self.assertIn('rubric_trial_incomplete', self.codes())

    def test_review_timestamp_requires_timezone_and_time(self):
        for value in ('2026-10-09', '2026-10-09T10:00:00'):
            self.evidence['reviewed_at'] = value
            self.assertIn('review_timestamp_invalid', self.codes())

    def test_review_cannot_complete_without_question_scope_annotation(self):
        self.ctx['question_annotations'].pop()
        self.assertIn('question_scope_annotation_missing', self.codes())

    def test_missing_review_record_fails(self):
        self.evidence['questions'].pop()
        with self.assertRaises(ValueError): self.report()

    def test_independent_claim_is_rejected(self):
        self.evidence['review_kind'] = 'independently_approved'
        with self.assertRaises(ValueError): self.report()


if __name__ == '__main__':
    unittest.main()
