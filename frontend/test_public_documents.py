"""Public rich hujjat proyeksiyasi: sanitizer -> anchor -> mundarija."""

from django.test import SimpleTestCase
from django.utils.safestring import SafeData

from frontend.public_documents import project_public_document


class PublicDocumentProjectionTests(SimpleTestCase):
    def test_sanitizes_before_building_the_toc(self):
        document = project_public_document(
            '<h2 id="owner" onclick="PWNED()">Kim <em>uchun</em></h2>'
            '<script>PWNED()</script><p style="color:red">Xavfsiz matn</p>',
            prefix="guide",
        )

        self.assertIsInstance(document.html, SafeData)
        self.assertEqual(
            [(item.anchor, item.label) for item in document.toc],
            [("guide-kim-uchun", "Kim uchun")],
        )
        self.assertIn('<h2 id="guide-kim-uchun">Kim <em>uchun</em></h2>', document.html)
        for forbidden in ('id="owner"', "onclick", "PWNED", "<script", "style="):
            self.assertNotIn(forbidden, document.html)

    def test_duplicate_and_non_latin_headings_get_unique_stable_ids(self):
        raw = "<h2>Bir xil</h2><h2>Bir xil</h2><h2>你好</h2><h2> </h2>"
        first = project_public_document(raw, prefix="guide")
        second = project_public_document(first.html, prefix="guide")

        self.assertEqual(
            [item.anchor for item in first.toc],
            ["guide-bir-xil", "guide-bir-xil-2", "guide-bolim-3"],
        )
        self.assertEqual(first, second)
        self.assertEqual(str(first.html).count('id="guide-'), 3)
        self.assertIn("你好", first.toc[2].label)

    def test_document_without_a_nonempty_h2_has_no_toc(self):
        document = project_public_document("<h3>Kichik sarlavha</h3><h2></h2><p>Matn</p>")

        self.assertEqual(document.toc, ())
        self.assertNotIn(" id=", document.html)
        self.assertNotIn("<h2", document.html)
        self.assertIn("<p>Matn</p>", document.html)
