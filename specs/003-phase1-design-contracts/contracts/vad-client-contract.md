# Client-Side VAD Contract

## Overview

This contract defines the interface between the frontend JavaScript application and the @ricky0123/vad library for client-side voice activity detection.

## Version

- **Version**: 1.0.0
- **Date**: 2026-04-16
- **Status**: Draft

## Interface Definition

### VAD Initialization

#### Constructor Parameters

```typescript
interface VADInitOptions {
  // Audio configuration
  sampleRate: number;           // Audio sample rate in Hz (default: 16000)
  frameSize: number;            // Frame size in samples (default: 512)

  // VAD model configuration
  model: 'silero' | 'webrtc';   // VAD model to use (default: 'silero')
  threshold: number;            // Speech probability threshold (0.0-1.0, default: 0.5)

  // Performance configuration
  minSpeechFrames: number;      // Minimum frames to consider speech (default: 10)
  minSilenceFrames: number;     // Minimum frames to consider silence (default: 20)
  preSpeechPad: number;         // Frames to include before speech start (default: 5)
  redemptionFrames: number;     // Frames to wait before ending speech (default: 8)

  // Event callbacks
  onSpeechStart: (audio: Float32Array) => void;
  onSpeechEnd: (audio: Float32Array) => void;
  onError: (error: VADError) => void;

  // Performance monitoring
  enableMetrics: boolean;       // Enable performance metrics (default: false)
  onMetrics: (metrics: VADMetrics) => void;
}
```

#### Default Values

```typescript
const DEFAULT_VAD_OPTIONS: VADInitOptions = {
  sampleRate: 16000,
  frameSize: 512,
  model: 'silero',
  threshold: 0.5,
  minSpeechFrames: 10,
  minSilenceFrames: 20,
  preSpeechPad: 5,
  redemptionFrames: 8,
  onSpeechStart: () => {},
  onSpeechEnd: () => {},
  onError: () => {},
  enableMetrics: false,
  onMetrics: () => {},
};
```

### VAD Instance Methods

#### `start()`

Starts the VAD processing.

```typescript
start(): Promise<void>
```

**Returns**: Promise that resolves when VAD is started

**Throws**: `VADError` if VAD cannot be started

**Error Cases**:
- Microphone access denied
- WebAssembly not supported
- Model loading failed
- Audio context creation failed

#### `stop()`

Stops the VAD processing.

```typescript
stop(): Promise<void>
```

**Returns**: Promise that resolves when VAD is stopped

**Throws**: `VADError` if VAD cannot be stopped

**Error Cases**:
- VAD not started
- Audio context close failed

#### `processFrame(audio: Float32Array): VADResult`

Processes a single audio frame.

```typescript
processFrame(audio: Float32Array): VADResult
```

**Parameters**:
- `audio`: Audio frame as Float32Array (length must match frameSize)

**Returns**: VAD result with speech probability and state

**Throws**: `VADError` if frame processing fails

**Error Cases**:
- Invalid frame size
- VAD not started
- Processing error

#### `reset()`

Resets the VAD state.

```typescript
reset(): void
```

**Error Cases**: None

#### `getMetrics(): VADMetrics`

Gets current performance metrics.

```typescript
getMetrics(): VADMetrics
```

**Returns**: Current performance metrics

**Error Cases**: None

### Event Callbacks

#### `onSpeechStart(audio: Float32Array)`

Called when speech is detected.

**Parameters**:
- `audio`: Audio data from pre-speech pad frames

**Trigger Conditions**:
- Speech probability exceeds threshold for minSpeechFrames
- Speech state transitions from silence to speech

**Use Cases**:
- Start recording audio
- Update UI to show speech detected
- Begin STT processing

#### `onSpeechEnd(audio: Float32Array)`

Called when speech ends.

**Parameters**:
- `audio`: Complete audio segment from speech start to end

**Trigger Conditions**:
- Speech probability falls below threshold for minSilenceFrames
- Speech state transitions from speech to silence

**Use Cases**:
- Send audio to STT service
- Update UI to show speech ended
- Clear recording buffer

#### `onError(error: VADError)`

Called when an error occurs.

**Parameters**:
- `error`: Error object with type and message

**Trigger Conditions**:
- Microphone access denied
- WebAssembly not supported
- Model loading failed
- Audio context error
- Processing error

**Use Cases**:
- Show error message to user
- Log error for debugging
- Trigger fallback to WebSocket

#### `onMetrics(metrics: VADMetrics)`

Called periodically with performance metrics (if enabled).

**Parameters**:
- `metrics`: Performance metrics object

**Trigger Conditions**:
- Every 1 second (if enableMetrics is true)

**Use Cases**:
- Monitor performance
- Detect performance degradation
- Optimize configuration

### Data Types

#### VADResult

```typescript
interface VADResult {
  probability: number;    // Speech probability (0.0-1.0)
  isSpeech: boolean;      // Whether speech is detected
  timestamp: number;     // Frame timestamp in milliseconds
}
```

#### VADError

```typescript
interface VADError {
  type: 'microphone_access' | 'wasm_not_supported' | 'model_load_failed' |
        'audio_context_error' | 'processing_error' | 'invalid_frame';
  message: string;        // Human-readable error message
  code: number;           // Error code for programmatic handling
  details?: any;         // Additional error details
}
```

#### VADMetrics

```typescript
interface VADMetrics {
  framesProcessed: number;        // Total frames processed
  speechFrames: number;          // Frames with speech detected
  silenceFrames: number;         // Frames with silence detected
  averageProbability: number;    // Average speech probability
  processingTime: number;        // Average processing time per frame (ms)
  memoryUsage: number;            // Estimated memory usage (MB)
  cpuUsage: number;               // Estimated CPU usage (%)
  uptime: number;                 // VAD uptime in milliseconds
}
```

### Audio Stream Configuration

#### Audio Input Format

```typescript
interface AudioInputConfig {
  sampleRate: number;       // Sample rate in Hz (16000)
  channels: number;         // Number of channels (1)
  format: 'float32';        // Audio format (float32)
  frameSize: number;        // Frame size in samples (512)
}
```

#### Audio Buffer Requirements

```typescript
interface AudioBufferConfig {
  bufferSize: number;        // Buffer size in samples (4096)
  bufferCount: number;      // Number of buffers (3)
  overflowStrategy: 'drop' | 'block' | 'expand';  // Overflow handling
}
```

### Performance Requirements

#### Latency

- **Frame Processing**: <10ms per frame
- **Speech Detection**: <50ms from speech start
- **Speech End Detection**: <100ms from speech end

#### Memory Usage

- **Initial Load**: <30MB
- **Steady State**: <50MB
- **Peak Usage**: <70MB

#### CPU Usage

- **Idle**: <1%
- **Processing**: <5%
- **Peak**: <10%

#### Accuracy

- **Speech Detection**: >95% true positive rate
- **Silence Detection**: >90% true negative rate
- **False Positive Rate**: <5%

### Error Handling

#### Error Recovery Strategies

1. **Microphone Access Denied**
   - Show user-friendly error message
   - Request microphone access again
   - Fallback to WebSocket mode

2. **WebAssembly Not Supported**
   - Detect browser support
   - Show compatibility message
   - Fallback to WebSocket mode

3. **Model Loading Failed**
   - Retry model loading (max 3 times)
   - Show loading progress
   - Fallback to WebSocket mode

4. **Audio Context Error**
   - Recreate audio context
   - Resume audio context
   - Fallback to WebSocket mode

5. **Processing Error**
   - Log error details
   - Skip problematic frame
   - Continue processing

6. **Invalid Frame**
   - Validate frame size
   - Skip invalid frame
   - Log warning

#### Error Codes

```typescript
enum VADErrorCode {
  MICROPHONE_ACCESS_DENIED = 1001,
  WASM_NOT_SUPPORTED = 1002,
  MODEL_LOAD_FAILED = 1003,
  AUDIO_CONTEXT_ERROR = 1004,
  PROCESSING_ERROR = 1005,
  INVALID_FRAME = 1006,
}
```

### Fallback Scenarios

#### Browser Compatibility Fallback

**Detection**:
```typescript
function detectWASMSupport(): boolean {
  try {
    return typeof WebAssembly === 'object' &&
           typeof WebAssembly.instantiate === 'function';
  } catch (e) {
    return false;
  }
}
```

**Fallback Trigger**:
- WebAssembly not supported
- Model loading fails after 3 retries
- Performance metrics exceed thresholds

**Fallback Action**:
- Switch to WebSocket mode
- Use server-side VAD
- Maintain same interface

#### Performance Fallback

**Detection**:
```typescript
function shouldFallback(metrics: VADMetrics): boolean {
  return metrics.memoryUsage > 70 ||
         metrics.cpuUsage > 10 ||
         metrics.processingTime > 20;
}
```

**Fallback Trigger**:
- Memory usage >70MB
- CPU usage >10%
- Processing time >20ms per frame

**Fallback Action**:
- Show performance warning
- Offer fallback option
- Switch to WebSocket mode if accepted

### Performance Monitoring

#### Metrics Collection

Metrics are collected automatically when `enableMetrics` is true.

**Collection Frequency**: Every 1 second

**Metrics Included**:
- Frames processed
- Speech/silence frame counts
- Average probability
- Processing time
- Memory usage
- CPU usage
- Uptime

#### Metrics Reporting

Metrics are reported through the `onMetrics` callback.

**Report Format**:
```typescript
{
  framesProcessed: 1000,
  speechFrames: 450,
  silenceFrames: 550,
  averageProbability: 0.52,
  processingTime: 5.2,
  memoryUsage: 35.5,
  cpuUsage: 3.2,
  uptime: 60000
}
```

### Browser Compatibility

#### Supported Browsers

- **Chrome**: 90+ (WebAssembly support)
- **Firefox**: 88+ (WebAssembly support)
- **Safari**: 14+ (WebAssembly support)
- **Edge**: 90+ (WebAssembly support)

#### Unsupported Browsers

- **Internet Explorer**: No WebAssembly support
- **Older Chrome**: <90 (limited WebAssembly support)
- **Older Firefox**: <88 (limited WebAssembly support)
- **Older Safari**: <14 (limited WebAssembly support)

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
```

### Security Considerations

#### Microphone Access

- Always request microphone access explicitly
- Show clear permission request message
- Handle permission denial gracefully
- Never access microphone without user consent

#### Audio Data

- Audio data stays in browser memory
- No audio data is sent to third parties
- Audio data is only sent to configured STT endpoint
- Audio data is cleared after processing

#### WebAssembly

- WebAssembly module is loaded from trusted source
- WebAssembly module is validated before execution
- WebAssembly module runs in sandboxed environment

### Testing Requirements

#### Unit Tests

- Test VAD initialization with various options
- Test frame processing with valid and invalid data
- Test event callback triggering
- Test error handling scenarios
- Test metrics collection

#### Integration Tests

- Test with real microphone input
- Test speech detection accuracy
- Test performance under load
- Test fallback scenarios
- Test browser compatibility

#### Performance Tests

- Measure memory usage
- Measure CPU usage
- Measure processing latency
- Measure detection accuracy
- Compare with baseline

### Implementation Notes

#### Initialization Sequence

1. Create VAD instance with options
2. Load WebAssembly model
3. Create audio context
4. Request microphone access
5. Start audio processing
6. Begin frame processing

#### Processing Loop

1. Read audio frame from microphone
2. Process frame through VAD
3. Update speech state
4. Trigger events if state changes
5. Collect metrics if enabled
6. Repeat until stopped

#### Cleanup Sequence

1. Stop audio processing
2. Close audio context
3. Release microphone access
4. Clear audio buffers
5. Unload WebAssembly model

## Examples

### Basic Usage

```typescript
import { VAD } from '@ricky0123/vad';

const vad = new VAD({
  sampleRate: 16000,
  threshold: 0.5,
  onSpeechStart: (audio) => {
    console.log('Speech started', audio.length);
  },
  onSpeechEnd: (audio) => {
    console.log('Speech ended', audio.length);
    // Send audio to STT service
    sendToSTT(audio);
  },
  onError: (error) => {
    console.error('VAD error:', error);
  },
});

await vad.start();
```

### With Performance Monitoring

```typescript
const vad = new VAD({
  sampleRate: 16000,
  threshold: 0.5,
  enableMetrics: true,
  onMetrics: (metrics) => {
    console.log('Metrics:', metrics);
    if (metrics.cpuUsage > 5) {
      console.warn('High CPU usage');
    }
  },
  onSpeechStart: (audio) => {
    console.log('Speech started');
  },
  onSpeechEnd: (audio) => {
    console.log('Speech ended');
    sendToSTT(audio);
  },
  onError: (error) => {
    console.error('VAD error:', error);
  },
});

await vad.start();
```

### With Fallback Detection

```typescript
const vad = new VAD({
  sampleRate: 16000,
  threshold: 0.5,
  enableMetrics: true,
  onMetrics: (metrics) => {
    if (shouldFallback(metrics)) {
      console.warn('Performance degraded, falling back');
      fallbackToWebSocket();
    }
  },
  onSpeechStart: (audio) => {
    console.log('Speech started');
  },
  onSpeechEnd: (audio) => {
    console.log('Speech ended');
    sendToSTT(audio);
  },
  onError: (error) => {
    console.error('VAD error:', error);
    if (error.type === 'wasm_not_supported') {
      fallbackToWebSocket();
    }
  },
});

await vad.start();
```

## References

- [@ricky0123/vad Documentation](https://github.com/ricky0123/vad)
- [WebAssembly Documentation](https://webassembly.org/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

## Changelog

### Version 1.0.0 (2026-04-16)
- Initial version
- Defined VAD initialization parameters
- Defined event callbacks
- Defined performance requirements
- Defined error handling
- Defined fallback scenarios
