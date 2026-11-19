export default function(component) {
    // Keep the user-unlocked audio context across Streamlit fragment updates.
    const s = window.__drowsinessAudio ||= { context: null, active: false, muted: false };
    const root = component.parentElement;
    const button = root.querySelector('button');
    const label = root.querySelector('[role="status"]');
    const active = Boolean(component.data?.active);
    if (!active) s.muted = false;
    s.active = active;
    s.updated = Date.now();
    const enabled = () => s.context?.state === 'running';
    const stopTone = () => {
        if (s.oscillator) { try { s.oscillator.stop(); } catch (_) {} s.oscillator = null; }
    };
    const tone = () => {
        if (!enabled()) return;
        stopTone();
        const ctx = s.context, osc = ctx.createOscillator(), gain = ctx.createGain();
        const now = ctx.currentTime;
        osc.frequency.setValueAtTime(1700, now);
        osc.frequency.setValueAtTime(2200, now + .18);
        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(.12, now + .02);
        gain.gain.setValueAtTime(.12, now + .32);
        gain.gain.linearRampToValueAtTime(0, now + .38);
        osc.connect(gain); gain.connect(ctx.destination);
        osc.start(); osc.stop(now + .4); s.oscillator = osc;
        osc.onended = () => { osc.disconnect(); gain.disconnect(); };
    };
    button.textContent = enabled() ? 'Test sound' : 'Enable sound';
    label.textContent = enabled() ? 'Browser sound enabled' : 'Enable sound before monitoring';
    button.onclick = async () => {
        try {
            s.context ||= new (window.AudioContext || window.webkitAudioContext)();
            await s.context.resume();
            tone();
            button.textContent = 'Test sound'; label.textContent = 'Browser sound enabled';
        } catch (_) { label.textContent = 'Audio unavailable. Check browser sound permissions.'; }
    };
    const onKey = event => {
        if (!s.active || (event.code !== 'Space' && event.key !== ' ')) return;
        if (event.target instanceof Element && event.target.closest('input, textarea, select, button, [contenteditable="true"]')) return;
        event.preventDefault(); s.muted = true; stopTone();
        component.setTriggerValue('space_pressed', true);
    };
    window.addEventListener('keydown', onKey);
    if (!s.active || s.muted) stopTone();
    // A stale/disconnected dashboard must not leave an endless alarm playing.
    const timer = window.setInterval(() => {
        if (s.active && !s.muted && Date.now() - s.updated < 3000 &&
            (!s.lastTone || Date.now() - s.lastTone >= 850)) {
            tone(); s.lastTone = Date.now();
        }
    }, 100);
    return () => {
        clearInterval(timer); stopTone();
        window.removeEventListener('keydown', onKey);
        button.onclick = null;
    };
}
