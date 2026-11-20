import unittest
import numpy as np
from src.real_monitor import RealMonitor, eye_ratio

class MonitorTests(unittest.TestCase):
    def test_eye_geometry(self):
        points = np.array([[0,0],[3,-2],[7,-2],[10,0],[7,2],[3,2]])
        self.assertAlmostEqual(eye_ratio(points), .4)
        points[:,1] = 0
        self.assertEqual(eye_ratio(points), 0)
        self.assertIsNone(eye_ratio(np.zeros((6,2))))

    def test_real_model_and_reset(self):
        monitor = RealMonitor()
        try:
            monitor.process_frame(np.zeros((480,640,3), dtype=np.uint8))
            self.assertEqual(monitor.driver_status, 'NO_FACE')
            self.assertIsNone(monitor.last_error)
            monitor.alarm_latched = True
            monitor.close()
            self.assertFalse(monitor.alarm_latched)
            self.assertEqual(monitor.eye_boxes, [])
        finally:
            monitor.landmarker.close()

    def test_landmark_closure_and_recovery(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        from src.real_monitor import EYES
        monitor = RealMonitor()
        original = monitor.landmarker
        landmarks = [SimpleNamespace(x=.5, y=.5) for _ in range(478)]
        def set_eyes(gap):
            for eye, offset in zip(EYES, (.25, .6)):
                for index, (x,y) in zip(eye, ((0,0),(.03,-gap),(.07,-gap),(.1,0),(.07,gap),(.03,gap))):
                    landmarks[index] = SimpleNamespace(x=offset+x, y=.5+y)
        monitor.landmarker = Mock()
        monitor.landmarker.detect.return_value = SimpleNamespace(face_landmarks=[landmarks])
        frame = np.zeros((480,640,3), dtype=np.uint8)
        try:
            set_eyes(.003)
            monitor.detector._clock = lambda: 0
            monitor.process_frame(frame)
            self.assertEqual(monitor.left_eye, 'CLOSED')
            monitor.detector._clock = lambda: 2
            monitor.process_frame(frame)
            self.assertEqual(monitor.driver_status, 'DROWSY')
            self.assertTrue(monitor.alarm_latched)
            monitor.acknowledge_alarm()
            set_eyes(.03)
            monitor.process_frame(frame)
            self.assertEqual(monitor.driver_status, 'NORMAL')
            self.assertFalse(monitor.alarm_latched)
        finally:
            original.close()
