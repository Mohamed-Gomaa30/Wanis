// Simple audio chunker for client‑side VAD segments
let currentChunk = [];
let sequence = 0;
let requestId = crypto.randomUUID();

export function startChunk() {
  currentChunk = [];
  sequence = 0;
  requestId = crypto.randomUUID();
}

export function addChunk(floatArray) {
  // Convert Float32Array to base64 PCM (Int16)
  const int16 = new Int16Array(floatArray.length);
  for (let i = 0; i < floatArray.length; i++) {
    const s = Math.max(-1, Math.min(1, floatArray[i]));
    int16[i] = s < 0 ? s * 32768 : s * 32767;
  }
  const base64 = btoa(String.fromCharCode(...new Uint8Array(int16.buffer)));
  currentChunk.push({
    sequence: ++sequence,
    timestamp: Date.now(),
    data: base64,
    audio_format: { sample_rate: 16000, channels: 1, encoding: 'pcm_s16le' }
  });
}

export function getPayload() {
  return {
    request_id: requestId,
    client_vad: true,
    chunks: currentChunk
  };
}
