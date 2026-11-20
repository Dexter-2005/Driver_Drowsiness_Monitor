"""Live browser-camera dashboard using Streamlit transport."""
import base64
import sys
from pathlib import Path
from time import monotonic
import cv2
import numpy as np
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.real_monitor import RealMonitor

st.set_page_config(page_title='Driver Drowsiness Monitor', page_icon='â—‰', layout='wide')
st.markdown("""<style>
.stApp {background:#091321;color:#e8eef8}
.block-container {max-width:1400px;padding-top:2rem}
[data-testid="stMetric"] {background:#142338;border:1px solid #29405c;border-radius:12px;padding:16px;margin-bottom:12px}
[data-testid="stMetricValue"] {font-size:1.8rem;color:#63dfc3}
h1,h3 {color:#e8eef8}
</style>""", unsafe_allow_html=True)
st.title('Driver Drowsiness Monitor')
st.caption('Allow camera access, enable sound, then start the camera. Frames are processed on the server without recording.')

camera = st.components.v2.component('live_camera',
    html='<div style="position:relative"><canvas width="640" height="480" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none"></canvas><video autoplay muted playsinline style="width:100%;max-height:440px;border-radius:12px;background:#111"></video></div><button type="button">Start camera</button><p>Camera stopped</p>',
    js=(ROOT / 'src/browser_camera.js').read_text(encoding='utf-8'))
alarm = st.components.v2.component('driver_alarm',
    html='<button type="button">Enable sound</button> <span role="status"></span>',
    js=(ROOT / 'src/browser_alarm.js').read_text(encoding='utf-8'))

if 'live_monitor' not in st.session_state:
    try:
        with st.spinner('Loading detection modelâ€¦'):
            st.session_state.live_monitor = RealMonitor()
    except Exception as error:
        st.error(f'Model could not load: {error}')
        st.stop()
if 'frame_ack' not in st.session_state:
    st.session_state.frame_ack = None
    st.session_state.camera_active = False

def process_camera_frame():
    monitor = st.session_state.live_monitor
    packet = st.session_state["live-camera"].get("frame")
    if packet and packet.get('id') != st.session_state.frame_ack:
        st.session_state.frame_ack = packet.get('id')
        if packet.get('stopped'):
            monitor.close()
            st.session_state.camera_active = False
        else:
            try:
                image = packet.get('image', '')
                if len(image) > 1000000 or not image.startswith('data:image/jpeg;base64,'):
                    raise ValueError('Invalid camera frame')
                raw = base64.b64decode(image.split(',', 1)[1], validate=True)
                frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    raise ValueError('Camera frame could not be decoded')
                st.session_state.frame_error = None
                monitor.process_frame(frame)
                st.session_state.camera_active = True
            except Exception as error:
                monitor.close()
                st.session_state.camera_active = False
                st.session_state.frame_error = str(error)

@st.fragment(run_every=0.5)
def dashboard():
    monitor = st.session_state.live_monitor
    left, right = st.columns([2, 1])
    with left:
        result = camera(data={'ack': st.session_state.frame_ack, 'heartbeat': monotonic(), 'boxes': monitor.eye_boxes}, key='live-camera', on_frame_change=process_camera_frame)
        alarm(data={'active': monitor.alarm_latched and not monitor.alarm_acknowledged,
                    'heartbeat': monotonic()}, key='browser-alarm', height=45,
              on_space_pressed_change=monitor.acknowledge_alarm)
    with right:
        active = st.session_state.camera_active
        st.subheader('Driver status')
        st.metric('Status', monitor.driver_status if active else 'CAMERA STOPPED')
        st.metric('Left eye', monitor.left_eye if active else 'â€”')
        st.metric('Right eye', monitor.right_eye if active else 'â€”')
        st.metric('Eye closure', f'{monitor.closure_duration if active else 0:.1f} s')
        st.caption('MediaPipe face landmarks · 1.5-second closure threshold')
        threshold = st.slider('Eye closure sensitivity', .12, .32, monitor.threshold, .01,
                              help='Increase if closed eyes remain OPEN. Decrease if open eyes appear CLOSED.')
        if threshold != monitor.threshold:
            monitor.threshold = threshold
            monitor.detector.reset()
        if all(value is not None for value in monitor.ratios):
            st.caption(f'Eyelid ratios: {monitor.ratios[0]:.3f} / {monitor.ratios[1]:.3f}')
        if monitor.alarm_latched:
            st.warning('Alarm silenced' if monitor.alarm_acknowledged else 'Drowsiness alarm active')
            if st.button('Silence alarm', key='silence'):
                monitor.acknowledge_alarm()
                st.rerun(scope='fragment')
        if active and monitor.fps and monitor.fps < 2:
            st.warning('Slow connection. Detection updates may be delayed.')
        if st.session_state.get('frame_error'):
            st.error(st.session_state.frame_error)
        if monitor.last_error:
            st.error(monitor.last_error)
        st.caption(f'Processing: {monitor.fps:.1f} FPS' if active else 'Ready for camera')

dashboard()
