// Browser lifecycle checks without accessing a real microphone/camera or speaker.
import fs from 'node:fs';
import assert from 'node:assert/strict';
const source = fs.readFileSync(new URL('../src/browser_alarm.js', import.meta.url), 'utf8');
const render = (await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'))).default;
let interval, listener, starts = 0, stops = 0, trigger;
globalThis.window = {
  setInterval: fn => { interval = fn; return 1; },
  addEventListener: (_, fn) => { listener = fn; },
  removeEventListener: () => { listener = null; },
  AudioContext: class {
    state = 'running'; currentTime = 0; destination = {};
    async resume() {}
    createOscillator() { return { frequency: {setValueAtTime() {}}, connect() {}, disconnect() {}, start() {starts++;}, stop() {stops++;} }; }
    createGain() { return { gain: {setValueAtTime() {}, linearRampToValueAtTime() {}}, connect() {}, disconnect() {} }; }
  }
};
globalThis.Element = class {};
const button = {}, label = {};
const component = {data: {active: false}, parentElement: {querySelector: q => q === 'button' ? button : label}, setTriggerValue: name => { trigger = name; }};
let cleanup = render(component);
interval(); assert.equal(starts, 0, 'No autoplay before user gesture');
await button.onclick(); assert.equal(starts, 1, 'Enable sound plays a test tone');
cleanup(); component.data.active = true; cleanup = render(component);
interval(); assert.equal(starts, 2, 'Active alarm plays');
listener({code: 'Space', target: {}, preventDefault() {}});
assert.equal(trigger, 'space_pressed');
interval(); assert.equal(starts, 2, 'Acknowledgment silences immediately');
cleanup(); component.data.active = false; cleanup = render(component); cleanup();
component.data.active = true; cleanup = render(component);
window.__drowsinessAudio.lastTone = 0; interval();
assert.equal(starts, 3, 'New alarm re-arms');
window.__drowsinessAudio.updated = 0; window.__drowsinessAudio.lastTone = 0; interval();
assert.equal(starts, 3, 'Disconnected dashboard stops repeating');
cleanup(); assert.equal(listener, null); assert.ok(stops > 0);
console.log('Browser alarm lifecycle checks passed');
