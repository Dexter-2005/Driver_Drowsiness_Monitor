export default function(component) {
    const root = component.parentElement;
    const video = root.querySelector('video');
    const button = root.querySelector('button');
    const status = root.querySelector('p');
    const overlay = root.querySelector('canvas');
    if (overlay) {
        const drawing = overlay.getContext('2d');
        drawing.clearRect(0, 0, 640, 480);
        drawing.font = '16px sans-serif';
        drawing.lineWidth = 3;
        for (const item of component.data?.boxes || []) {
            drawing.strokeStyle = drawing.fillStyle = item.label === 'OPEN' ? '#55efb2' : '#ff5566';
            drawing.strokeRect(...item.box);
            drawing.fillText(item.label, item.box[0], Math.max(18, item.box[1] - 5));
        }
    }
    const state = window.__driverCamera ||= {stream: null, sequence: 0, pending: null};
    state.updated = Date.now();
    state.send = component.setStateValue;
    if (component.data?.ack === state.pending) state.pending = null;
    if (state.stream && video.srcObject !== state.stream) {
        video.srcObject = state.stream;
        video.play().catch(() => {});
    }
    const stop = () => {
        state.stream?.getTracks().forEach(track => track.stop());
        state.stream = null;
        state.pending = null;
        video.srcObject = null;
        button.textContent = 'Start camera';
        status.textContent = 'Camera stopped';
        state.send('frame', {id: ++state.sequence, stopped: true});
    };
    button.textContent = state.stream ? 'Stop camera' : 'Start camera';
    button.onclick = async () => {
        if (state.stream) { stop(); return; }
        button.disabled = true;
        try {
            state.stream = await navigator.mediaDevices.getUserMedia({video: {width: {ideal: 640}, height: {ideal: 480}}, audio: false});
            video.srcObject = state.stream;
            await video.play();
            status.textContent = 'Camera active';
            button.textContent = 'Stop camera';
        } catch (error) {
            state.stream?.getTracks().forEach(track => track.stop());
            state.stream = null;
            status.textContent = `Camera could not start: ${error.message}. Allow camera access and close other apps using it.`;
        } finally { button.disabled = false; }
    };
    const canvas = document.createElement('canvas');
    canvas.width = 640; canvas.height = 480;
    clearInterval(state.timer);
    state.timer = setInterval(() => {
        if (state.stream && Date.now() - state.updated > 15000) { stop(); return; }
        if (!state.stream || state.pending !== null || video.readyState < 2) return;
        canvas.getContext('2d').drawImage(video, 0, 0, 640, 480);
        state.pending = ++state.sequence;
        state.send('frame', {id: state.pending, image: canvas.toDataURL('image/jpeg', .7)});
    }, 200);
    // Renders reuse the same camera stream. Release only when truly detached.
    return () => {
        button.onclick = null;
        setTimeout(() => {
            if (!root.host?.isConnected && !root.isConnected) {
                clearInterval(state.timer);
                state.stream?.getTracks().forEach(track => track.stop());
                state.stream = null;
                state.pending = null;
            }
        }, 0);
    };
}
