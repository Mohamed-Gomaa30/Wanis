# Technology Context

## Overview

This document provides the AI agent with context about the new technologies being used in the Wanis project, specifically focusing on client-side VAD implementation using @ricky0123/vad library, WebAssembly performance characteristics, and browser compatibility.

## @ricky0123/vad Library

### Library Overview

The @ricky0123/vad library is a JavaScript implementation of Voice Activity Detection (VAD) that runs entirely in the browser using WebAssembly. It provides real-time speech detection without requiring server-side processing.

### Key Features

- **Client-Side Processing**: All VAD processing happens in the browser
- **Real-Time Detection**: Low-latency speech detection (<50ms)
- **WebAssembly-Based**: High performance using WebAssembly
- **Multiple Models**: Supports Silero VAD and WebRTC VAD models
- **Configurable Thresholds**: Adjustable speech probability thresholds
- **Event-Driven**: Emits events for speech start, speech end, and errors
- **Performance Monitoring**: Built-in metrics collection

### Capabilities

#### Speech Detection

- **Accuracy**: >95% true positive rate for speech detection
- **False Positive Rate**: <5% for silence detection
- **Latency**: <50ms from speech start to detection
- **Adaptive Thresholds**: Configurable probability thresholds (0.0-1.0)

#### Audio Processing

- **Sample Rates**: Supports 8kHz, 16kHz, 22.05kHz, 44.1kHz, 48kHz
- **Channels**: Mono and stereo support
- **Frame Sizes**: Configurable frame sizes (default: 512 samples)
- **Formats**: PCM 16-bit and 32-bit float

#### Performance

- **Memory Usage**: <50MB steady state
- **CPU Usage**: <5% during processing
- **Processing Time**: <10ms per frame
- **Model Size**: ~20MB for Silero VAD model

### Limitations

#### Browser Support

- **Required**: WebAssembly support
- **Minimum Versions**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Unsupported**: Internet Explorer, older browsers

#### Performance Constraints

- **Memory**: Requires <70MB peak memory
- **CPU**: Requires <10% CPU usage
- **Latency**: Requires <20ms per frame processing time

#### Model Limitations

- **Language**: Optimized for English, supports other languages with reduced accuracy
- **Noise**: Performance degrades in noisy environments
- **Multiple Speakers**: Designed for single-speaker scenarios

### Configuration Options

#### VAD Parameters

```typescript
interface VADConfig {
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
}
```

#### Default Configuration

```typescript
const DEFAULT_VAD_CONFIG = {
  sampleRate: 16000,
  frameSize: 512,
  model: 'silero',
  threshold: 0.5,
  minSpeechFrames: 10,
  minSilenceFrames: 20,
  preSpeechPad: 5,
  redemptionFrames: 8,
};
```

### Event Interface

#### Speech Start Event

Triggered when speech is detected.

```typescript
onSpeechStart: (audio: Float32Array) => void
```

**Parameters**:
- `audio`: Audio data from pre-speech pad frames

**Use Cases**:
- Start recording audio
- Update UI to show speech detected
- Begin STT processing

#### Speech End Event

Triggered when speech ends.

```typescript
onSpeechEnd: (audio: Float32Array) => void
```

**Parameters**:
- `audio`: Complete audio segment from speech start to end

**Use Cases**:
- Send audio to STT service
- Update UI to show speech ended
- Clear recording buffer

#### Error Event

Triggered when an error occurs.

```typescript
onError: (error: VADError) => void
```

**Parameters**:
- `error`: Error object with type and message

**Error Types**:
- `microphone_access`: Microphone access denied
- `wasm_not_supported`: WebAssembly not supported
- `model_load_failed`: Model loading failed
- `audio_context_error`: Audio context error
- `processing_error`: Processing error
- `invalid_frame`: Invalid frame size

### Performance Monitoring

#### Metrics Collection

Metrics are collected automatically when enabled.

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

#### Performance Targets

- **Memory**: <50MB steady state, <70MB peak
- **CPU**: <5% during processing, <10% peak
- **Latency**: <10ms per frame, <50ms speech detection
- **Accuracy**: >95% speech detection, <5% false positive rate

## WebAssembly Performance

### WebAssembly Overview

WebAssembly (Wasm) is a binary instruction format for a stack-based virtual machine that enables high-performance applications on web pages.

### Performance Characteristics

#### Memory Usage

- **Initial Load**: <30MB for model and runtime
- **Steady State**: <50MB during processing
- **Peak Usage**: <70MB during model loading
- **Memory Growth**: Linear with audio buffer size

#### CPU Usage

- **Idle**: <1% when not processing
- **Processing**: <5% during frame processing
- **Peak**: <10% during model initialization
- **Scaling**: Linear with frame rate

#### Latency

- **Model Loading**: <500ms for initial load
- **Frame Processing**: <10ms per frame
- **Speech Detection**: <50ms from speech start
- **Speech End Detection**: <100ms from speech end

#### Throughput

- **Frames per Second**: 100+ frames per second
- **Real-Time Factor**: 0.1-0.2 (faster than real-time)
- **Concurrent Streams**: 1 stream per WebAssembly instance

### Optimization Strategies

#### Memory Optimization

- **Buffer Pooling**: Reuse audio buffers
- **Frame Batching**: Process multiple frames together
- **Model Pruning**: Use smaller model variants
- **Memory Cleanup**: Explicitly release unused memory

#### CPU Optimization

- **Frame Skipping**: Skip frames if CPU is high
- **Adaptive Quality**: Reduce quality if CPU is high
- **Worker Threads**: Offload processing to workers
- **SIMD Operations**: Use SIMD when available

#### Latency Optimization

- **Preloading**: Load model before use
- **Warm-up**: Process dummy frames before use
- **Buffer Size**: Optimize buffer size for latency
- **Priority**: Use high-priority scheduling

### Browser Support

#### Supported Browsers

- **Chrome**: 90+ (full WebAssembly support)
- **Firefox**: 88+ (full WebAssembly support)
- **Safari**: 14+ (full WebAssembly support)
- **Edge**: 90+ (full WebAssembly support)

#### Unsupported Browsers

- **Internet Explorer**: No WebAssembly support
- **Older Chrome**: <90 (limited WebAssembly support)
- **Older Firefox**: <88 (limited WebAssembly support)
- **Older Safari**: <14 (limited WebAssembly support)

#### Feature Detection

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

### Fallback Strategies

#### Browser Compatibility Fallback

**Detection**:
- Check WebAssembly support
- Check WebAssembly instantiation
- Check model loading capability

**Fallback Action**:
- Switch to WebSocket mode
- Use server-side VAD
- Maintain same interface

#### Performance Fallback

**Detection**:
- Monitor memory usage
- Monitor CPU usage
- Monitor processing time

**Fallback Action**:
- Show performance warning
- Offer fallback option
- Switch to WebSocket mode if accepted

#### Error Fallback

**Detection**:
- Monitor error rate
- Monitor error types
- Monitor error frequency

**Fallback Action**:
- Log error details
- Attempt recovery
- Switch to WebSocket mode if unrecoverable

## Browser Compatibility

### Compatibility Matrix

| Browser | Version | WebAssembly | AudioContext | MediaStream | Status |
|---------|---------|-------------|--------------|-------------|--------|
| Chrome | 90+ | ✅ | ✅ | ✅ | Fully Supported |
| Chrome | 80-89 | ⚠️ | ✅ | ✅ | Partial Support |
| Chrome | <80 | ❌ | ✅ | ✅ | Not Supported |
| Firefox | 88+ | ✅ | ✅ | ✅ | Fully Supported |
| Firefox | 78-87 | ⚠️ | ✅ | ✅ | Partial Support |
| Firefox | <78 | ❌ | ✅ | ✅ | Not Supported |
| Safari | 14+ | ✅ | ✅ | ✅ | Fully Supported |
| Safari | 13-13.1 | ⚠️ | ✅ | ✅ | Partial Support |
| Safari | <13 | ❌ | ✅ | ✅ | Not Supported |
| Edge | 90+ | ✅ | ✅ | ✅ | Fully Supported |
| Edge | 80-89 | ⚠️ | ✅ | ✅ | Partial Support |
| Edge | <80 | ❌ | ✅ | ✅ | Not Supported |
| IE | Any | ❌ | ⚠️ | ⚠️ | Not Supported |

### Feature Support

#### WebAssembly

- **Chrome 90+**: Full support
- **Firefox 88+**: Full support
- **Safari 14+**: Full support
- **Edge 90+**: Full support

#### AudioContext

- **Chrome 43+**: Full support
- **Firefox 42+**: Full support
- **Safari 9+**: Full support
- **Edge 12+**: Full support

#### MediaStream

- **Chrome 51+**: Full support
- **Firefox 48+**: Full support
- **Safari 11+**: Full support
- **Edge 12+**: Full support

### Browser-Specific Considerations

#### Chrome

- **Performance**: Excellent WebAssembly performance
- **Memory**: Efficient memory management
- **Audio**: Good audio quality
- **Recommendation**: Primary browser for development

#### Firefox

- **Performance**: Good WebAssembly performance
- **Memory**: Higher memory usage than Chrome
- **Audio**: Good audio quality
- **Recommendation**: Good alternative to Chrome

#### Safari

- **Performance**: Moderate WebAssembly performance
- **Memory**: Higher memory usage
- **Audio**: Good audio quality
- **Recommendation**: Use for iOS testing

#### Edge

- **Performance**: Good WebAssembly performance (Chromium-based)
- **Memory**: Efficient memory management
- **Audio**: Good audio quality
- **Recommendation**: Good alternative to Chrome

### Mobile Browser Support

#### iOS Safari

- **Version**: 14+
- **WebAssembly**: Supported
- **Performance**: Moderate
- **Recommendation**: Test thoroughly on iOS

#### Android Chrome

- **Version**: 90+
- **WebAssembly**: Supported
- **Performance**: Good
- **Recommendation**: Good mobile experience

## Best Practices

### Initialization

```typescript
// Good: Initialize with configuration
const vad = new VAD({
  sampleRate: 16000,
  threshold: 0.5,
  onSpeechStart: (audio) => {
    console.log('Speech started');
  },
  onSpeechEnd: (audio) => {
    console.log('Speech ended');
    sendToSTT(audio);
  },
  onError: (error) => {
    console.error('VAD error:', error);
    fallbackToWebSocket();
  },
});

await vad.start();
```

### Error Handling

```typescript
// Good: Handle all error types
const vad = new VAD({
  onError: (error) => {
    switch (error.type) {
      case 'microphone_access':
        showMicrophoneError();
        break;
      case 'wasm_not_supported':
        fallbackToWebSocket();
        break;
      case 'model_load_failed':
        retryModelLoad();
        break;
      default:
        logError(error);
    }
  },
});
```

### Performance Monitoring

```typescript
// Good: Monitor performance
const vad = new VAD({
  enableMetrics: true,
  onMetrics: (metrics) => {
    if (metrics.cpuUsage > 5) {
      console.warn('High CPU usage');
    }
    if (metrics.memoryUsage > 50) {
      console.warn('High memory usage');
    }
  },
});
```

### Fallback Detection

```typescript
// Good: Detect and handle fallback
function shouldFallback(metrics: VADMetrics): boolean {
  return (
    metrics.memoryUsage > 70 ||
    metrics.cpuUsage > 10 ||
    metrics.processingTime > 20
  );
}

const vad = new VAD({
  enableMetrics: true,
  onMetrics: (metrics) => {
    if (shouldFallback(metrics)) {
      console.warn('Performance degraded, falling back');
      fallbackToWebSocket();
    }
  },
});
```

## Common Issues and Solutions

### Issue 1: WebAssembly Not Supported

**Symptoms**:
- Error: "WebAssembly not supported"
- VAD fails to initialize

**Solution**:
- Check browser version
- Update browser to latest version
- Fallback to WebSocket mode

### Issue 2: High Memory Usage

**Symptoms**:
- Memory usage >70MB
- Browser becomes slow

**Solution**:
- Reduce buffer size
- Clear audio buffers
- Restart VAD instance
- Fallback to WebSocket mode

### Issue 3: High CPU Usage

**Symptoms**:
- CPU usage >10%
- Browser becomes unresponsive

**Solution**:
- Reduce frame rate
- Skip frames if CPU is high
- Use smaller model
- Fallback to WebSocket mode

### Issue 4: Slow Detection

**Symptoms**:
- Speech detection latency >100ms
- Speech end detection latency >200ms

**Solution**:
- Reduce frame size
- Optimize buffer size
- Use faster model
- Check system performance

### Issue 5: Poor Accuracy

**Symptoms**:
- High false positive rate
- High false negative rate

**Solution**:
- Adjust threshold
- Improve audio quality
- Reduce background noise
- Use better microphone

## References

- [@ricky0123/vad Documentation](https://github.com/ricky0123/vad)
- [WebAssembly Documentation](https://webassembly.org/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [Silero VAD](https://github.com/snakers4/silero-vad)

## Agent Knowledge Base

### Key Concepts

1. **Client-Side VAD**: VAD processing happens in the browser using WebAssembly
2. **WebAssembly**: Binary instruction format for high-performance web applications
3. **Event-Driven**: VAD emits events for speech start, speech end, and errors
4. **Performance Monitoring**: Built-in metrics collection for memory, CPU, and latency
5. **Fallback Strategy**: WebSocket fallback for unsupported browsers or poor performance

### Common Questions

**Q: What is @ricky0123/vad?**
A: A JavaScript library for client-side voice activity detection using WebAssembly.

**Q: What browsers support @ricky0123/vad?**
A: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+.

**Q: What is the performance of @ricky0123/vad?**
A: <50MB memory, <5% CPU, <50ms latency.

**Q: What is the fallback strategy?**
A: WebSocket mode for unsupported browsers or poor performance.

**Q: How do I configure @ricky0123/vad?**
A: Use VADConfig object with sample rate, threshold, and event callbacks.

### Technical Guidance

When providing technical guidance about @ricky0123/vad:

1. **Browser Compatibility**: Always check browser version and WebAssembly support
2. **Performance**: Monitor memory, CPU, and latency metrics
3. **Error Handling**: Handle all error types with appropriate fallback
4. **Configuration**: Use appropriate thresholds and frame sizes for the use case
5. **Testing**: Test on target browsers and devices

### Architecture Guidance

When providing architectural guidance:

1. **Client-Side First**: Use client-side VAD when possible for better performance
2. **Fallback Strategy**: Always have WebSocket fallback for unsupported browsers
3. **Performance Monitoring**: Monitor metrics and fallback if performance degrades
4. **Error Recovery**: Implement robust error handling and recovery
5. **Testing**: Test on multiple browsers and devices

## Changelog

### Version 1.0.0 (2026-04-16)
- Initial version
- Documented @ricky0123/vad library capabilities
- Documented WebAssembly performance characteristics
- Documented browser compatibility matrix
- Documented fallback strategies
- Documented best practices
