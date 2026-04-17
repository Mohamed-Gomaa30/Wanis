/* ══════════════════════════════════════════════════════════
   Wanis – Client-side audio streaming (WebSocket)
   Streams mic PCM → server-side VAD + STT + LLM + TTS
   ══════════════════════════════════════════════════════════ */

// ── DOM References ──────────────────────────────────────
const chatArea = document.getElementById("chatArea");
const emptyState = document.getElementById("emptyState");
const canvas = document.getElementById("visualizer");
const micBtn = document.getElementById("micBtn");
const micLabel = document.getElementById("micLabel");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const canvasCtx = canvas.getContext("2d");

// ── State ───────────────────────────────────────────────
let ws = null;
let audioContext = null;
let processor = null;
let sourceNode = null;
let mediaStream = null;
let analyser = null;
let visualizerFrame = null;
let isRecording = false;

// ── Helpers ─────────────────────────────────────────────

function setStatus(text, dotClass) {
    statusText.textContent = text;
    statusDot.className = "status-dot " + (dotClass || "");
}

function addBubble(text, type) {
    // Hide empty state on first message
    if (emptyState) emptyState.classList.add("hidden");

    const bubble = document.createElement("div");
    bubble.className = "bubble notranslate " + type;
    bubble.textContent = text;
    chatArea.appendChild(bubble);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function floatTo16BitPCM(float32Array) {
    const out = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
}

function downsampleBuffer(buffer, inputSampleRate, targetSampleRate) {
    if (targetSampleRate >= inputSampleRate) return buffer;
    const ratio = inputSampleRate / targetSampleRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
        let accum = 0;
        let count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        result[offsetResult] = count ? accum / count : 0;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

function pcmChunkToBase64(int16Array) {
    const bytes = new Uint8Array(int16Array.buffer);
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
    }
    return btoa(binary);
}

function playHexAudio(hexData) {
    if (!hexData) return;
    const pairs = hexData.match(/[\da-f]{2}/gi);
    if (!pairs) return;
    const bytes = new Uint8Array(pairs.map(h => parseInt(h, 16)));
    const blob = new Blob([bytes], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.play().catch(() => { });
}

// ── Visualizer ──────────────────────────────────────────

function draw() {
    if (!analyser) return;
    const width = canvas.width;
    const height = canvas.height;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    // Dark background
    canvasCtx.fillStyle = "rgba(0, 0, 0, 0.25)";
    canvasCtx.fillRect(0, 0, width, height);

    // Waveform line
    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = "#22d3c5";
    canvasCtx.shadowBlur = 6;
    canvasCtx.shadowColor = "rgba(34, 211, 197, 0.5)";
    canvasCtx.beginPath();

    let x = 0;
    const sliceWidth = width / bufferLength;
    for (let i = 0; i < bufferLength; i++) {
        const y = (dataArray[i] / 128.0) * height / 2;
        if (i === 0) canvasCtx.moveTo(x, y);
        else canvasCtx.lineTo(x, y);
        x += sliceWidth;
    }
    canvasCtx.lineTo(width, height / 2);
    canvasCtx.stroke();
    canvasCtx.shadowBlur = 0;

    visualizerFrame = requestAnimationFrame(draw);
}

// ── Audio Graph ─────────────────────────────────────────

function stopAudioGraph() {
    if (processor) {
        processor.disconnect();
        processor.onaudioprocess = null;
        processor = null;
    }
    if (sourceNode) { sourceNode.disconnect(); sourceNode = null; }
    if (audioContext) { audioContext.close(); audioContext = null; }
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    if (visualizerFrame) {
        cancelAnimationFrame(visualizerFrame);
        visualizerFrame = null;
    }
    analyser = null;
}

// ── Recording ───────────────────────────────────────────

async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
        addBubble("خطأ: المتصفح لا يدعم الميكروفون", "system");
        return;
    }
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: { sampleRate: 16000, channelCount: 1 },
        });
        ws = new WebSocket(`ws://${window.location.host}/ws`);

        ws.onopen = () => {
            addBubble("تم الاتصال بالخادم", "system");
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            sourceNode = audioContext.createMediaStreamSource(mediaStream);
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 2048;
            processor = audioContext.createScriptProcessor(4096, 1, 1);

            processor.onaudioprocess = (event) => {
                if (!ws || ws.readyState !== WebSocket.OPEN) return;
                const input = event.inputBuffer.getChannelData(0);
                const downsampled = downsampleBuffer(input, audioContext.sampleRate, 16000);
                const int16 = floatTo16BitPCM(downsampled);
                const b64 = pcmChunkToBase64(int16);
                ws.send(
                    JSON.stringify({
                        type: "audio_chunk",
                        data: b64,
                        request_id: Date.now(),
                    })
                );
            };

            sourceNode.connect(analyser);
            sourceNode.connect(processor);
            processor.connect(audioContext.destination);
            draw();

            isRecording = true;
            micBtn.classList.add("recording");
            micBtn.textContent = "⏹";
            micLabel.textContent = "اضغط للإيقاف";
            setStatus("يستمع...", "listening");
        };

        ws.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            if (msg.type === "vad") {
                if (msg.status === "listening") setStatus("يستمع...", "listening");
                if (msg.status === "processing") setStatus("يعالج...", "processing");
            } else if (msg.type === "transcription") {
                addBubble(msg.text, "user");
            } else if (msg.type === "audio") {
                addBubble(msg.sentence, "bot");
                playHexAudio(msg.data);
            } else if (msg.type === "done") {
                setStatus("يستمع...", "listening");
            } else if (msg.type === "error") {
                addBubble(`خطأ: ${msg.message}`, "system");
            }
        };

        ws.onclose = () => {
            addBubble("تم قطع الاتصال - سيتم إعادة الاتصال تلقائياً", "system");
            if (isRecording) {
                stopAudioGraph();
                isRecording = false;
                handleAutoRestart();
            }
        };

        ws.onerror = () => {
            addBubble("خطأ في الاتصال", "system");
        };
    } catch (err) {
        addBubble(`خطأ: ${err.message}`, "system");
    }
}

function stopRecording() {
    stopAudioGraph();
    if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    ws = null;
    isRecording = false;
    micBtn.classList.remove("recording");
    micBtn.textContent = "🎤";
    micLabel.textContent = "اضغط للتحدث";
    setStatus("متوقف", "");
}

// ── Auto-Start / Always Active ──────────────────────────

// Browsers block AudioContext until a user interaction.
// We'll listen for the first click anywhere to start the "Always Active" mode.
window.addEventListener("click", () => {
    if (!audioContext && !isRecording) {
        console.log("User interacted, auto-starting always-active mode...");
        startRecording();
    }
}, { once: true });

// Auto-restart if WebSocket closes unexpectedly
function handleAutoRestart() {
    if (isRecording) {
        console.log("Connection lost, attempting auto-restart...");
        setTimeout(() => {
            if (!isRecording) startRecording();
        }, 2000);
    }
}

// ── Event Listeners ─────────────────────────────────────

micBtn.addEventListener("click", (e) => {
    e.stopPropagation(); // Don't trigger the window click listener
    if (isRecording) stopRecording();
    else startRecording();
});

// Resize canvas to match container width
function resizeCanvas() {
    canvas.width = canvas.parentElement.offsetWidth;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();
