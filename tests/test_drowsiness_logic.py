"""Deterministic tests for the time-based drowsiness logic."""

import unittest

from src.dashboard_state import demo_eye_inputs
from src.drowsiness_logic import CLOSURE_THRESHOLD_SECONDS, DrowsinessDetector


class DrowsinessDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = DrowsinessDetector(closure_threshold_seconds=2.0)

    def test_initial_state_is_normal(self):
        self.assertEqual(self.detector.get_status(), DrowsinessDetector.NORMAL)

    def test_open_eyes_remain_normal(self):
        for timestamp in (0.0, 1.0, 5.0):
            self.assertEqual(
                self.detector.update("OPEN", "OPEN", now=timestamp),
                DrowsinessDetector.NORMAL,
            )

    def test_brief_closure_remains_normal(self):
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=0.0), "NORMAL")
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=0.6), "NORMAL")

    def test_blink_returns_to_normal(self):
        self.detector.update("CLOSED", "CLOSED", now=10.0)
        self.assertEqual(self.detector.update("OPEN", "OPEN", now=10.3), "NORMAL")
        self.assertEqual(self.detector.get_closure_duration(now=10.3), 0.0)

    def test_long_continuous_closure_becomes_drowsy_at_threshold(self):
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=2.0), "NORMAL")
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=3.99), "NORMAL")
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=4.0), "DROWSY")

    def test_drowsy_remains_drowsy_while_both_eyes_stay_closed(self):
        self.detector.update("CLOSED", "CLOSED", now=0.0)
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=2.0), "DROWSY")
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=8.0), "DROWSY")

    def test_opening_eyes_after_drowsiness_returns_to_normal(self):
        self.detector.update("CLOSED", "CLOSED", now=0.0)
        self.detector.update("CLOSED", "CLOSED", now=2.0)
        self.assertEqual(self.detector.update("OPEN", "OPEN", now=2.1), "NORMAL")
        self.assertEqual(self.detector.get_closure_duration(now=2.1), 0.0)

    def test_one_eye_closed_does_not_start_both_eye_closure(self):
        for timestamp in (0.0, 1.0, 5.0):
            self.assertEqual(
                self.detector.update("CLOSED", "OPEN", now=timestamp),
                "NORMAL",
            )
        self.assertEqual(self.detector.get_closure_duration(now=5.0), 0.0)

    def test_no_face_is_not_drowsy_and_clears_timer(self):
        self.detector.update("CLOSED", "CLOSED", now=1.0)
        self.assertEqual(
            self.detector.update(None, None, face_detected=False, now=1.5),
            DrowsinessDetector.NO_FACE,
        )
        self.assertEqual(self.detector.get_closure_duration(now=1.5), 0.0)

    def test_missing_eye_data_is_safe_and_not_drowsy(self):
        for left, right in ((None, "CLOSED"), ("CLOSED", None), (None, None)):
            self.assertEqual(
                self.detector.update(left, right, now=1.0),
                DrowsinessDetector.EYE_NOT_DETECTED,
            )
        self.assertEqual(
            self.detector.update("SLEEPING", "CLOSED", now=2.0),
            DrowsinessDetector.EYE_NOT_DETECTED,
        )

    def test_reset_clears_status_and_closure_timer(self):
        self.detector.update("CLOSED", "CLOSED", now=0.0)
        self.detector.update("CLOSED", "CLOSED", now=2.0)
        self.detector.reset()
        self.assertEqual(self.detector.get_status(), "NORMAL")
        self.assertEqual(self.detector.get_closure_duration(now=3.0), 0.0)

    def test_reset_during_closure_starts_a_fresh_interval(self):
        self.detector.update("CLOSED", "CLOSED", now=0.0)
        self.detector.update("CLOSED", "CLOSED", now=1.5)
        self.detector.reset()
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=2.0), "NORMAL")
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=3.99), "NORMAL")
        self.assertEqual(self.detector.update("CLOSED", "CLOSED", now=4.0), "DROWSY")

    def test_configurable_threshold_is_used(self):
        detector = DrowsinessDetector(closure_threshold_seconds=0.5)
        self.assertEqual(detector.update("CLOSED", "CLOSED", now=0.0), "NORMAL")
        self.assertEqual(detector.update("CLOSED", "CLOSED", now=0.49), "NORMAL")
        self.assertEqual(detector.update("CLOSED", "CLOSED", now=0.5), "DROWSY")
        self.assertEqual(CLOSURE_THRESHOLD_SECONDS, 1.5)

    def test_blink_demo_input_opens_after_short_interval(self):
        self.assertEqual(demo_eye_inputs("Blink", 0.0), ("CLOSED", "CLOSED", True))
        self.assertEqual(demo_eye_inputs("Blink", 0.5), ("OPEN", "OPEN", True))

    def test_demo_inputs_cover_one_eye_no_face_and_missing_eyes(self):
        self.assertEqual(demo_eye_inputs("One Eye Closed"), ("CLOSED", "OPEN", True))
        self.assertEqual(demo_eye_inputs("No Face"), (None, None, False))
        self.assertEqual(demo_eye_inputs("Eye Not Detected"), (None, None, True))


if __name__ == "__main__":
    unittest.main()
