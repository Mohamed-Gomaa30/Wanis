# Architecture Context

## Overview

This document provides the AI agent with context about the new architecture being implemented in the Wanis project, specifically focusing on client-side VAD architecture, HTTP POST communication flow, WebSocket fallback architecture, and performance optimization strategies.

## Client-Side VAD Architecture

### Architecture Overview

The client-side VAD architecture moves voice activity detection from the server to the client browser, reducing latency and bandwidth usage while improving privacy.

### Components

#### 1. Audio Capture Layer

**Purpose**: Capture audio from microphone and prepare for processing

**Components**:
- **MediaStream API**: Access microphone
- **AudioContext**: Audio processing context
- **AudioWorklet**: Real-time audio processing
- **Audio Buffer**: Audio data storage

**Flow**:
1. Request microphone access
2. Create AudioContext
3. Create AudioWorklet
4. Stream audio to AudioWorklet
5. Process audio frames

**Code Example**:
```typescript
// Request microphone access
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

// Create audio context
const audioContext = new AudioContext({ sampleRate: 16000 });

// Create audio worklet
const worklet = await audioContext.audioWorklet.addModule('vad-processor.js');
const vadProcessor = new AudioWorkletNode(audioContext, 'vad-processor');

// Connect audio stream
const source = audioContext.createMediaStreamSource(stream);
source.connect(vadProcessor);
```

#### 2. VAD Processing Layer

**Purpose**: Process audio frames and detect speech activity

**Components**:
- **WebAssembly Module**: VAD model execution
- **Frame Processor**: Frame-by-frame processing
- **State Machine**: Speech state management
- **Event Emitter**: Event notification

**Flow**:
1. Receive audio frame
2. Convert to required format
3. Process through VAD model
4. Update speech state
5. Emit events if state changes

**Code Example**:
```typescript
// Process audio frame
function processFrame(audio: Float32Array): VADResult {
  // Convert to required format
  const formatted = convertAudioFormat(audio);

  // Process through VAD model
  const probability = vadModel.process(formatted);

  // Update speech state
  const result = updateState(probability);

  // Emit events if state changes
  if (result.stateChanged) {
    emitEvent(result.event, result.audio);
  }

  return result;
}
```

#### 3. Event Handling Layer

**Purpose**: Handle VAD events and trigger actions

**Components**:
- **Event Listener**: Event subscription
- **Event Dispatcher**: Event routing
- **Action Handler**: Action execution
- **Error Handler**: Error processing

**Flow**:
1. Receive event from VAD layer
2. Dispatch to appropriate handler
3. Execute action
4. Handle errors if any

**Code Example**:
```typescript
// Handle speech start event
vad.onSpeechStart = (audio) => {
  // Start recording
  startRecording(audio);

  // Update UI
  updateUI('speech_detected');

  // Begin STT processing
  prepareSTT(audio);
};

// Handle speech end event
vad.onSpeechEnd = (audio) => {
  // Stop recording
  stopRecording();

  // Update UI
  updateUI('speech_ended');

  // Send to STT service
  sendToSTT(audio);
};
```

#### 4. Communication Layer

**Purpose**: Communicate with server for STT processing

**Components**:
- **HTTP Client**: HTTP request handling
- **WebSocket Client**: WebSocket connection
- **Request Builder**: Request formatting
- **Response Handler**: Response processing

**Flow**:
1. Receive audio from event handler
2. Format request
3. Send to server
4. Process response
5. Return result

**Code Example**:
```typescript
// Send audio to STT service
async function sendToSTT(audio: Float32Array): Promise<STTResponse> {
  // Format request
  const request = formatSTTRequest(audio);

  // Send to server
  const response = await fetch('/api/stt/transcribe', {
    method: 'POST',
    headers: {
      'Content-Type': 'audio/wav',
      'X-Request-ID': generateUUID(),
      'X-Client-ID': 'web-client-v1',
      'X-Session-ID': getSessionID(),
    },
    body: request.body,
  });

  // Process response
  const result = await response.json();
  return result;
}
```

### Data Flow

#### Speech Detection Flow

```
Microphone → MediaStream → AudioContext → AudioWorklet → VAD Model → State Machine → Event Emitter → Event Handler → STT Service
```

#### Speech End Flow

```
VAD Model → State Machine → Event Emitter → Event Handler → STT Service → Response Handler → UI Update
```

#### Error Flow

```
VAD Model → Error Handler → Error Logger → Fallback Manager → WebSocket Mode
```

### State Management

#### Speech States

```typescript
enum SpeechState {
  SILENCE = 'silence',
  PRE_SPEECH = 'pre_speech',
  SPEECH = 'speech',
  POST_SPEECH = 'post_speech',
}
```

#### State Transitions

```
SILENCE → PRE_SPEECH (speech probability > threshold for minSpeechFrames)
PRE_SPEECH → SPEECH (speech probability > threshold)
SPEECH → POST_SPEECH (speech probability < threshold for minSilenceFrames)
POST_SPEECH → SILENCE (speech probability < threshold)
```

#### State Machine

```typescript
class SpeechStateMachine {
  private state: SpeechState = SpeechState.SILENCE;
  private speechFrameCount: number = 0;
  private silenceFrameCount: number = 0;

  update(probability: number): StateTransition {
    const isSpeech = probability > threshold;

    switch (this.state) {
      case SpeechState.SILENCE:
        if (isSpeech) {
          this.speechFrameCount++;
          if (this.speechFrameCount >= minSpeechFrames) {
            this.state = SpeechState.PRE_SPEECH;
            return { event: 'speech_start', audio: getPreSpeechAudio() };
          }
        }
        break;

      case SpeechState.PRE_SPEECH:
        if (isSpeech) {
          this.state = SpeechState.SPEECH;
          return { event: 'speech_confirmed' };
        } else {
          this.state = SpeechState.SILENCE;
          this.speechFrameCount = 0;
          return { event: 'speech_cancelled' };
        }
        break;

      case SpeechState.SPEECH:
        if (!isSpeech) {
          this.silenceFrameCount++;
          if (this.silenceFrameCount >= minSilenceFrames) {
            this.state = SpeechState.POST_SPEECH;
            return { event: 'speech_end', audio: getSpeechAudio() };
          }
        }
        break;

      case SpeechState.POST_SPEECH:
        if (!isSpeech) {
          this.state = SpeechState.SILENCE;
          this.silenceFrameCount = 0;
          return { event: 'silence_confirmed' };
        } else {
          this.state = SpeechState.SPEECH;
          this.silenceFrameCount = 0;
          return { event: 'speech_resumed' };
        }
        break;
    }

    return { event: 'no_change' };
  }
}
```

## HTTP POST Communication Flow

### Flow Overview

The HTTP POST communication flow handles sending audio data from the client to the server for STT processing.

### Request Flow

#### 1. Audio Preparation

**Purpose**: Prepare audio data for transmission

**Steps**:
1. Receive audio from VAD event
2. Convert to required format (WAV)
3. Add metadata headers
4. Encode as binary

**Code Example**:
```typescript
// Prepare audio for transmission
function prepareAudio(audio: Float32Array): ArrayBuffer {
  // Convert to WAV format
  const wav = encodeWAV(audio, {
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16,
  });

  // Return binary data
  return wav;
}
```

#### 2. Request Building

**Purpose**: Build HTTP request with headers and body

**Steps**:
1. Set Content-Type header
2. Add request ID header
3. Add client ID header
4. Add session ID header
5. Add audio metadata headers
6. Add authentication header (if needed)

**Code Example**:
```typescript
// Build HTTP request
function buildRequest(audio: ArrayBuffer): RequestInit {
  return {
    method: 'POST',
    headers: {
      'Content-Type': 'audio/wav',
      'X-Request-ID': generateUUID(),
      'X-Client-ID': 'web-client-v1',
      'X-Session-ID': getSessionID(),
      'X-Audio-Format': 'wav',
      'X-Audio-Sample-Rate': '16000',
      'X-Audio-Channels': '1',
      'X-Audio-Duration': calculateDuration(audio).toString(),
      'Authorization': `Bearer ${getAuthToken()}`,
    },
    body: audio,
  };
}
```

#### 3. Request Sending

**Purpose**: Send request to server

**Steps**:
1. Create fetch request
2. Send to server
3. Wait for response
4. Handle errors

**Code Example**:
```typescript
// Send request to server
async function sendRequest(request: RequestInit): Promise<Response> {
  try {
    const response = await fetch('/api/stt/transcribe', request);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response;
  } catch (error) {
    console.error('Request failed:', error);
    throw error;
  }
}
```

### Response Flow

#### 1. Response Receiving

**Purpose**: Receive response from server

**Steps**:
1. Receive HTTP response
2. Check status code
3. Parse response body
4. Handle errors

**Code Example**:
```typescript
// Receive response from server
async function receiveResponse(response: Response): Promise<STTResponse> {
  // Check status code
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }

  // Parse response body
  const result = await response.json();

  // Return result
  return result;
}
```

#### 2. Response Processing

**Purpose**: Process response and extract transcription

**Steps**:
1. Extract transcription text
2. Extract confidence score
3. Extract language
4. Extract segments
5. Extract alternatives

**Code Example**:
```typescript
// Process response
function processResponse(response: STTResponse): TranscriptionResult {
  return {
    text: response.transcription,
    confidence: response.confidence,
    language: response.language,
    segments: response.segments,
    alternatives: response.alternatives,
    processingTime: response.processing_time_ms,
  };
}
```

#### 3. Result Handling

**Purpose**: Handle transcription result

**Steps**:
1. Update UI with transcription
2. Send to AI companion
3. Log result for analytics
4. Handle errors if any

**Code Example**:
```typescript
// Handle transcription result
function handleResult(result: TranscriptionResult) {
  // Update UI
  updateUI('transcription', result.text);

  // Send to AI companion
  sendToAICompanion(result.text);

  // Log for analytics
  logTranscription(result);

  // Handle errors
  if (result.confidence < 0.5) {
    showLowConfidenceWarning();
  }
}
```

### Error Handling

#### Request Errors

**Types**:
- Network errors
- Timeout errors
- Server errors

**Handling**:
```typescript
// Handle request errors
async function sendWithRetry(audio: ArrayBuffer, maxRetries: number = 3): Promise<STTResponse> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const request = buildRequest(audio);
      const response = await sendRequest(request);
      const result = await receiveResponse(response);
      return result;
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
      await sleep(1000 * Math.pow(2, attempt));
    }
  }
}
```

#### Response Errors

**Types**:
- Invalid audio format
- Invalid audio data
- STT processing errors
- Rate limit errors

**Handling**:
```typescript
// Handle response errors
function handleResponseError(error: STTError): void {
  switch (error.code) {
    case 'INVALID_AUDIO_FORMAT':
      showFormatError();
      break;
    case 'INVALID_AUDIO_DATA':
      showDataError();
      break;
    case 'STT_ERROR':
      showSTTError();
      break;
    case 'RATE_LIMIT_EXCEEDED':
      showRateLimitError();
      break;
    default:
      showGenericError();
  }
}
```

## WebSocket Fallback Architecture

### Architecture Overview

The WebSocket fallback architecture provides an alternative communication path for browsers without WebAssembly support or when client-side VAD performance is insufficient.

### Components

#### 1. WebSocket Connection Layer

**Purpose**: Establish and maintain WebSocket connection

**Components**:
- **WebSocket Client**: WebSocket connection management
- **Connection Manager**: Connection lifecycle
- **Reconnection Manager**: Reconnection logic
- **Heartbeat Manager**: Keep-alive mechanism

**Flow**:
1. Connect to WebSocket endpoint
2. Authenticate connection
3. Send configuration
4. Start audio streaming
5. Maintain connection

**Code Example**:
```typescript
// Connect to WebSocket
async function connectWebSocket(): Promise<WebSocket> {
  const url = `ws://localhost:8000/ws/vad?client_id=web-client-v1&session_id=${getSessionID()}`;

  const ws = new WebSocket(url);

  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  return ws;
}
```

#### 2. Audio Streaming Layer

**Purpose**: Stream audio data to server

**Components**:
- **Audio Capture**: Microphone access
- **Audio Encoder**: Audio format conversion
- **Stream Manager**: Stream lifecycle
- **Buffer Manager**: Audio buffering

**Flow**:
1. Capture audio from microphone
2. Encode audio data
3. Buffer audio chunks
4. Stream to server
5. Handle backpressure

**Code Example**:
```typescript
// Stream audio to server
function streamAudio(ws: WebSocket): void {
  const stream = navigator.mediaDevices.getUserMedia({ audio: true });

  stream.then((mediaStream) => {
    const audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(mediaStream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    processor.onaudioprocess = (event) => {
      const audio = event.inputBuffer.getChannelData(0);
      const message = {
        type: 'audio',
        timestamp: Date.now(),
        sequence: sequence++,
        data: arrayBufferToBase64(audio.buffer),
        format: {
          sample_rate: 16000,
          channels: 1,
          encoding: 'pcm_f32le',
        },
      };
      ws.send(JSON.stringify(message));
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
  });
}
```

#### 3. Event Handling Layer

**Purpose**: Handle VAD events from server

**Components**:
- **Message Parser**: Message parsing
- **Event Dispatcher**: Event routing
- **Action Handler**: Action execution
- **Error Handler**: Error processing

**Flow**:
1. Receive message from server
2. Parse message
3. Dispatch to handler
4. Execute action
5. Handle errors

**Code Example**:
```typescript
// Handle WebSocket messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'speech_start':
      handleSpeechStart(message);
      break;
    case 'speech_end':
      handleSpeechEnd(message);
      break;
    case 'error':
      handleError(message);
      break;
    default:
      console.warn('Unknown message type:', message.type);
  }
};
```

### Data Flow

#### Audio Streaming Flow

```
Microphone → MediaStream → AudioContext → ScriptProcessor → Audio Encoder → WebSocket → Server VAD → STT Service
```

#### Event Flow

```
Server VAD → WebSocket → Message Parser → Event Dispatcher → Event Handler → UI Update
```

#### Error Flow

```
WebSocket → Error Handler → Reconnection Manager → WebSocket Reconnect
```

### Reconnection Strategy

#### Reconnection Logic

**Purpose**: Automatically reconnect on connection loss

**Strategy**:
- Exponential backoff
- Maximum retry limit
- Random jitter
- Connection validation

**Code Example**:
```typescript
// Reconnect with exponential backoff
async function reconnectWithBackoff(url: string, maxRetries: number = 5): Promise<WebSocket> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const ws = new WebSocket(url);
      await waitForOpen(ws);
      return ws;
    } catch (error) {
      const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
      await sleep(delay + Math.random() * 1000);
    }
  }
  throw new Error('Failed to reconnect after ' + maxRetries + ' attempts');
}
```

#### Connection Validation

**Purpose**: Validate connection before use

**Strategy**:
- Send ping message
- Wait for pong response
- Validate response
- Mark as connected

**Code Example**:
```typescript
// Validate connection
async function validateConnection(ws: WebSocket): Promise<boolean> {
  const ping = { type: 'ping', timestamp: Date.now() };
  ws.send(JSON.stringify(ping));

  return new Promise((resolve) => {
    const timeout = setTimeout(() => resolve(false), 5000);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'pong') {
        clearTimeout(timeout);
        resolve(true);
      }
    };
  });
}
```

## Performance Optimization Strategies

### Client-Side Optimization

#### 1. Memory Optimization

**Strategies**:
- Buffer pooling
- Frame batching
- Memory cleanup
- Model pruning

**Code Example**:
```typescript
// Buffer pooling
class AudioBufferPool {
  private buffers: Float32Array[] = [];
  private bufferSize: number;

  constructor(bufferSize: number) {
    this.bufferSize = bufferSize;
  }

  acquire(): Float32Array {
    if (this.buffers.length > 0) {
      return this.buffers.pop()!;
    }
    return new Float32Array(this.bufferSize);
  }

  release(buffer: Float32Array): void {
    this.buffers.push(buffer);
  }
}
```

#### 2. CPU Optimization

**Strategies**:
- Frame skipping
- Adaptive quality
- Worker threads
- SIMD operations

**Code Example**:
```typescript
// Frame skipping
class FrameSkipper {
  private skipCount: number = 0;
  private maxSkipCount: number = 2;

  shouldSkip(): boolean {
    if (this.skipCount >= this.maxSkipCount) {
      this.skipCount = 0;
      return false;
    }
    this.skipCount++;
    return true;
  }
}
```

#### 3. Latency Optimization

**Strategies**:
- Preloading
- Warm-up
- Buffer size optimization
- Priority scheduling

**Code Example**:
```typescript
// Preload model
async function preloadModel(): Promise<void> {
  const vad = new VAD();
  await vad.loadModel();
  await vad.warmup();
}
```

### Server-Side Optimization

#### 1. Request Optimization

**Strategies**:
- Request batching
- Connection pooling
- Compression
- Caching

**Code Example**:
```python
# Request batching
class RequestBatcher:
    def __init__(self, batch_size: int = 10, timeout: float = 0.1):
        self.batch_size = batch_size
        self.timeout = timeout
        self.batch = []
        self.timer = None

    async def add(self, request: STTRequest):
        self.batch.append(request)
        if len(self.batch) >= self.batch_size:
            await self.process_batch()
        elif self.timer is None:
            self.timer = asyncio.create_task(self.wait_for_timeout())

    async def wait_for_timeout(self):
        await asyncio.sleep(self.timeout)
        await self.process_batch()

    async def process_batch(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

        if self.batch:
            await self.process(self.batch)
            self.batch = []
```

#### 2. Response Optimization

**Strategies**:
- Streaming responses
- Compression
- Caching
- CDN

**Code Example**:
```python
# Streaming response
async def stream_response(audio_data: bytes):
    async for chunk in process_audio(audio_data):
        yield chunk
```

#### 3. Model Optimization

**Strategies**:
- Model quantization
- Model pruning
- Model distillation
- GPU acceleration

**Code Example**:
```python
# Model quantization
import torch.quantization

def quantize_model(model):
    model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
    model_prepared = torch.quantization.prepare(model)
    model_quantized = torch.quantization.convert(model_prepared)
    return model_quantized
```

### Network Optimization

#### 1. Bandwidth Optimization

**Strategies**:
- Audio compression
- Adaptive bitrate
- Delta encoding
- Protocol optimization

**Code Example**:
```typescript
// Audio compression
function compressAudio(audio: Float32Array): Uint8Array {
  const encoder = new AudioEncoder();
  const compressed = encoder.encode(audio);
  return compressed;
}
```

#### 2. Latency Optimization

**Strategies**:
- Edge computing
- CDN
- Protocol optimization
- Connection reuse

**Code Example**:
```typescript
// Connection reuse
class ConnectionPool {
  private connections: Map<string, WebSocket> = new Map();

  async getConnection(url: string): Promise<WebSocket> {
    if (this.connections.has(url)) {
      return this.connections.get(url)!;
    }

    const ws = await connectWebSocket(url);
    this.connections.set(url, ws);
    return ws;
  }
}
```

#### 3. Reliability Optimization

**Strategies**:
- Retry logic
- Fallback mechanisms
- Error recovery
- Health checks

**Code Example**:
```typescript
// Retry logic
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3
): Promise<T> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
      await sleep(1000 * Math.pow(2, attempt));
    }
  }
  throw new Error('Max retries exceeded');
}
```

## Architecture Diagrams

### Client-Side VAD Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Microphone   │  │ AudioContext │  │ AudioWorklet │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │ VAD Model   │                          │
│                    │ (WebAssembly)│                         │
│                    └──────┬──────┘                          │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │ State       │                          │
│                    │ Machine     │                          │
│                    └──────┬──────┘                          │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │ Event       │                          │
│                    │ Emitter     │                          │
│                    └──────┬──────┘                          │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │ HTTP Client │                          │
│                    └──────┬──────┘                          │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           │ HTTP POST
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                         Server                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ HTTP Server  │  │ STT Service  │  │ AI Companion │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### WebSocket Fallback Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Microphone   │  │ AudioContext │  │ Script       │      │
│  │              │  │              │  │ Processor    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │ Audio       │                          │
│                    │ Encoder     │                          │
│                    └──────┬──────┘                          │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │ WebSocket   │                          │
│                    │ Client      │                          │
│                    └──────┬──────┘                          │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           │ WebSocket
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                         Server                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ WebSocket    │  │ VAD Service  │  │ STT Service  │      │
│  │ Server       │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Best Practices

### Client-Side Best Practices

1. **Always check browser compatibility** before using client-side VAD
2. **Monitor performance metrics** and fallback if needed
3. **Handle all error types** with appropriate fallback
4. **Use appropriate buffer sizes** for your use case
5. **Test on target browsers** and devices

### Server-Side Best Practices

1. **Use request batching** to improve throughput
2. **Implement rate limiting** to prevent abuse
3. **Use compression** to reduce bandwidth
4. **Implement caching** for repeated requests
5. **Monitor performance** and optimize as needed

### Network Best Practices

1. **Use retry logic** with exponential backoff
2. **Implement fallback mechanisms** for reliability
3. **Use connection pooling** to reduce overhead
4. **Implement health checks** for monitoring
5. **Use compression** to reduce bandwidth

## Common Issues and Solutions

### Issue 1: High Memory Usage

**Symptoms**:
- Memory usage >70MB
- Browser becomes slow

**Solution**:
- Reduce buffer size
- Clear audio buffers
- Restart VAD instance
- Fallback to WebSocket mode

### Issue 2: High CPU Usage

**Symptoms**:
- CPU usage >10%
- Browser becomes unresponsive

**Solution**:
- Reduce frame rate
- Skip frames if CPU is high
- Use smaller model
- Fallback to WebSocket mode

### Issue 3: Slow Detection

**Symptoms**:
- Speech detection latency >100ms
- Speech end detection latency >200ms

**Solution**:
- Reduce frame size
- Optimize buffer size
- Use faster model
- Check system performance

### Issue 4: Connection Issues

**Symptoms**:
- WebSocket connection fails
- HTTP requests timeout

**Solution**:
- Check network connectivity
- Implement retry logic
- Use fallback mechanism
- Check server status

## References

- [WebAssembly Documentation](https://webassembly.org/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [HTTP/1.1 Specification](https://www.rfc-editor.org/rfc/rfc7231)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

## Agent Knowledge Base

### Key Concepts

1. **Client-Side VAD**: VAD processing happens in the browser using WebAssembly
2. **HTTP POST Communication**: Audio data sent via HTTP POST for STT processing
3. **WebSocket Fallback**: Alternative communication path for unsupported browsers
4. **Performance Optimization**: Strategies for optimizing memory, CPU, and latency
5. **Error Handling**: Robust error handling and recovery mechanisms

### Common Questions

**Q: What is the client-side VAD architecture?**
A: VAD processing happens in the browser using WebAssembly, reducing latency and bandwidth.

**Q: What is the HTTP POST communication flow?**
A: Audio data is sent via HTTP POST to the server for STT processing.

**Q: What is the WebSocket fallback architecture?**
A: Alternative communication path for browsers without WebAssembly support.

**Q: How do I optimize performance?**
A: Use memory optimization, CPU optimization, and latency optimization strategies.

**Q: How do I handle errors?**
A: Implement robust error handling with retry logic and fallback mechanisms.

### Technical Guidance

When providing technical guidance about architecture:

1. **Client-Side First**: Use client-side VAD when possible for better performance
2. **Fallback Strategy**: Always have WebSocket fallback for unsupported browsers
3. **Performance Monitoring**: Monitor metrics and fallback if performance degrades
4. **Error Recovery**: Implement robust error handling and recovery
5. **Testing**: Test on multiple browsers and devices

### Architecture Guidance

When providing architectural guidance:

1. **Separation of Concerns**: Separate audio capture, VAD processing, and communication
2. **Event-Driven**: Use event-driven architecture for VAD events
3. **State Management**: Use state machine for speech state management
4. **Error Handling**: Handle all error types with appropriate fallback
5. **Performance**: Optimize for memory, CPU, and latency

## Changelog

### Version 1.0.0 (2026-04-16)
- Initial version
- Documented client-side VAD architecture
- Documented HTTP POST communication flow
- Documented WebSocket fallback architecture
- Documented performance optimization strategies
- Documented best practices
