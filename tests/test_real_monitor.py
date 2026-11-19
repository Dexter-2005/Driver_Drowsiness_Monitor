"""Runtime checks with the real model; no webcam or audio hardware needed."""
import unittest
from unittest.mock import patch

import numpy as np
from src.real_monitor import RealMonitor


class RealMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monitor = RealMonitor()

    def tearDown(self):
        self.monitor.close()

    def test_model_warmup_and_batch_inference(self):
        states = self.monitor._predict_eyes([np.zeros((80, 80, 3), dtype=np.uint8)] * 2)
        self.assertEqual(len(states), 2)
        self.assertTrue(all(state in ('OPEN', 'CLOSED') for state in states))

    def test_shared_model_but_independent_session_state(self):
        other = RealMonitor()
        self.assertIs(other.model, self.monitor.model)
        self.assertIsNot(other.detector, self.monitor.detector)
        self.monitor.alarm_latched = True
        self.assertFalse(other.alarm_latched)
        other.close()

    def test_empty_frame_has_no_face(self):
        self.monitor.process_frame(np.zeros((480, 640, 3), dtype=np.uint8))
        self.assertEqual(self.monitor.driver_status, 'NO_FACE')
        self.assertIsNone(self.monitor.last_error)

    def test_camera_gap_does_not_count_as_continuous_closure(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        crops = [{'crop': frame[:80, :80], 'bbox': (0, 0, 80, 80), 'side': 'Left'}] * 2
        self.monitor.detector.update('CLOSED', 'CLOSED', now=1)
        self.monitor._last_processed_at = 1
        with patch('src.real_monitor.monotonic', return_value=10), patch.object(self.monitor, '_detect_face', return_value=(0, 0, 100, 100)), patch.object(self.monitor.eye_detector, 'extract_eye_crops', return_value=crops), patch.object(self.monitor, '_predict_eyes', return_value=['CLOSED', 'CLOSED']):
            self.monitor.process_frame(frame)
        self.assertEqual(self.monitor.driver_status, 'NORMAL')
        self.assertFalse(self.monitor.alarm_latched)
