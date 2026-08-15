"""A1a — CI ning supply-chain gate'i: sir skaneri va zaiflik reyestri.

Ikkala gate ham "topilmadi" deb yashil bo'lishi juda oson, shuning uchun bu yerdagi
asosiy da'vo — ular **haqiqatan ham topa oladi**. Har bir qoida uchun soxta sir
yozib, uning ushlanishi tekshiriladi; shundan keyingina real repo toza degan
tasdiq biror narsani anglatadi.
"""

import json
import subprocess
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from core.dependency_audit import (
    DependencyAuditError,
    baseline_path,
    compare,
    load_json,
    report_findings,
    review_overdue,
)
from core.secret_scan import scan_repository, scan_text, tracked_env_files

# Soxta, ammo formati haqiqiy sirlar. Skaner ularni ushlashi shart — shu sababli
# skanerning o'zi ham ularni topadi va bu fayl uni qizil qilib qo'yadi. `allow`
# markeri aynan shu holat uchun: qoidani zaiflashtirmasdan bitta satrni chiqarib
# tashlaydi. Markerlarni olib tashlash gate'ni qizil qiladi.
FAKE_TELEGRAM_TOKEN = "1234567890:AAF7bQzKmR3xLpWvNc8dTyE2sHjU6gVoXqZ"  # secret-scan: allow
FAKE_GOOGLE_KEY = "AIzaSyD3fK9mQ2xVbN7pLrT4wHjE8sYcU1gZoAv"  # secret-scan: allow
FAKE_AWS_KEY = "AKIAQ7WZ3MXKPLRVN2TD"  # secret-scan: allow


class SecretRuleTests(SimpleTestCase):
    def test_telegram_bot_token_is_caught(self):
        findings = scan_text("bot/config.py", f'TOKEN = "{FAKE_TELEGRAM_TOKEN}"')
        self.assertEqual([item["rule"] for item in findings], ["telegram_bot_token"])

    def test_google_api_key_is_caught(self):
        findings = scan_text(".env.production", f"GEMINI_API_KEY={FAKE_GOOGLE_KEY}")
        self.assertEqual([item["rule"] for item in findings], ["google_api_key"])

    def test_aws_access_key_is_caught(self):
        findings = scan_text("deploy.md", f"AWS_ACCESS_KEY_ID={FAKE_AWS_KEY}")
        self.assertEqual([item["rule"] for item in findings], ["aws_access_key_id"])

    def test_private_key_block_is_caught(self):
        header = "-----BEGIN RSA PRIVATE KEY-----"  # secret-scan: allow
        findings = scan_text("keys/app.pem", header)
        self.assertEqual([item["rule"] for item in findings], ["private_key_block"])

    def test_dsn_with_a_real_password_is_caught(self):
        text = "DATABASE_URL=postgresql://azurelms:t7Kq2ZmXpR9v@db.internal:25060/app"  # secret-scan: allow
        findings = scan_text(".env", text)
        self.assertEqual([item["rule"] for item in findings], ["url_inline_password"])

    def test_a_placeholder_dsn_is_not_reported(self):
        """Hujjatlardagi namuna DSN gate'ni qizil qilmasligi kerak."""
        text = "DATABASE_URL=postgresql://user:YOUR_PASSWORD@localhost:5432/azurelms"
        self.assertEqual(scan_text("README.md", text), [])

    def test_an_explicit_allow_marker_suppresses_a_line(self):
        text = f'sample = "{FAKE_GOOGLE_KEY}"  # secret-scan: allow (hujjat namunasi)'
        self.assertEqual(scan_text("docs.md", text), [])

    def test_the_finding_never_echoes_the_whole_secret(self):
        """CI logi public: xulosaning o'zi sirni tarqatmasligi kerak."""
        finding = scan_text("bot/config.py", f'TOKEN = "{FAKE_TELEGRAM_TOKEN}"')[0]
        self.assertNotIn(FAKE_TELEGRAM_TOKEN, json.dumps(finding))
        self.assertLessEqual(len(finding["preview"]), 5)

    def test_line_numbers_point_at_the_offending_line(self):
        text = "birinchi\nikkinchi\n" + f"KEY={FAKE_GOOGLE_KEY}\n"
        self.assertEqual(scan_text("x.env", text)[0]["line"], 3)


class TrackedEnvFileTests(SimpleTestCase):
    def test_a_tracked_env_file_is_reported(self):
        self.assertEqual(
            tracked_env_files(["core/settings.py", ".env.production"]),
            [".env.production"],
        )

    def test_example_files_are_allowed(self):
        self.assertEqual(tracked_env_files([".env.local.example", ".env.sample"]), [])


class RepositoryIsCleanTests(SimpleTestCase):
    """Asl gate: kuzatuvdagi fayllarda sir yo'q."""

    def test_no_secret_is_tracked_in_the_repository(self):
        findings = scan_repository()
        self.assertEqual(findings, [], f"Kuzatuvdagi fayllarda sir topildi: {findings}")

    def test_the_scanner_reports_a_secret_planted_in_a_tracked_file(self):
        """Nazorat: skaner haqiqiy git daraxtidan ham topa olishini isbotlaydi."""
        with TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
            (root / "app.py").write_text(f'KEY = "{FAKE_GOOGLE_KEY}"\n', encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=str(root), check=True)

            findings = scan_repository(root)

        self.assertEqual([item["rule"] for item in findings], ["google_api_key"])

    def test_the_command_exits_non_zero_when_a_secret_is_planted(self):
        """CI faqat buyruqning exit kodini ko'radi — u qizil bo'lishi shart."""
        with TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
            (root / "app.py").write_text(f'KEY = "{FAKE_GOOGLE_KEY}"\n', encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=str(root), check=True)

            with override_settings(BASE_DIR=root):
                with self.assertRaises(CommandError):
                    call_command("scan_secrets", stderr=StringIO(), stdout=StringIO())

    def test_the_command_succeeds_on_the_real_repository(self):
        call_command("scan_secrets", stdout=StringIO(), stderr=StringIO())


class DependencyReportTests(SimpleTestCase):
    def _report(self, name, version, ids):
        return {"dependencies": [{
            "name": name,
            "version": version,
            "vulns": [{"id": vuln_id, "fix_versions": []} for vuln_id in ids],
        }]}

    def test_duplicate_advisory_ids_are_collapsed(self):
        """pip-audit bir advisory'ni bir necha manbadan qaytarishi mumkin."""
        report = self._report("Django", "6.0.2", ["PYSEC-1", "PYSEC-1", "PYSEC-2"])
        self.assertEqual(report_findings(report), {"django==6.0.2": {"PYSEC-1", "PYSEC-2"}})

    def test_packages_without_vulnerabilities_are_skipped(self):
        report = {"dependencies": [{"name": "six", "version": "1.17.0", "vulns": []}]}
        self.assertEqual(report_findings(report), {})

    def test_a_malformed_report_is_rejected_loudly(self):
        with self.assertRaises(DependencyAuditError):
            report_findings({"packages": []})


class BaselineComparisonTests(SimpleTestCase):
    def _report(self, name, version, ids):
        return {"dependencies": [{
            "name": name,
            "version": version,
            "vulns": [{"id": vuln_id} for vuln_id in ids],
        }]}

    def test_a_new_advisory_is_flagged(self):
        report = self._report("django", "6.0.2", ["PYSEC-1", "PYSEC-9"])
        baseline = {"known": {"django==6.0.2": ["PYSEC-1"]}}
        self.assertEqual(compare(report, baseline)["unlisted"], {"django==6.0.2": ["PYSEC-9"]})

    def test_a_listed_advisory_is_not_flagged(self):
        report = self._report("django", "6.0.2", ["PYSEC-1"])
        baseline = {"known": {"django==6.0.2": ["PYSEC-1"]}}
        self.assertEqual(compare(report, baseline)["unlisted"], {})

    def test_bumping_the_package_invalidates_its_old_exemptions(self):
        """Reyestr `name==version` bo'yicha: yangi versiya qayta ko'rilishi shart."""
        report = self._report("django", "6.0.7", ["PYSEC-1"])
        baseline = {"known": {"django==6.0.2": ["PYSEC-1"]}}
        result = compare(report, baseline)
        self.assertEqual(result["unlisted"], {"django==6.0.7": ["PYSEC-1"]})
        self.assertEqual(result["stale"], {"django==6.0.2": ["PYSEC-1"]})

    def test_a_resolved_advisory_becomes_stale_but_does_not_fail(self):
        report = {"dependencies": []}
        baseline = {"known": {"pillow==12.1.1": ["PYSEC-1"]}}
        result = compare(report, baseline)
        self.assertEqual(result["stale"], {"pillow==12.1.1": ["PYSEC-1"]})
        self.assertEqual(result["unlisted"], {})


class ReviewDeadlineTests(SimpleTestCase):
    def test_a_past_deadline_is_overdue(self):
        overdue = review_overdue({"review_by": "2026-01-01"}, today=date(2026, 8, 15))
        self.assertEqual(overdue, date(2026, 1, 1))

    def test_the_deadline_day_itself_is_still_in_time(self):
        self.assertIsNone(review_overdue({"review_by": "2026-08-15"}, today=date(2026, 8, 15)))

    def test_an_empty_baseline_needs_no_deadline(self):
        """Muddat istisnolarni abadiylashishdan saqlaydi; istisno yo'q — muddat ham kerak emas."""
        self.assertIsNone(review_overdue({"known": {}}, today=date(2026, 8, 15)))

    def test_an_exemption_without_a_deadline_is_rejected(self):
        """Sanasiz istisno gate'ni jimgina bo'shatadi — bu ruxsat etilmaydi."""
        with self.assertRaises(DependencyAuditError):
            review_overdue({"known": {"django==6.0.2": ["PYSEC-1"]}}, today=date(2026, 8, 15))

    def test_a_broken_deadline_is_rejected_loudly(self):
        with self.assertRaises(DependencyAuditError):
            review_overdue({"review_by": "15.08.2026"})


class CommittedBaselineTests(SimpleTestCase):
    """Reyestr fayli haqiqatan repoda va o'qiladigan holatda."""

    def test_the_shipped_baseline_carries_no_exemptions(self):
        """Maqsad holati: bo'sh reyestr, ya'ni har qanday zaiflik darhol qizil.

        Bu test yiqilsa, kimdir zaiflikni tuzatish o'rniga oqlagan. Bu ba'zan
        to'g'ri qaror (major/RC ko'tarish talab qilinsa), ammo u ko'rinib
        turishi kerak — testni yangilash o'sha ko'rinishning o'zi.
        """
        baseline = load_json(baseline_path())
        self.assertEqual(
            baseline["known"], {},
            "Reyestrda istisno paydo bo'lgan. Paketni ko'tarib bo'lmaganini "
            "faylda sabab bilan yozing va shu testni ataylab yangilang.",
        )

    def test_an_exemption_would_require_a_review_date(self):
        """Bo'sh reyestrda ham qoida amalda ekanini tekshiradi."""
        baseline = dict(load_json(baseline_path()))
        baseline["known"] = {"example==1.0.0": ["PYSEC-0000"]}
        baseline.pop("review_by", None)
        with self.assertRaises(DependencyAuditError):
            review_overdue(baseline)

    def test_every_baseline_key_is_pinned_to_an_exact_version(self):
        for key in load_json(baseline_path())["known"]:
            self.assertIn("==", key, f"Reyestr kaliti versiyaga bog'lanmagan: {key}")
