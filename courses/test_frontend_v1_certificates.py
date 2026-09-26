from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.flags import flag_by_slug, set_flag
from courses.models import Certificate, Course, Exam, ExamAttempt, ExamSection, ExamSectionReview


class CertificateDocumentV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = get_user_model().objects.create_user('cert.student', 'cert@example.test', first_name='<Dilnoza>')
        cls.course = Course.objects.create(title='Turk tili <A1>')
        cls.certificate = Certificate.objects.create(student=cls.student, course=cls.course, certificate_id='V1-TEST-ARCHIVE', final_score=82)
        cls.exam = Exam.objects.create(course=cls.course, title='Final', exam_type='final', weight_percentage=100)
        cls.section = ExamSection.objects.create(exam=cls.exam, title='Published section', section_type='writing', max_score=10)

    def setUp(self):
        set_flag('frontend_v1_certificates', enabled=True, reason='Certificate port')
        self.detail = reverse('certificate_detail', args=[self.certificate.certificate_id])
        self.appendix = reverse('certificate_appendix', args=[self.certificate.certificate_id])

    def test_existing_public_exact_id_policy_and_no_get_mutations(self):
        for url, template in [(self.detail, 'detail'), (self.appendix, 'appendix')]:
            response = self.client.get(url)
            self.assertTemplateUsed(response, f'frontend_v1/certificates/{template}.html')
            self.assertContains(response, '&lt;Dilnoza&gt;')
            self.assertContains(response, 'Turk tili &lt;A1&gt;')
            self.assertNotContains(response, self.student.email)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(self.client.head(url).status_code, 200)
            self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertEqual(ExamAttempt.objects.count(), 0)
        self.assertEqual(ExamSectionReview.objects.count(), 0)

    def test_default_off_and_legacy_rollback(self):
        self.assertFalse(flag_by_slug('frontend_v1_certificates').default)
        set_flag('frontend_v1_certificates', enabled=False, reason='Rollback')
        self.assertTemplateUsed(self.client.get(self.detail), 'courses/certificate.html')
        self.assertTemplateUsed(self.client.get(self.appendix), 'courses/certificate_appendix.html')

    def test_missing_id_is_404_not_another_certificate(self):
        for name in ('certificate_detail', 'certificate_appendix'):
            self.assertEqual(self.client.get(reverse(name, args=['UNKNOWN'])).status_code, 404)

    def test_download_parameter_does_not_auto_print_or_claim_saved_pdf(self):
        for path in (self.detail, self.appendix):
            response = self.client.get(path + '?download=1')
            self.assertContains(response, 'data-certificate-print')
            self.assertNotContains(response, 'window.print()')
            self.assertContains(response, 'frontend_v1/js/certificates.js')
            self.assertNotContains(response, 'SINOV NAMUNASI')

    def test_only_published_sections_not_draft_pending_or_other_users(self):
        attempt = ExamAttempt.objects.create(student=self.student, exam=self.exam, is_completed=True)
        review = ExamSectionReview.objects.create(attempt=attempt, section=self.section, awarded_score=7)
        attempt.finalize_review(reviewed_by=self.student)
        review.awarded_score = 9; review.feedback = 'SECRET'; review.save()
        self.section.title = 'SECRET draft rubric'; self.section.save()
        pending_exam = Exam.objects.create(course=self.course, title='SECRET pending', exam_type='visa', weight_percentage=0)
        ExamAttempt.objects.create(student=self.student, exam=pending_exam, is_completed=True)
        other = get_user_model().objects.create_user('cert.other', 'other@example.test')
        other_exam = Exam.objects.create(course=self.course, title='SECRET other student', exam_type='visa', weight_percentage=0)
        ExamAttempt.objects.create(student=other, exam=other_exam, is_reviewed=True, score=99)
        response = self.client.get(self.appendix)
        self.assertContains(response, 'Published section')
        self.assertContains(response, '7 / 10')
        self.assertNotContains(response, 'SECRET')

    def test_historical_and_empty_are_not_invented_zero_scores(self):
        self.assertContains(self.client.get(self.appendix), 'bo‘sh ro‘yxat nol ball degani emas')
        ExamAttempt.objects.create(student=self.student, exam=self.exam, is_completed=True, is_reviewed=True, score=75, passed=True)
        response = self.client.get(self.appendix)
        self.assertContains(response, '75%')
        self.assertContains(response, 'Bo‘sh qiymat nol emas')

    def test_authenticated_back_link_and_records_hint(self):
        self.assertNotContains(self.client.get(self.detail), 'Sertifikatlarim')
        self.client.force_login(self.student)
        self.assertContains(self.client.get(self.detail), 'Sertifikatlarim')
        set_flag('frontend_v1_records', enabled=True, reason='Link projection')
        response = self.client.get(reverse('certificates'))
        self.assertNotContains(response, 'Hujjat va ilova avvalgi ko‘rinishda')
        set_flag('frontend_v1_certificates', enabled=False, reason='Rollback')
        self.assertContains(self.client.get(reverse('certificates')), 'Hujjat va ilova avvalgi ko‘rinishda')
