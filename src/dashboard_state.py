"""Demo state and UI-facing values for the drowsiness dashboard.

Keep this module independent of OpenCV and ML dependencies. Future adapters can
populate the same fields from the real detection pipeline.
"""

from dataclasses import dataclass

from src.drowsiness_logic import CLOSURE_THRESHOLD_SECONDS


@dataclass(frozen=True)
class DashboardState:
    # These are the values the UI needs to display. Defaults represent a
    # ready-to-integrate system with no camera or model connected.
    left_eye_status: str = "OPEN"
    right_eye_status: str = "OPEN"
    driver_status: str = "NORMAL"
    alarm_status: str = "OFF"
    eye_closure_duration: float = 0.0
    drowsiness_threshold: float = CLOSURE_THRESHOLD_SECONDS
    camera_status: str = "Not Connected"
    opencv_status: str = "Waiting"
    model_status: str = "Waiting"
    system_status: str = "Ready for Integration"
    monitoring: bool = False
    demo_scenario: str = "Normal"


def state_for_scenario(scenario: str, monitoring: bool = False) -> DashboardState:
    """Return clearly synthetic UI values for a selected demo scenario."""
    # Each tuple is: left eye, right eye, driver status, alarm, closure seconds.
    # Changing this table is an easy way to add or tune UI-only demo scenarios.
    values = {
        "Normal": ("OPEN", "OPEN", "NORMAL", "OFF", 0.0),
        "Blink": ("CLOSED", "CLOSED", "NORMAL", "OFF", 0.0),
        "Long Eye Closure": ("CLOSED", "CLOSED", "NORMAL", "OFF", 0.0),
        "One Eye Closed": ("CLOSED", "OPEN", "NORMAL", "OFF", 0.0),
        "Drowsy": ("CLOSED", "CLOSED", "DROWSY", "ON", 2.4),
        "No Face": ("—", "—", "NO FACE DETECTED", "OFF", 0.0),
        "Eye Not Detected": ("NOT DETECTED", "NOT DETECTED", "EYE NOT DETECTED", "OFF", 0.0),
    }
    # If an unexpected scenario name is supplied, safely show the Normal demo.
    left, right, driver, alarm, duration = values.get(scenario, values["Normal"])
    # Pack the selected demo values into the same shape that a future real
    # camera/model adapter can populate.
    return DashboardState(
        left_eye_status=left,
        right_eye_status=right,
        driver_status=driver,
        alarm_status=alarm,
        eye_closure_duration=duration,
        monitoring=monitoring,
        demo_scenario=scenario,
    )


def demo_eye_inputs(
    scenario: str,
    elapsed_seconds: float = 0.0,
) -> tuple[str | None, str | None, bool]:
    """Return mock (left eye, right eye, face detected) values for the UI demo.

    Blink closes both eyes briefly and then opens them. Long Eye Closure remains
    closed until the user selects another scenario. No alarm is controlled here.
    """
    if scenario == "Normal":
        return "OPEN", "OPEN", True
    if scenario == "Blink":
        if elapsed_seconds < 0.4:
            return "CLOSED", "CLOSED", True
        return "OPEN", "OPEN", True
    if scenario == "Long Eye Closure":
        return "CLOSED", "CLOSED", True
    if scenario == "One Eye Closed":
        return "CLOSED", "OPEN", True
    if scenario == "No Face":
        return None, None, False
    if scenario == "Eye Not Detected":
        return None, None, True
    # Preserve compatibility with the old hidden Drowsy demo state.
    if scenario == "Drowsy":
        return "CLOSED", "CLOSED", True
    return "OPEN", "OPEN", True
