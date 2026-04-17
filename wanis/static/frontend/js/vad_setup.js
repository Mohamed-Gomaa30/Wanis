import { startChunk, getPayload } from './audio_chunker.js';

export function registerVAD(ws) {
  // Start a new chunk when client VAD signals speech start
  window.addEventListener('vad-speech-start', () => {
    startChunk();
    console.log('VAD speech start – chunking begun');
  });

  // When speech ends, send the accumulated payload over the provided WebSocket
  window.addEventListener('vad-speech-end', () => {
    const payload = getPayload();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
      console.log('Sent VAD segment payload');
    }
  });
}
