"""Learner-facing review data comes only from an explicit publication.

Draft rows stay editable by staff. This is the last approved presentation,
not a second grading engine, event history, or certificate reissue policy.
"""
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.utils.dateparse import parse_datetime


def publication_payload(attempt, reviews):
    """Called only by canonical finalize_review, using its exact scoring rows."""
    return {
        'version': 1,
        'score': str(attempt.score),
        'passed': attempt.passed,
        'passing_score': attempt.exam.passing_score,
        'review_notes': attempt.review_notes,
        'reviewed_at': attempt.reviewed_at.isoformat(),
        'section_reviews': [
            {
                'section': {
                    'title': review.section.title,
                    'section_type': review.section.section_type,
                    'get_section_type_display': review.section.get_section_type_display(),
                    'max_score': review.section.max_score,
                },
                'awarded_score': str(review.awarded_score),
                'feedback': review.feedback,
            } for review in reviews
        ],
        'feedback_answers': [
            {
                'question': {
                    'text': str(answer.question.text),
                    'points': answer.question.points,
                    'exam_section': {
                        'get_section_type_display': answer.question.exam_section.get_section_type_display()
                        if answer.question.exam_section_id else 'Savol',
                    },
                },
                'awarded_score': str(answer.awarded_score),
                'grader_feedback': answer.grader_feedback,
            }
            for answer in attempt.answers.exclude(grader_feedback='').select_related('question__exam_section').order_by('question__exam_section__order', 'question_id')
        ],
    }


def learner_result(attempt):
    """Never fall back to live draft feedback, even for an old reviewed attempt."""
    result = dict(is_reviewed=False, score=None, passed=False, passing_score=None,
                  review_notes='', reviewed_at=None, section_reviews=[],
                  feedback_answers=[], details_unavailable=False)
    if not attempt or not attempt.is_completed or not attempt.is_reviewed:
        return result
    try:
        payload = attempt.result_publication.payload
    except ObjectDoesNotExist:
        payload = None
    if payload:
        result.update(payload)
        result['is_reviewed'] = True
        result['score'] = Decimal(payload['score'])
        result['reviewed_at'] = parse_datetime(payload['reviewed_at'])
    else:
        # Pre-migration rows have an approved aggregate but no provable
        # publication of their mutable section/answer feedback. Do not invent one.
        result.update(is_reviewed=True, score=attempt.score, passed=attempt.passed,
                      reviewed_at=attempt.reviewed_at, details_unavailable=True)
    return result
