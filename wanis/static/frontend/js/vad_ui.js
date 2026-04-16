// UI handling for VAD state
const indicator = document.getElementById('vadIndicator');

function setListening(isListening) {
  if (indicator) {
    indicator.style.background = isListening ? '#4caf50' : '#cccccc';
  }
}

window.addEventListener('vad-speech-start', () => setListening(true));
window.addEventListener('vad-speech-end', () => setListening(false));
window.addEventListener('vad-error', () => setListening(false));
