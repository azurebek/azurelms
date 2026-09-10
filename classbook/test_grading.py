from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .grading import grade_answer, parse_author_definition, points_for_grade, validate_exercise_payload


class AuthorDefinitionTests(SimpleTestCase):
    def test_single_choice_marks_exactly_one_answer(self):
        config, key = parse_author_definition("single_choice", "Anqara\n*Istanbul\nIzmir")
        self.assertEqual(len(config["options"]), 3)
        self.assertEqual(key["correct"], ["o2"])

    def test_single_choice_rejects_two_correct_answers(self):
        with self.assertRaises(ValidationError):
            parse_author_definition("single_choice", "*A\n*B")

    def test_all_launch_types_are_structured(self):
        samples = {
            "multiple_choice": "*A\nB\n*C",
            "true_false": "ha",
            "short_answer": "merhaba\nMerhaba!",
            "fill_blank": "geliyorum\ngelmekteyim",
            "matching": "salom = merhaba\nxayr = hoşça kal",
            "ordering": "Ben\nbugün\nokula\ngidiyorum",
            "categorization": "Meva: olma, nok\nSabzavot: sabzi, piyoz",
            "unscramble": "Türkçe\nöğreniyorum",
            "poll": "Oson\nO'rtacha\nQiyin",
        }
        for kind, raw in samples.items():
            with self.subTest(kind=kind):
                config, key = parse_author_definition(kind, raw)
                self.assertIsInstance(config, dict)
                self.assertIsInstance(key, dict)


class GraderTests(SimpleTestCase):
    def _payload(self, kind, raw):
        return parse_author_definition(kind, raw)

    def test_choice_and_text_graders(self):
        config, key = self._payload("multiple_choice", "*A\nB\n*C")
        exact = grade_answer("multiple_choice", config, key, ["o1", "o3"])
        penalized = grade_answer("multiple_choice", config, key, ["o1", "o2"])
        self.assertTrue(exact.is_correct)
        self.assertEqual(exact.fraction, Decimal("1"))
        self.assertEqual(penalized.fraction, Decimal("0"))

        config, key = self._payload("short_answer", "İstanbul\nIstanbul")
        self.assertTrue(grade_answer("short_answer", config, key, "  İSTANBUL ").is_correct)

    def test_matching_ordering_and_categories_give_partial_credit(self):
        config, key = self._payload("matching", "salom = merhaba\nxayr = güle güle")
        grade = grade_answer("matching", config, key, {"l1": "r1", "l2": "r1"})
        self.assertEqual(grade.fraction, Decimal("0.5"))

        config, key = self._payload("ordering", "bir\nikki\nuch")
        grade = grade_answer("ordering", config, key, ["i1", "i3", "i2"])
        self.assertEqual(grade.fraction, Decimal("0.3333333333333333333333333333"))

        config, key = self._payload("categorization", "A: bir, ikki\nB: uch")
        grade = grade_answer(
            "categorization", config, key, {"i1": "c1", "i2": "c2", "i3": "c2"}
        )
        self.assertEqual(grade.fraction, Decimal("2") / Decimal("3"))

    def test_poll_is_valid_but_not_graded(self):
        config, key = self._payload("poll", "Oson\nQiyin")
        grade = grade_answer("poll", config, key, "o1")
        self.assertFalse(grade.is_correct)
        self.assertEqual(grade.fraction, 0)

    def test_tampered_answers_and_broken_keys_are_rejected(self):
        config, key = self._payload("true_false", "yo'q")
        with self.assertRaises(ValidationError):
            grade_answer("true_false", config, key, "anything-is-false")

        config, key = self._payload("single_choice", "*A\nB")
        with self.assertRaises(ValidationError):
            grade_answer("single_choice", config, key, "forged-id")
        with self.assertRaises(ValidationError):
            validate_exercise_payload("single_choice", config, {"correct": ["missing"]})

    def test_author_definition_has_bounded_size(self):
        with self.assertRaises(ValidationError):
            parse_author_definition("poll", "\n".join(f"variant-{index}" for index in range(101)))

    def test_speed_is_only_a_capped_bonus(self):
        config, key = self._payload("single_choice", "*A\nB")
        grade = grade_answer("single_choice", config, key, "o1")
        score, maximum, bonus = points_for_grade(
            grade=grade,
            max_points=100,
            speed_bonus_percent=10,
            elapsed_ms=0,
            time_limit_seconds=60,
        )
        self.assertEqual(score, Decimal("110.00"))
        self.assertEqual(maximum, Decimal("110.00"))
        self.assertEqual(bonus, Decimal("10.00"))
