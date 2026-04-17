// MediaStream + AudioWorklet + VAD + STT client
// Uses MediaStream to get raw audio, AudioWorklet to process it, sends to VAD + STT

// UI elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusEl = document.getElementById('status');
const transcriptEl = document.getElementById('transcript');
const canvas = document.getElementById('waveCanvas');
const ctx = canvas.getContext('2d');

let audioContext = null;
let mediaStream = null;
let audioWorklet = null;
let audioWorkletNode = null;
let analyser = null;
let animationId = null;
import { vad, processFloat32 } from './js/vad.js';
import { startChunk, addChunk, getPayload } from './js/audio_chunker.js';
import './js/vad_ui.js'; // ensures UI listener registration
let ws = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function setTranscript(text) {
  transcriptEl.textContent = text;
}

// AudioWorklet code (runs in separate thread)
const audioWorkletCode = `
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    this.sampleRate = 16000;
    this.chunkSize = 4096;  // ~256ms at 16kHz
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    
    // Get raw PCM data
    const inputData = input.getChannelData(0);
    const length = inputData.length;
    
    // Convert Float32 to Int16 PCM
    const pcmData = new Int16Array(length);
    for (let i = 0; i < length; i++) {
      const sample = inputData[i];
      const clamped = Math.max(-1, Math.min(1, sample));
      pcmData[i] = clamped < 0 ? clamped * 32768 : clamped * 32767;
    }
    
    // Copy to output
    output.copyToChannel(inputData, 0);
    
    // Send PCM data to main thread
    this.port.postMessage({
      type: 'audio_chunk',
      data: pcmData.buffer
    }, [pcmData.buffer]);
  }
};

registerProcessor('audio-processor', AudioProcessor);
`;

// Visualize audio waveform
function drawWave() {
  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  analyser.getByteTimeDomainData(dataArray);

  ctx.clearRect(0, 0, width, height);
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#0066ff';
  ctx.beginPath();

  const baseRadius = Math.min(width, height) * 0.3;
  const maxOffset = Math.min(width, height) * 0.15;
  const angleStep = (2 * Math.PI) / bufferLength;

  for (let i = 0; i < bufferLength; i++) {
    const sample = dataArray[i];
    const offset = ((sample - 128) / 128) * maxOffset;
    const radius = baseRadius + offset;
    const angle = i * angleStep - Math.PI / 2;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.stroke();

  animationId = requestAnimationFrame(drawWave);
}

async function start() {
  try {
    setStatus('Initializing…');
    startBtn.disabled = true;
    stopBtn.disabled = true;
    setTranscript('');

    // 1. Get MediaStream from microphone
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    console.log('MediaStream obtained');

    // 2. Create AudioContext
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(mediaStream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);

    // 3. Set up WebSocket
    ws = new WebSocket('ws://localhost:8001/ws');
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      setStatus('Running');
      stopBtn.disabled = false;
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'transcript') {
          setTranscript(data.text);
          console.log(`Transcript: ${data.text}`);
        }
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };

    ws.onerror = (e) => {
      console.error('WebSocket error:', e);
    };

    ws.onclose = () => {
      setStatus('Disconnected');
      console.log('WebSocket closed');
    };

    // 4. Load AudioWorklet
    const blob = new Blob([audioWorkletCode], { type: 'application/javascript' });
    const workletUrl = URL.createObjectURL(blob);
    audioWorklet = await audioContext.audioWorklet.addModule(workletUrl);
    console.log('AudioWorklet loaded');

    // 5. Create AudioWorkletNode
    audioWorkletNode = new AudioWorkletNode(
      audioContext,
      'audio-processor',
      { numberOfOutputs: 1, numberOfInputs: 1 }
    );

    // 6. Connect audio graph
    source.connect(audioWorkletNode);
    audioWorkletNode.connect(analyser);
    audioWorkletNode.connect(audioContext.destination);

    // 7. Handle PCM data from AudioWorklet
audioWorkletNode.port.onmessage = (event) => {
  if (event.data.type === 'audio_chunk') {
    // Convert Int16 PCM to Float32 for VAD processing
    const pcmInt16 = new Int16Array(event.data.data);
    const float32 = new Float32Array(pcmInt16.length);
    for (let i = 0; i < pcmInt16.length; i++) {
      float32[i] = pcmInt16[i] / 32768;
    }
    // Feed audio to VAD (processFloat32 handles framing internally)
    processFloat32(float32);
    // Add chunk to our custom chunker (stores base64 PCM)
    addChunk(float32);
  }
};

    // 8. Start visualization
    drawWave();
    console.log('Audio capture started');

  } catch (err) {
    console.error(err);
    setStatus('Error: ' + err.message);
    startBtn.disabled = true;
  }
}

window.addEventListener('load', start);

function stop() {
  // Stop AudioWorklet
  if (audioWorkletNode) {
    audioWorkletNode.disconnect();
    audioWorkletNode.port.close();
    audioWorkletNode = null;
  }

  // Stop animation
  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }

  // Stop media stream
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }

  // Close AudioContext
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  // Close WebSocket
  if (ws) {
    ws.close();
    ws = null;
  }

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  setStatus('Stopped');
  startBtn.disabled = false;
  stopBtn.disabled = true;
}

startBtn.addEventListener('click', start);
stopBtn.addEventListener('click', stop);
