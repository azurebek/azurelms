"""Enrollment transition qulfi PostgreSQL'da ham ishlashi (A1a CI topilmasi).

CI ning PostgreSQL ishi ochgan xato: `select_for_update()` bilan birga
`select_related("plan")` ishlatilar edi. `plan` nullable FK, ya'ni Django LEFT
OUTER JOIN yasaydi, PostgreSQL esa "FOR UPDATE cannot be applied to the
nullable side of an outer join" deb butun so'rovni rad etadi. Transfer va
promotion productionda birinchi chaqiruvdayoq yiqilardi.

SQLite'da `has_select_for_update = False` — Django `FOR UPDATE` bandini
jimgina tushirib qoldiradi, shuning uchun bu yerda backend imkoniyatlari
vaqtincha PostgreSQL'niki kabi ko'rsatiladi va **yaralgan SQL** tekshiriladi.
Haqiqiy isbot esa CI ning `integration` ishida: o'sha suite real PostgreSQL'da
yugiradi.
"""

from unittest import mock

from django.db import connection
from django.test import TestCase

from cohorts.transition_service import locked_enrollment_queryset


def _compile_with_postgres_like_features(queryset):
    """SQLite'da turib `FOR UPDATE` bandi qanday yozilishini ko'radi."""
    features = connection.features
    with mock.patch.object(type(features), "has_select_for_update", True), \
            mock.patch.object(type(features), "has_select_for_update_of", True):
        sql, _params = queryset.query.get_compiler(using="default").as_sql()
    return sql


class EnrollmentLockingSqlTests(TestCase):
    """`TestCase` — kompilyator `select_for_update` uchun ochiq tranzaksiya talab qiladi."""

    def test_the_locked_read_joins_a_nullable_relation(self):
        """Muammoning sharti: eager-load ichida LEFT OUTER JOIN bor."""
        sql = _compile_with_postgres_like_features(locked_enrollment_queryset())
        self.assertIn("LEFT OUTER JOIN", sql)

    def test_the_lock_targets_only_the_enrollment_row(self):
        """`FOR UPDATE OF` bo'lmasa PostgreSQL so'rovni butunlay rad etadi."""
        sql = _compile_with_postgres_like_features(locked_enrollment_queryset())
        self.assertIn("FOR UPDATE OF", sql)
        self.assertIn("cohorts_enrollment", sql.split("FOR UPDATE OF", 1)[1])

    def test_no_bare_for_update_is_emitted(self):
        sql = _compile_with_postgres_like_features(locked_enrollment_queryset())
        tail = sql.split("FOR UPDATE", 1)[1]
        self.assertTrue(tail.startswith(" OF"), f"Yalang'och FOR UPDATE: ...{tail[:40]}")
