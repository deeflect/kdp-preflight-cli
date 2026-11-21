import tempfile
import unittest
import zlib
from pathlib import Path

import kdp_preflight as kdp


class TestKdpPreflight(unittest.TestCase):
    def test_canonical_174_white_paperback(self) -> None:
        res = kdp.compute_cover(5.5, 8.5, 174, paper="white", binding="paperback")
        self.assertAlmostEqual(res["spine_in"], 0.392, places=3)
        self.assertAlmostEqual(res["wrap_width_in"], 11.642, places=3)
        self.assertAlmostEqual(res["wrap_height_in"], 8.750, places=3)
        self.assertTrue(res["spine_text_allowed"])
        self.assertEqual(res["min_inside_margin_in"], 0.5)

    def test_hardcover_case_wrap_matches_kdp(self) -> None:
        res = kdp.compute_cover(6.0, 9.0, 300, paper="white", binding="hardcover")
        self.assertAlmostEqual(res["spine_in"], 0.865, places=3)
        self.assertAlmostEqual(res["wrap_width_in"], 14.439, places=3)
        self.assertAlmostEqual(res["wrap_height_in"], 10.417, places=3)

    def test_gutter_step_ups(self) -> None:
        self.assertEqual(kdp.kdp_inside_min(150), 0.375)
        self.assertEqual(kdp.kdp_inside_min(151), 0.5)
        self.assertEqual(kdp.kdp_inside_min(301), 0.625)
        self.assertEqual(kdp.kdp_inside_min(501), 0.75)
        self.assertEqual(kdp.kdp_inside_min(701), 0.875)

    def test_preflight_catches_bad_margin_and_low_dpi(self) -> None:
        checks = kdp.run_preflight(
            6.0,
            9.0,
            320,
            paper="white",
            binding="paperback",
            inside=0.5,
            outside=0.25,
            bleed=True,
            image_px=(1200, 1800),
            image_in=(6.0, 9.0),
        )
        by_id = {c["id"]: c["ok"] for c in checks}
        self.assertTrue(by_id["page-count"])
        self.assertFalse(by_id["inside-margin"])
        self.assertFalse(by_id["outside-margin"])
        self.assertFalse(by_id["image-dpi"])

    def test_hardcover_unsupported_trim_fails(self) -> None:
        checks = kdp.run_preflight(5.0, 8.0, 120, paper="white", binding="hardcover")
        by_id = {c["id"]: c["ok"] for c in checks}
        self.assertFalse(by_id["hardcover-trim"])

    def test_inspect_pdf_reads_pages_and_trim_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "book.pdf"
            pdf.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Pages /Count 174 >> endobj\n"
                b"2 0 obj << /Type /Page /MediaBox [0 0 396 612] >> endobj\n"
                b"%%EOF\n"
            )
            info = kdp.inspect_pdf(pdf)
            self.assertEqual(info["pages"], 174)
            self.assertEqual(info["size_in"], [5.5, 8.5])
            self.assertFalse(info["mixed_page_sizes"])
            self.assertEqual(kdp.main(["pdf", str(pdf), "--paper", "white", "--json"]), 0)

    def test_inspect_pdf_reads_compressed_objstm_and_flags_mixed_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "compressed.pdf"
            inner = zlib.compress(
                b"<< /Type /Pages /Count 200 >> "
                b"<< /Type /Page /MediaBox [0 0 432 648] >> "
                b"<< /Type /Page /MediaBox [0 0 612 792] >>"
            )
            pdf.write_bytes(
                b"%PDF-1.5\n1 0 obj << /Type /ObjStm /Filter /FlateDecode /Length "
                + str(len(inner)).encode()
                + b" >>\nstream\n"
                + inner
                + b"\nendstream\nendobj\n%%EOF\n"
            )
            info = kdp.inspect_pdf(pdf)
            self.assertEqual(info["pages"], 200)
            self.assertTrue(info["mixed_page_sizes"])
            self.assertEqual(kdp.main(["pdf", str(pdf), "--paper", "cream"]), 1)


if __name__ == "__main__":
    unittest.main()
