// VAD integration using @ricky0123/vad
import VAD from '@ricky0123/vad';

// Default VAD options – matches spec
const vadOptions = {
  sampleRate: 16000,
  frameSize: 512,
  model: 'silero',
  threshold: 0.5,
  minSpeechFrames: 10,
  minSilenceFrames: 20,
  preSpeechPad: 5,
  redemptionFrames: 8,
  onSpeechStart: (audio) => {
    // Forward to UI and chunker
    window.dispatchEvent(new CustomEvent('vad-speech-start', { detail: audio }));
  },
  onSpeechEnd: (audio) => {
    window.dispatchEvent(new CustomEvent('vad-speech-end', { detail: audio }));
  },
  onError: (err) => {
    console.error('VAD error:', err);
    window.dispatchEvent(new CustomEvent('vad-error', { detail: err }));
  },
  enableMetrics: false,
  onMetrics: () => {}
};

export const vad = new VAD(vadOptions);

export function processFloat32(float32Array) {
  // Feed the audio buffer to VAD (the library handles framing)
  vad.update(float32Array);
}
