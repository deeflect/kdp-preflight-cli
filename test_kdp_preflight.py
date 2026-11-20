import unittest

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


if __name__ == "__main__":
    unittest.main()
