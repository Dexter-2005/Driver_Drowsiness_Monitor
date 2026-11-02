"""Streamlit dashboard foundation for Driver Drowsiness Detection System."""

import sys
from dataclasses import replace
from pathlib import Path
from time import monotonic

import streamlit as st
import av
from streamlit_webrtc import VideoProcessorBase, WebRtcMode, webrtc_streamer

# Add the project folder to Python's import path so `src.dashboard_state`
# can be imported when Streamlit is started with `streamlit run app/main.py`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard_state import demo_eye_inputs, state_for_scenario
from src.drowsiness_logic import CLOSURE_THRESHOLD_SECONDS, DrowsinessDetector
from src.real_monitor import RealMonitor


class DashboardVideoProcessor(VideoProcessorBase):
    """Run each browser camera frame through the shared real-mode pipeline."""

    def __init__(self, monitor: RealMonitor) -> None:
        self.monitor = monitor

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        image = frame.to_ndarray(format="bgr24")
        processed = self.monitor.process_frame(image)
        return av.VideoFrame.from_ndarray(processed, format="bgr24")


# Configure the browser tab and use a wide page for the dashboard columns.
st.set_page_config(
    page_title="Driver Drowsiness Detection System",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Most of the visual design is CSS. These class names are attached to HTML
# panels below; Streamlit's normal widgets (buttons/selectbox) remain usable.
st.markdown("""
<style>
/* Optional web fonts; the dashboard still works if they cannot be downloaded. */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
/* Shared colors make it easier to adjust the dashboard theme in one place. */
:root { --ink:#e8eef8; --muted:#8b9ab1; --line:#25344a; --panel:#111d2d; --bg:#091321; --cyan:#55d6d2; }
/* Main page background, typography, reusable cards, camera placeholder and status colors. */
.stApp { background: radial-gradient(ellipse at 50% -25%, #18304a 0%, #091321 58%); color:var(--ink); font-family:'DM Sans',sans-serif; }
.block-container { max-width:1320px; padding-top:2rem; padding-bottom:2rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; color:var(--ink) !important; }
.eyebrow { color:var(--cyan); font-size:.72rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }
.subtitle { color:var(--muted); margin-top:-.65rem; }
.panel { background:linear-gradient(145deg,rgba(19,33,51,.96),rgba(14,26,42,.96)); border:1px solid var(--line); border-radius:16px; padding:20px 22px; height:100%; box-shadow:0 12px 30px rgba(0,0,0,.12); }
.panel-title { color:#aab8cb; font-size:.78rem; text-transform:uppercase; letter-spacing:.1em; font-weight:700; margin-bottom:16px; }
.camera { min-height:340px; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; background:radial-gradient(ellipse at center,#172a3f 0%,#0b1625 70%); border:1px dashed #3b526c; border-radius:12px; }
.camera-icon { width:58px; height:58px; display:grid; place-items:center; border-radius:16px; background:#1b3044; color:var(--cyan); font-size:1.55rem; margin-bottom:16px; }
.camera-main { color:#d8e3f2; font-size:1.05rem; font-weight:600; }
.camera-sub { color:var(--muted); font-size:.84rem; margin-top:5px; }
.status-value { font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:700; color:#e8eef8; margin-top:8px; }
.status-value.good { color:#55d6a1; } .status-value.warn { color:#ffbd69; } .status-value.bad { color:#ff7c87; }
.metric { color:#e8eef8; font-family:'Space Grotesk',sans-serif; font-size:1.65rem; font-weight:600; margin-top:8px; }
.metric small { font:500 .8rem 'DM Sans',sans-serif; color:var(--muted); }
.meta-row { display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:1px solid rgba(37,52,74,.7); color:#aab8cb; font-size:.9rem; }
.meta-row:last-child { border-bottom:0; } .meta-val { color:#e8eef8; font-weight:600; }
.demo-pill { display:inline-block; padding:5px 10px; border-radius:99px; color:#ffd27b; background:rgba(255,189,105,.11); border:1px solid rgba(255,189,105,.25); font-size:.72rem; font-weight:700; letter-spacing:.08em; }
/* Small responsive adjustments for narrower laptop/browser widths. */
div[data-testid="stButton"] button { border-radius:9px; min-height:2.65rem; font-weight:600; }
div[data-testid="stSelectbox"] label { color:#aab8cb; }
@media (max-width: 800px) { .block-container{padding-left:1rem;padding-right:1rem;} .camera{min-height:250px;} }
</style>
""", unsafe_allow_html=True)

# Streamlit reruns this file after every interaction. Session state remembers
# these values between reruns so the buttons and selected demo scenario persist.
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
if "scenario" not in st.session_state:
    st.session_state.scenario = "Normal"
if "mode" not in st.session_state:
    st.session_state.mode = "DEMO MODE"
if "drowsiness_detector" not in st.session_state:
    st.session_state.drowsiness_detector = DrowsinessDetector(
        CLOSURE_THRESHOLD_SECONDS
    )
if "tracked_scenario" not in st.session_state:
    st.session_state.tracked_scenario = st.session_state.scenario
if "tracked_mode" not in st.session_state:
    st.session_state.tracked_mode = st.session_state.mode
if "scenario_started_at" not in st.session_state:
    st.session_state.scenario_started_at = monotonic()
if "real_monitor" not in st.session_state:
    st.session_state.real_monitor = None
if "real_error" not in st.session_state:
    st.session_state.real_error = None

# Header: title on the left and explicit mode selection on the right.
header, badge = st.columns([5, 1])
with header:
    st.markdown('<div class="eyebrow">Driver Safety • Monitoring Console</div>', unsafe_allow_html=True)
    st.title("Driver Drowsiness Detection System")
    st.markdown('<div class="subtitle">Real-Time Driver Monitoring</div>', unsafe_allow_html=True)
with badge:
    mode_badge = st.session_state.mode
    st.markdown(
        f'<div style="text-align:right;padding-top:4px"><span class="demo-pill">{mode_badge}</span></div>',
        unsafe_allow_html=True,
    )
    st.selectbox(
        "Operating mode",
        ["DEMO MODE", "REAL MODE"],
        key="mode",
        label_visibility="collapsed",
    )

def get_current_dashboard_state():
    """Advance demo input or read the connected webcam pipeline."""
    now = monotonic()
    scenario = st.session_state.scenario
    mode = st.session_state.mode

    if mode != st.session_state.tracked_mode:
        st.session_state.drowsiness_detector.reset()
        if st.session_state.real_monitor is not None:
            st.session_state.real_monitor.close()
            st.session_state.real_monitor = None
        st.session_state.monitoring = False
        st.session_state.real_error = None
        st.session_state.tracked_mode = mode
        st.session_state.scenario_started_at = now

    if mode == "REAL MODE":
        monitor = st.session_state.real_monitor
        if monitor is None or not st.session_state.monitoring:
            ready = monitor is not None
            return replace(
                state_for_scenario("Normal", False),
                left_eye_status="WAITING" if ready else "NOT CONNECTED",
                right_eye_status="WAITING" if ready else "NOT CONNECTED",
                driver_status="MONITORING STOPPED" if ready else "WAITING FOR MODULES",
                camera_status="Ready" if ready else "Not Connected",
                opencv_status="Connected",
                model_status="Loaded" if ready else "Not Loaded",
                system_status="Ready" if ready else "Real Mode Ready to Start",
            )
        st.session_state.real_error = monitor.last_error
        status = monitor.driver_status
        display_status = {
            DrowsinessDetector.NO_FACE: "NO FACE DETECTED",
            DrowsinessDetector.EYE_NOT_DETECTED: "EYE NOT DETECTED",
        }.get(status, status)
        return replace(
            state_for_scenario("Normal", True),
            left_eye_status=monitor.left_eye,
            right_eye_status=monitor.right_eye,
            driver_status=display_status,
            alarm_status=(
                "AUDIO ALERT" if monitor.alarm.supported else "VISUAL ALERT"
            ) if status == DrowsinessDetector.DROWSY else "OFF",
            eye_closure_duration=monitor.closure_duration,
            camera_status="Waiting for browser camera" if monitor.last_frame is None else "Connected",
            opencv_status="Connected",
            model_status="Loaded",
            system_status="Waiting for camera stream" if monitor.last_frame is None else "Monitoring",
        )

    # Starting a different scenario resets the timer so old closure time cannot
    # carry over and make a new selection appear drowsy immediately.
    if scenario != st.session_state.tracked_scenario:
        st.session_state.drowsiness_detector.reset()
        st.session_state.tracked_scenario = scenario
        st.session_state.scenario_started_at = now

    elapsed = now - st.session_state.scenario_started_at
    left_eye, right_eye, face_detected = demo_eye_inputs(scenario, elapsed)
    detector = st.session_state.drowsiness_detector

    # Future ML integration point: replace these mock eye strings with the
    # classifier's OPEN/CLOSED predictions. OpenCV face/eye detection will
    # supply face_detected and indicate when an eye cannot be observed.
    detected_status = detector.update(
        left_eye,
        right_eye,
        face_detected=face_detected,
        now=now,
    )
    display_status = {
        DrowsinessDetector.NO_FACE: "NO FACE DETECTED",
        DrowsinessDetector.EYE_NOT_DETECTED: "EYE NOT DETECTED",
    }.get(detected_status, detected_status)

    state = state_for_scenario(scenario, st.session_state.monitoring)
    left_display = "N/A" if not face_detected else (left_eye or "NOT DETECTED")
    right_display = "N/A" if not face_detected else (right_eye or "NOT DETECTED")
    return replace(
        state,
        left_eye_status=left_display,
        right_eye_status=right_display,
        driver_status=display_status,
        eye_closure_duration=detector.get_closure_duration(now),
        drowsiness_threshold=detector.closure_threshold_seconds,
    )


@st.fragment(run_every=0.5)
def render_dashboard():
    """Refresh the demo dashboard twice a second so the closure timer advances."""
    # The recurring fragment lets a sustained mock closure cross its threshold
    # without requesting an external auto-refresh dependency.
    state = get_current_dashboard_state()

    # Main row: retain the camera placeholder and existing driver overview.
    left, right = st.columns([1.75, 1], gap="large")
    with left:
        if st.session_state.mode == "REAL MODE" and state.monitoring and st.session_state.real_monitor is not None:
            monitor = st.session_state.real_monitor
            webrtc_streamer(
                key="real-camera-stream",
                mode=WebRtcMode.SENDRECV,
                video_processor_factory=lambda: DashboardVideoProcessor(monitor),
                media_stream_constraints={
                    "video": {
                        "width": {"ideal": 640},
                        "height": {"ideal": 480},
                        "frameRate": {"ideal": 10, "max": 15},
                    },
                    "audio": False,
                },
                rtc_configuration={"iceServers": []},
            )
            if st.session_state.real_error:
                st.warning(st.session_state.real_error)
            elif monitor.last_frame is None:
                st.info("Start the camera above and allow browser camera access to begin live detection.")
            else:
                st.caption(f"Live processing: {monitor.fps:.1f} FPS")
        elif st.session_state.mode == "REAL MODE":
            camera_message = "REAL MODE - Camera stopped"
            camera_detail = "Start Monitoring, then start the camera stream and allow browser camera access."
            st.markdown(
                f'<div class="panel"><div class="panel-title">Live Camera Feed</div><div class="camera"><div class="camera-icon">⌖</div><div class="camera-main">{camera_message}</div><div class="camera-sub">{camera_detail}</div></div></div>',
                unsafe_allow_html=True,
            )
        else:
            camera_message = "Demo Mode - Camera Not Connected"
            camera_detail = "Camera feed will appear here when the OpenCV component is integrated."
            st.markdown(
                f'<div class="panel"><div class="panel-title">Live Camera Feed</div><div class="camera"><div class="camera-icon">⌖</div><div class="camera-main">{camera_message}</div><div class="camera-sub">{camera_detail}</div></div></div>',
                unsafe_allow_html=True,
            )
    with right:
        st.markdown('<div class="panel-title">Driver Overview</div>', unsafe_allow_html=True)
        eye1, eye2 = st.columns(2, gap="medium")
        with eye1:
            st.markdown(f'<div class="panel"><div class="panel-title">Left Eye</div><div class="status-value">{state.left_eye_status}</div></div>', unsafe_allow_html=True)
        with eye2:
            st.markdown(f'<div class="panel"><div class="panel-title">Right Eye</div><div class="status-value">{state.right_eye_status}</div></div>', unsafe_allow_html=True)
        st.write("")
        driver_class = "good" if state.driver_status == "NORMAL" else ("warn" if state.driver_status in ("NO FACE DETECTED", "EYE NOT DETECTED", "WAITING FOR MODULES") else "bad")
        alarm_class = "good" if state.alarm_status == "OFF" else "bad"
        a, b = st.columns(2, gap="medium")
        with a:
            st.markdown(f'<div class="panel"><div class="panel-title">Driver Status</div><div class="status-value {driver_class}" style="font-size:1.2rem">{state.driver_status}</div></div>', unsafe_allow_html=True)
        with b:
            # Existing alarm display is preserved; this task does not activate an alarm.
            st.markdown(f'<div class="panel"><div class="panel-title">Alarm Status</div><div class="status-value {alarm_class}">{state.alarm_status}</div></div>', unsafe_allow_html=True)

    # Secondary row: duration/threshold, readiness, and existing controls.
    st.write("")
    info_col, system_col, controls_col = st.columns([1, 1.2, 1.25], gap="large")
    with info_col:
        st.markdown('<div class="panel-title">Eye Closure Information</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="panel"><div class="panel-title">Eye Closure Duration</div><div class="metric">{state.eye_closure_duration:.1f} <small>sec</small></div><div style="height:16px"></div><div class="panel-title">Drowsiness Threshold</div><div class="metric">{state.drowsiness_threshold:.1f} <small>sec</small></div></div>', unsafe_allow_html=True)
    with system_col:
        st.markdown('<div class="panel-title">System Status</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="panel"><div class="meta-row"><span>Camera</span><span class="meta-val">{state.camera_status}</span></div><div class="meta-row"><span>OpenCV</span><span class="meta-val">{state.opencv_status}</span></div><div class="meta-row"><span>ML Model</span><span class="meta-val">{state.model_status}</span></div><div class="meta-row"><span>System</span><span class="meta-val">{state.system_status}</span></div></div>', unsafe_allow_html=True)
    with controls_col:
        st.markdown('<div class="panel-title">Monitoring Controls</div>', unsafe_allow_html=True)
        with st.container(border=True):
            if st.session_state.mode == "REAL MODE":
                if st.session_state.real_error:
                    st.warning(st.session_state.real_error)
                st.caption("Real mode streams webcam frames to the OpenCV/CNN pipeline and plays a repeating alert while DROWSY is detected.")
            else:
                st.caption("Controls update demo state only. No camera or alarm is started.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Start Monitoring", type="primary", use_container_width=True):
                    if st.session_state.mode == "REAL MODE":
                        try:
                            if st.session_state.real_monitor is None:
                                st.session_state.real_monitor = RealMonitor()
                            st.session_state.real_error = None
                            st.session_state.monitoring = True
                        except Exception as exc:
                            st.session_state.real_error = f"Could not start real monitoring ({type(exc).__name__}): {exc}"
                            st.session_state.monitoring = False
                    else:
                        st.session_state.monitoring = True
            with c2:
                if st.button("Stop Monitoring", use_container_width=True):
                    st.session_state.monitoring = False
                    if st.session_state.real_monitor is not None:
                        st.session_state.real_monitor.close()
                        st.session_state.real_monitor = None
            if st.button("Reset Demo", use_container_width=True):
                st.session_state.monitoring = False
                if st.session_state.real_monitor is not None:
                    st.session_state.real_monitor.close()
                    st.session_state.real_monitor = None
                st.session_state.drowsiness_detector.reset()
                st.session_state.scenario = "Normal"
                st.session_state.tracked_scenario = "Normal"
                st.session_state.scenario_started_at = monotonic()
                st.rerun()
            active_label = "Active (real)" if st.session_state.mode == "REAL MODE" else "Active (demo)"
            st.caption("Monitoring state: " + (active_label if st.session_state.monitoring else "Stopped"))
            st.selectbox(
                "Demo scenario",
                ["Normal", "Blink", "Long Eye Closure", "One Eye Closed", "No Face", "Eye Not Detected"],
                key="scenario",
                disabled=st.session_state.mode == "REAL MODE",
            )

    st.divider()
    if st.session_state.mode == "DEMO MODE":
        st.caption("Demo eye-state inputs are synthetic and for interface preview only.")
    else:
        st.caption("Real inference runs locally from your webcam. The dashboard visualizes the upstream CNN's eye predictions and the project's continuous-closure logic.")


render_dashboard()

# Integration seams for the other project members' components:
# OpenCV supplies the frame/face/eye observations; the ML model supplies the
# OPEN/CLOSED strings passed to DrowsinessDetector.update() above.
