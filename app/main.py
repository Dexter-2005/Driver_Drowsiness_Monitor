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

st.set_page_config(page_title='Driver Drowsiness Monitor', page_icon='◉', layout='wide')
st.title('Driver Drowsiness Detection System')
st.caption('Allow camera access, enable sound, then start the camera. Frames are processed on the server without recording.')

camera = st.components.v2.component('live_camera',
    html='<video autoplay muted playsinline style="width:100%;max-height:440px;border-radius:12px;background:#111"></video><button type="button">Start camera</button><p>Camera stopped</p>',
    js=(ROOT / 'src/browser_camera.js').read_text(encoding='utf-8'))
alarm = st.components.v2.component('driver_alarm',
    html='<button type="button">Enable sound</button> <span role="status"></span>',
    js=(ROOT / 'src/browser_alarm.js').read_text(encoding='utf-8'))

if 'live_monitor' not in st.session_state:
    try:
        with st.spinner('Loading detection model…'):
            st.session_state.live_monitor = RealMonitor()
    except Exception as error:
        st.error(f'Model could not load: {error}')
        st.stop()
if 'frame_ack' not in st.session_state:
    st.session_state.frame_ack = None
    st.session_state.camera_active = False

@st.fragment(run_every=0.5)
def dashboard():
    monitor = st.session_state.live_monitor
    left, right = st.columns([2, 1])
    with left:
        result = camera(data={'ack': st.session_state.frame_ack, 'heartbeat': monotonic()}, key='live-camera', on_frame_change=lambda: None)
        packet = result.frame
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
                    monitor.process_frame(frame)
                    st.session_state.camera_active = True
                except Exception as error:
                    monitor.close()
                    st.session_state.camera_active = False
                    st.error(str(error))
        alarm(data={'active': monitor.alarm_latched and not monitor.alarm_acknowledged,
                    'heartbeat': monotonic()}, key='browser-alarm', height=45,
              on_space_pressed_change=monitor.acknowledge_alarm)
    with right:
        active = st.session_state.camera_active
        st.subheader('Driver status')
        st.metric('Status', monitor.driver_status if active else 'CAMERA STOPPED')
        st.metric('Left eye', monitor.left_eye if active else '—')
        st.metric('Right eye', monitor.right_eye if active else '—')
        st.metric('Eye closure', f'{monitor.closure_duration if active else 0:.1f} s')
        st.caption('Drowsiness threshold: 1.5 seconds')
        if monitor.alarm_latched:
            st.warning('Alarm silenced' if monitor.alarm_acknowledged else 'Drowsiness alarm active')
            if st.button('Silence alarm', key='silence'):
                monitor.acknowledge_alarm()
                st.rerun(scope='fragment')
        if monitor.last_error:
            st.error(monitor.last_error)
        st.caption(f'Processing: {monitor.fps:.1f} FPS' if active else 'Ready for camera')

dashboard()
