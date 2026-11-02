"""Tests for the injected integration adapter; uses no webcam or ML packages."""

import unittest

from src.drowsiness_logic import DrowsinessDetector
from src.integration import DrowsinessPipeline


class IntegrationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.detector = DrowsinessDetector(closure_threshold_seconds=1.0)

    def test_missing_classifier_is_reported_without_fake_predictions(self):
        pipeline = DrowsinessPipeline(eye_classifier=None, detector=self.detector)
        result = pipeline.process_detection(
            face_detected=True,
            left_eye_crop=object(),
            right_eye_crop=object(),
            now=1.0,
        )
        self.assertEqual(result.driver_status, DrowsinessDetector.EYE_NOT_DETECTED)
        self.assertIn("not connected", result.diagnostic)
        self.assertIsNone(result.left_eye_status)

    def test_no_face_skips_classifier_and_reports_no_face(self):
        calls = []
        pipeline = DrowsinessPipeline(
            eye_classifier=lambda crop: calls.append(crop) or "CLOSED",
            detector=self.detector,
        )
        result = pipeline.process_detection(face_detected=False, now=0.0)
        self.assertEqual(result.driver_status, DrowsinessDetector.NO_FACE)
        self.assertEqual(calls, [])

    def test_unavailable_face_status_is_not_mistaken_for_no_face(self):
        pipeline = DrowsinessPipeline(eye_classifier=None, detector=self.detector)
        result = pipeline.process_detection(face_detected=None, now=0.0)
        self.assertIsNone(result.face_detected)
        self.assertEqual(result.driver_status, DrowsinessDetector.EYE_NOT_DETECTED)
        self.assertIn("unavailable or invalid", result.diagnostic)

    def test_valid_predictions_are_normalized_and_passed_to_logic(self):
        predictions = iter([" closed ", "CLOSED", "CLOSED", "closed"])
        pipeline = DrowsinessPipeline(
            eye_classifier=lambda crop: next(predictions), detector=self.detector
        )
        first = pipeline.process_detection(
            face_detected=True, left_eye_crop=1, right_eye_crop=2, now=0.0
        )
        second = pipeline.process_detection(
            face_detected=True, left_eye_crop=1, right_eye_crop=2, now=1.0
        )
        self.assertEqual(first.left_eye_status, "CLOSED")
        self.assertEqual(first.driver_status, "NORMAL")
        self.assertEqual(second.driver_status, "DROWSY")
        self.assertEqual(second.eye_closure_duration, 1.0)

    def test_missing_eye_crop_does_not_call_classifier(self):
        calls = []
        pipeline = DrowsinessPipeline(
            eye_classifier=lambda crop: calls.append(crop) or "OPEN",
            detector=self.detector,
        )
        result = pipeline.process_detection(
            face_detected=True, left_eye_crop=object(), right_eye_crop=None, now=0.0
        )
        self.assertEqual(result.driver_status, DrowsinessDetector.EYE_NOT_DETECTED)
        self.assertEqual(calls, [])

    def test_invalid_prediction_is_reported_safely(self):
        pipeline = DrowsinessPipeline(
            eye_classifier=lambda crop: "SLEEPY", detector=self.detector
        )
        result = pipeline.process_detection(
            face_detected=True,
            left_eye_crop=object(),
            right_eye_crop=object(),
            now=0.0,
        )
        self.assertEqual(result.driver_status, DrowsinessDetector.EYE_NOT_DETECTED)
        self.assertIn("invalid eye state", result.diagnostic)

    def test_classifier_exception_is_reported_without_crashing(self):
        def failing_classifier(crop):
            raise RuntimeError("model unavailable")

        pipeline = DrowsinessPipeline(
            eye_classifier=failing_classifier, detector=self.detector
        )
        result = pipeline.process_detection(
            face_detected=True,
            left_eye_crop=object(),
            right_eye_crop=object(),
            now=0.0,
        )
        self.assertEqual(result.driver_status, DrowsinessDetector.EYE_NOT_DETECTED)
        self.assertIn("RuntimeError", result.diagnostic)


if __name__ == "__main__":
    unittest.main()
