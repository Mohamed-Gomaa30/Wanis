# WebSocket Fallback Contract

## Overview

This contract defines the WebSocket interface for browsers without WebAssembly support or when client-side VAD performance is insufficient. The fallback uses server-side VAD and maintains the same functionality as the client-side VAD implementation.

## Version

- **Version**: 1.0.0
- **Date**: 2026-04-16
- **Status**: Final

## Interface Definition

### Connection Protocol

#### WebSocket URL

```
ws://localhost:8000/ws/vad
```

#### Secure WebSocket URL (Production)

```
wss://api.wanis.ai/ws/vad
```

#### Connection Parameters

**Query Parameters**:

- `client_id`: Client identifier (required)
  - Format: String
  - Example: `web-client-v1`

- `session_id`: Session identifier (required)
  - Format: UUID v4
  - Example: `550e8400-e29b-41d4-a716-446655440000`

- `token`: Authentication token (optional, production)
  - Format: JWT
  - Example: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**Example URL**:

```
ws://localhost:8000/ws/vad?client_id=web-client-v1&session_id=550e8400-e29b-41d4-a716-446655440000
```

#### Connection Headers

```http
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <key>
Sec-WebSocket-Version: 13
Sec-WebSocket-Protocol: vad-v1
Origin: <origin>
```

**Header Descriptions**:

- `Upgrade`: Protocol upgrade to WebSocket
- `Connection`: Connection upgrade
- `Sec-WebSocket-Key`: WebSocket key for handshake
- `Sec-WebSocket-Version`: WebSocket protocol version
- `Sec-WebSocket-Protocol`: Subprotocol (vad-v1)
- `Origin`: Origin of the request

### Message Types

#### Client → Server Messages

##### 1. Audio Data Message

**Type**: `audio`

**Purpose**: Send audio data to server for VAD processing

**Format**:

```json
{
  "type": "audio",
  "timestamp": 1713270000000,
  "sequence": 1,
  "data": "<base64_encoded_audio>",
  "format": {
    "sample_rate": 16000,
    "channels": 1,
    "encoding": "pcm_s16le"
  }
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `audio`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `sequence`: Sequence number for ordering (required)
  - Format: Number
  - Example: `1`

- `data`: Base64-encoded audio data (required)
  - Format: String
  - Encoding: Base64
  - Size: <64KB per message

- `format`: Audio format information (required)
  - `sample_rate`: Sample rate in Hz (required)
    - Values: `8000`, `16000`, `22050`, `44100`, `48000`
    - Default: `16000`
  - `channels`: Number of channels (required)
    - Values: `1`, `2`
    - Default: `1`
  - `encoding`: Audio encoding (required)
    - Values: `pcm_s16le`, `pcm_f32le`
    - Default: `pcm_s16le`

**Example**:

```json
{
  "type": "audio",
  "timestamp": 1713270000000,
  "sequence": 1,
  "data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
  "format": {
    "sample_rate": 16000,
    "channels": 1,
    "encoding": "pcm_s16le"
  }
}
```

##### 2. Configuration Message

**Type**: `config`

**Purpose**: Configure VAD parameters

**Format**:

```json
{
  "type": "config",
  "timestamp": 1713270000000,
  "vad": {
    "threshold": 0.5,
    "min_speech_frames": 10,
    "min_silence_frames": 20,
    "pre_speech_pad": 5,
    "redemption_frames": 8
  }
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `config`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `vad`: VAD configuration (required)
  - `threshold`: Speech probability threshold (0.0-1.0)
    - Default: `0.5`
  - `min_speech_frames`: Minimum frames to consider speech
    - Default: `10`
  - `min_silence_frames`: Minimum frames to consider silence
    - Default: `20`
  - `pre_speech_pad`: Frames to include before speech start
    - Default: `5`
  - `redemption_frames`: Frames to wait before ending speech
    - Default: `8`

**Example**:

```json
{
  "type": "config",
  "timestamp": 1713270000000,
  "vad": {
    "threshold": 0.5,
    "min_speech_frames": 10,
    "min_silence_frames": 20,
    "pre_speech_pad": 5,
    "redemption_frames": 8
  }
}
```

##### 3. Ping Message

**Type**: `ping`

**Purpose**: Keep connection alive

**Format**:

```json
{
  "type": "ping",
  "timestamp": 1713270000000
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `ping`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

**Example**:

```json
{
  "type": "ping",
  "timestamp": 1713270000000
}
```

##### 4. Close Message

**Type**: `close`

**Purpose**: Close connection gracefully

**Format**:

```json
{
  "type": "close",
  "timestamp": 1713270000000,
  "reason": "user_initiated"
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `close`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `reason`: Close reason (optional)
  - Format: String
  - Values: `user_initiated`, `error`, `timeout`, `switch_to_client_vad`
  - Default: `user_initiated`

**Example**:

```json
{
  "type": "close",
  "timestamp": 1713270000000,
  "reason": "user_initiated"
}
```

#### Server → Client Messages

##### 1. Speech Start Message

**Type**: `speech_start`

**Purpose**: Notify client that speech has started

**Format**:

```json
{
  "type": "speech_start",
  "timestamp": 1713270000000,
  "sequence": 1,
  "probability": 0.85,
  "audio": "<base64_encoded_audio>"
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `speech_start`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `sequence`: Sequence number (required)
  - Format: Number
  - Example: `1`

- `probability`: Speech probability (required)
  - Format: Number (0.0-1.0)
  - Example: `0.85`

- `audio`: Base64-encoded pre-speech audio (optional)
  - Format: String
  - Encoding: Base64
  - Size: <64KB

**Example**:

```json
{
  "type": "speech_start",
  "timestamp": 1713270000000,
  "sequence": 1,
  "probability": 0.85,
  "audio": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
}
```

##### 2. Speech End Message

**Type**: `speech_end`

**Purpose**: Notify client that speech has ended

**Format**:

```json
{
  "type": "speech_end",
  "timestamp": 1713270000000,
  "sequence": 100,
  "duration_ms": 5000,
  "audio": "<base64_encoded_audio>",
  "transcription": {
    "text": "مرحبا، كيف حالك؟",
    "confidence": 0.95,
    "language": "ar"
  }
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `speech_end`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `sequence`: Sequence number (required)
  - Format: Number
  - Example: `100`

- `duration_ms`: Speech duration in milliseconds (required)
  - Format: Number
  - Example: `5000`

- `audio`: Base64-encoded complete speech audio (required)
  - Format: String
  - Encoding: Base64
  - Size: <10MB

- `transcription`: Transcription result (optional)
  - `text`: Transcription text
    - Format: String
    - Example: `مرحبا، كيف حالك؟`
  - `confidence`: Confidence score
    - Format: Number (0.0-1.0)
    - Example: `0.95`
  - `language`: Detected language
    - Format: String
    - Values: `ar`, `en`, `ar-EG`
    - Example: `ar`

**Example**:

```json
{
  "type": "speech_end",
  "timestamp": 1713270000000,
  "sequence": 100,
  "duration_ms": 5000,
  "audio": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
  "transcription": {
    "text": "مرحبا، كيف حالك؟",
    "confidence": 0.95,
    "language": "ar"
  }
}
```

##### 3. Pong Message

**Type**: `pong`

**Purpose**: Respond to ping message

**Format**:

```json
{
  "type": "pong",
  "timestamp": 1713270000000,
  "ping_timestamp": 1713269999000
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `pong`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `ping_timestamp`: Original ping timestamp (required)
  - Format: Number
  - Example: `1713269999000`

**Example**:

```json
{
  "type": "pong",
  "timestamp": 1713270000000,
  "ping_timestamp": 1713269999000
}
```

##### 4. Error Message

**Type**: `error`

**Purpose**: Notify client of errors

**Format**:

```json
{
  "type": "error",
  "timestamp": 1713270000000,
  "code": "INVALID_AUDIO_FORMAT",
  "message": "Unsupported audio format",
  "details": {
    "provided_format": "pcm_s32le",
    "supported_formats": ["pcm_s16le", "pcm_f32le"]
  }
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `error`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `code`: Error code (required)
  - Format: String
  - Values: See Error Codes section

- `message`: Human-readable error message (required)
  - Format: String
  - Example: `Unsupported audio format`

- `details`: Additional error details (optional)
  - Format: Object
  - Example: `{ "provided_format": "pcm_s32le", "supported_formats": ["pcm_s16le", "pcm_f32le"] }`

**Example**:

```json
{
  "type": "error",
  "timestamp": 1713270000000,
  "code": "INVALID_AUDIO_FORMAT",
  "message": "Unsupported audio format",
  "details": {
    "provided_format": "pcm_s32le",
    "supported_formats": ["pcm_s16le", "pcm_f32le"]
  }
}
```

##### 5. Close Message

**Type**: `close`

**Purpose**: Notify client that connection is closing

**Format**:

```json
{
  "type": "close",
  "timestamp": 1713270000000,
  "reason": "server_shutdown",
  "code": 1000
}
```

**Fields**:

- `type`: Message type (required)
  - Value: `close`

- `timestamp`: Unix timestamp in milliseconds (required)
  - Format: Number
  - Example: `1713270000000`

- `reason`: Close reason (required)
  - Format: String
  - Values: `server_shutdown`, `error`, `timeout`, `switch_to_client_vad`
  - Example: `server_shutdown`

- `code`: WebSocket close code (required)
  - Format: Number
  - Values: See WebSocket Close Codes
  - Example: `1000`

**Example**:

```json
{
  "type": "close",
  "timestamp": 1713270000000,
  "reason": "server_shutdown",
  "code": 1000
}
```

### Error Codes

#### Client Errors

| Code | Message | Description |
|------|---------|-------------|
| `INVALID_MESSAGE` | Invalid message format | Message format is invalid |
| `INVALID_AUDIO_FORMAT` | Unsupported audio format | Audio format is not supported |
| `INVALID_AUDIO_DATA` | Invalid audio data | Audio data is corrupted |
| `MISSING_FIELD` | Missing required field | Required field is missing |
| `INVALID_FIELD` | Invalid field value | Field value is invalid |
| `SEQUENCE_ERROR` | Sequence number error | Sequence number is out of order |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | Too many messages sent |

#### Server Errors

| Code | Message | Description |
|------|---------|-------------|
| `INTERNAL_ERROR` | Internal server error | Server encountered an error |
| `VAD_ERROR` | VAD processing error | VAD processing failed |
| `STT_ERROR` | STT processing error | STT processing failed |
| `AUDIO_PROCESSING_ERROR` | Audio processing error | Audio processing failed |
| `SERVICE_UNAVAILABLE` | Service unavailable | Service is temporarily unavailable |

### Audio Streaming Format

#### Audio Chunk Size

- **Recommended**: 4096 samples (256ms at 16kHz)
- **Minimum**: 1024 samples (64ms at 16kHz)
- **Maximum**: 16384 samples (1024ms at 16kHz)

#### Audio Encoding

**Supported Encodings**:

1. **PCM 16-bit Little-Endian** (`pcm_s16le`)
   - Sample size: 16 bits
   - Byte order: Little-endian
   - Range: -32768 to 32767

2. **PCM 32-bit Float Little-Endian** (`pcm_f32le`)
   - Sample size: 32 bits
   - Byte order: Little-endian
   - Range: -1.0 to 1.0

#### Audio Configuration

```typescript
interface AudioConfig {
  sampleRate: number;    // Sample rate in Hz (16000)
  channels: number;      // Number of channels (1)
  encoding: string;      // Audio encoding (pcm_s16le)
  chunkSize: number;     // Chunk size in samples (4096)
}
```

### Fallback Detection Logic

#### Feature Detection

```typescript
interface BrowserSupport {
  webAssembly: boolean;
  audioContext: boolean;
  mediaStream: boolean;
  webWorkers: boolean;
}

function detectBrowserSupport(): BrowserSupport {
  return {
    webAssembly: typeof WebAssembly === 'object',
    audioContext: typeof AudioContext !== 'undefined',
    mediaStream: typeof MediaStream !== 'undefined',
    webWorkers: typeof Worker !== 'undefined',
  };
}

function shouldUseWebSocketFallback(): boolean {
  const support = detectBrowserSupport();
  return !support.webAssembly || !support.audioContext || !support.mediaStream;
}
```

#### Performance Detection

```typescript
interface PerformanceMetrics {
  memoryUsage: number;    // Memory usage in MB
  cpuUsage: number;       // CPU usage in percentage
  processingTime: number; // Processing time in ms
}

function shouldFallbackDueToPerformance(metrics: PerformanceMetrics): boolean {
  return (
    metrics.memoryUsage > 70 ||
    metrics.cpuUsage > 10 ||
    metrics.processingTime > 20
  );
}
```

#### Timeout Detection

```typescript
function shouldFallbackDueToTimeout(
  startTime: number,
  timeout: number
): boolean {
  const elapsed = Date.now() - startTime;
  return elapsed > timeout;
}
```

### Reconnection Strategy

#### Reconnection Configuration

```typescript
interface ReconnectionConfig {
  maxRetries: number;        // Maximum retry attempts (default: 5)
  initialDelay: number;      // Initial delay in ms (default: 1000)
  maxDelay: number;          // Maximum delay in ms (default: 30000)
  backoffFactor: number;     // Exponential backoff factor (default: 2)
  jitter: boolean;           // Add random jitter (default: true)
}

const DEFAULT_RECONNECTION_CONFIG: ReconnectionConfig = {
  maxRetries: 5,
  initialDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 2,
  jitter: true,
};
```

#### Reconnection Algorithm

```typescript
async function connectWithRetry(
  url: string,
  config: ReconnectionConfig = DEFAULT_RECONNECTION_CONFIG
): Promise<WebSocket> {
  let lastError: Error;

  for (let attempt = 0; attempt < config.maxRetries; attempt++) {
    try {
      const ws = new WebSocket(url);
      await waitForOpen(ws);
      return ws;
    } catch (error) {
      lastError = error;

      const delay = calculateDelay(attempt, config);
      await sleep(delay);
    }
  }

  throw lastError;
}

function calculateDelay(
  attempt: number,
  config: ReconnectionConfig
): number {
  let delay = config.initialDelay * Math.pow(config.backoffFactor, attempt);
  delay = Math.min(delay, config.maxDelay);

  if (config.jitter) {
    delay = delay * (0.5 + Math.random());
  }

  return delay;
}
```

### Data Types

#### WebSocketMessage

```typescript
type WebSocketMessage =
  | AudioMessage
  | ConfigMessage
  | PingMessage
  | CloseMessage
  | SpeechStartMessage
  | SpeechEndMessage
  | PongMessage
  | ErrorMessage;

interface AudioMessage {
  type: 'audio';
  timestamp: number;
  sequence: number;
  data: string;
  format: AudioFormat;
}

interface ConfigMessage {
  type: 'config';
  timestamp: number;
  vad: VADConfig;
}

interface PingMessage {
  type: 'ping';
  timestamp: number;
}

interface CloseMessage {
  type: 'close';
  timestamp: number;
  reason?: string;
}

interface SpeechStartMessage {
  type: 'speech_start';
  timestamp: number;
  sequence: number;
  probability: number;
  audio?: string;
}

interface SpeechEndMessage {
  type: 'speech_end';
  timestamp: number;
  sequence: number;
  duration_ms: number;
  audio: string;
  transcription?: TranscriptionResult;
}

interface PongMessage {
  type: 'pong';
  timestamp: number;
  ping_timestamp: number;
}

interface ErrorMessage {
  type: 'error';
  timestamp: number;
  code: string;
  message: string;
  details?: any;
}

interface AudioFormat {
  sample_rate: number;
  channels: number;
  encoding: string;
}

interface VADConfig {
  threshold: number;
  min_speech_frames: number;
  min_silence_frames: number;
  pre_speech_pad: number;
  redemption_frames: number;
}

interface TranscriptionResult {
  text: string;
  confidence: number;
  language: string;
}
```

### Performance Requirements

#### Latency

- **Speech Detection**: <100ms from speech start
- **Speech End Detection**: <150ms from speech end
- **Message Round-trip**: <50ms
- **Reconnection**: <5s

#### Throughput

- **Audio Messages**: 50 messages per second
- **Total Bandwidth**: <1Mbps

#### Resource Usage

- **Memory per Connection**: <20MB
- **CPU per Connection**: <2%
- **Concurrent Connections**: 100

### Security Considerations

#### Authentication

- Validate authentication tokens
- Check token expiration
- Verify token scopes
- Log authentication attempts

#### Input Validation

- Validate message format
- Validate audio format
- Validate field values
- Sanitize all inputs

#### Rate Limiting

- Enforce rate limits per connection
- Enforce rate limits per client
- Enforce global rate limits
- Drop excess messages

#### Data Privacy

- Audio data is processed in memory
- Audio data is not stored permanently
- Audio data is not shared with third parties
- Transcription results are not logged

### Testing Requirements

#### Unit Tests

- Test message parsing
- Test message validation
- Test error handling
- Test reconnection logic

#### Integration Tests

- Test with real WebSocket connection
- Test with real audio data
- Test VAD event triggering
- Test error scenarios

#### Performance Tests

- Measure latency
- Measure throughput
- Measure resource usage
- Test under load

### Implementation Notes

#### Connection Lifecycle

1. Client connects to WebSocket endpoint
2. Server validates connection parameters
3. Server sends welcome message
4. Client sends configuration message
5. Client starts sending audio messages
6. Server processes audio with VAD
7. Server sends VAD events to client
8. Client or server closes connection

#### Message Processing

1. Receive message from WebSocket
2. Parse message JSON
3. Validate message format
4. Process message based on type
5. Send response if needed
6. Handle errors if any

#### Audio Processing

1. Receive audio message
2. Decode base64 audio data
3. Convert audio format if needed
4. Process audio with VAD
5. Detect speech events
6. Send event messages to client

#### Error Handling

1. Detect error condition
2. Create error message
3. Send error message to client
4. Log error details
5. Close connection if needed

## Examples

### Basic Connection

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/ws/vad?client_id=web-client-v1&session_id=550e8400-e29b-41d4-a716-446655440000'
);

ws.onopen = () => {
  console.log('Connected to WebSocket');

  // Send configuration
  ws.send(JSON.stringify({
    type: 'config',
    timestamp: Date.now(),
    vad: {
      threshold: 0.5,
      min_speech_frames: 10,
      min_silence_frames: 20,
      pre_speech_pad: 5,
      redemption_frames: 8,
    },
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'speech_start':
      console.log('Speech started', message.probability);
      break;
    case 'speech_end':
      console.log('Speech ended', message.transcription);
      break;
    case 'error':
      console.error('Error:', message.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  console.log('WebSocket closed', event.code, event.reason);
};
```

### Sending Audio Data

```javascript
let sequence = 0;

function sendAudioChunk(audioData: Float32Array) {
  const message = {
    type: 'audio',
    timestamp: Date.now(),
    sequence: sequence++,
    data: arrayBufferToBase64(audioData.buffer),
    format: {
      sample_rate: 16000,
      channels: 1,
      encoding: 'pcm_f32le',
    },
  };

  ws.send(JSON.stringify(message));
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
```

### With Reconnection

```javascript
async function connectWithRetry(url: string, maxRetries: number = 5) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const ws = new WebSocket(url);
      await new Promise((resolve, reject) => {
        ws.onopen = resolve;
        ws.onerror = reject;
      });
      return ws;
    } catch (error) {
      const delay = Math.pow(2, attempt) * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  throw new Error('Failed to connect after ' + maxRetries + ' attempts');
}

const ws = await connectWithRetry(
  'ws://localhost:8000/ws/vad?client_id=web-client-v1&session_id=550e8400-e29b-41d4-a716-446655440000'
);
```

## References

- [WebSocket RFC 6455](https://www.rfc-editor.org/rfc/rfc6455)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Silero VAD](https://github.com/snakers4/silero-vad)

## Changelog

### Version 1.0.0 (2026-04-16)
- Initial version
- Defined WebSocket connection protocol
- Defined message types
- Defined audio streaming format
- Defined fallback detection logic
- Defined reconnection strategy
