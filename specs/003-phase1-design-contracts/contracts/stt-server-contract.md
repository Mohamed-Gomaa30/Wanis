# Server-Side STT Contract

## Overview

This contract defines the HTTP POST interface for Speech-to-Text (STT) processing on the server side. The server receives audio data from the client and returns transcriptions using the NeMo STT model (EgypTalk-ASR-v2).

## Version

- **Version**: 1.0.0
- **Date**: 2026-04-16
- **Status**: Final

## Interface Definition

### Endpoint

#### URL

```
POST /api/stt/transcribe
```

#### Base URL

- **Development**: `http://localhost:8000/api/stt/transcribe`
- **Production**: `https://api.wanis.ai/api/stt/transcribe`

### Request Format

#### Headers

```http
Content-Type: audio/wav
X-Request-ID: <uuid>
X-Client-ID: <client_id>
X-Session-ID: <session_id>
X-Audio-Format: <format>
X-Audio-Sample-Rate: <sample_rate>
X-Audio-Channels: <channels>
X-Audio-Duration: <duration_ms>
Authorization: Bearer <token>
```

**Header Descriptions**:

- `Content-Type`: Audio format (required)
  - `audio/wav`: WAV format
  - `audio/webm`: WebM format
  - `audio/ogg`: OGG format
  - `audio/raw`: Raw PCM data

- `X-Request-ID`: Unique request identifier (required)
  - Format: UUID v4
  - Example: `550e8400-e29b-41d4-a716-446655440000`

- `X-Client-ID`: Client identifier (required)
  - Format: String
  - Example: `web-client-v1`

- `X-Session-ID`: Session identifier (required)
  - Format: UUID v4
  - Example: `550e8400-e29b-41d4-a716-446655440000`

- `X-Audio-Format`: Audio format specification (optional)
  - Format: String
  - Values: `pcm_s16le`, `pcm_f32le`, `wav`, `webm`, `ogg`
  - Default: `pcm_s16le`

- `X-Audio-Sample-Rate`: Audio sample rate in Hz (optional)
  - Format: Integer
  - Values: `8000`, `16000`, `22050`, `44100`, `48000`
  - Default: `16000`

- `X-Audio-Channels`: Number of audio channels (optional)
  - Format: Integer
  - Values: `1`, `2`
  - Default: `1`

- `X-Audio-Duration`: Audio duration in milliseconds (optional)
  - Format: Integer
  - Example: `5000`

- `Authorization`: Bearer token for authentication (optional)
  - Format: `Bearer <token>`
  - Required for production

#### Body

Binary audio data in the format specified by `Content-Type` header.

**Audio Requirements**:

- **Sample Rate**: 16000 Hz (recommended)
- **Channels**: 1 (mono)
- **Bit Depth**: 16-bit (PCM) or 32-bit (Float)
- **Duration**: 100ms - 30s
- **File Size**: <10MB

**Supported Formats**:

1. **WAV** (`audio/wav`)
   - Standard WAV format
   - PCM encoding
   - 16-bit or 32-bit

2. **WebM** (`audio/webm`)
   - Opus encoding
   - Variable bitrate
   - Web-optimized

3. **OGG** (`audio/ogg`)
   - Opus or Vorbis encoding
   - Variable bitrate
   - Open format

4. **Raw PCM** (`audio/raw`)
   - Raw PCM data
   - Little-endian
   - 16-bit or 32-bit

#### Request Example

```http
POST /api/stt/transcribe HTTP/1.1
Host: localhost:8000
Content-Type: audio/wav
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Client-ID: web-client-v1
X-Session-ID: 660e8400-e29b-41d4-a716-446655440001
X-Audio-Format: wav
X-Audio-Sample-Rate: 16000
X-Audio-Channels: 1
X-Audio-Duration: 5000
Content-Length: 160000

<binary audio data>
```

### Response Format

#### Success Response

**Status Code**: `200 OK`

**Headers**:

```http
Content-Type: application/json
X-Request-ID: <uuid>
X-Processing-Time: <ms>
```

**Body**:

```json
{
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcription": "مرحبا، كيف حالك؟",
  "confidence": 0.95,
  "language": "ar",
  "duration_ms": 5000,
  "segments": [
    {
      "text": "مرحبا",
      "start": 0,
      "end": 1200,
      "confidence": 0.96
    },
    {
      "text": "كيف حالك؟",
      "start": 1300,
      "end": 5000,
      "confidence": 0.94
    }
  ],
  "alternatives": [
    {
      "text": "مرحبا، كيف حالك؟",
      "confidence": 0.95
    },
    {
      "text": "مرحبا كيف حالك",
      "confidence": 0.92
    }
  ],
  "processing_time_ms": 250,
  "model": "EgypTalk-ASR-v2",
  "timestamp": "2026-04-16T10:30:00Z"
}
```

**Response Fields**:

- `success`: Boolean indicating success (required)
- `request_id`: Request identifier (required)
- `transcription`: Full transcription text (required)
- `confidence`: Overall confidence score (0.0-1.0) (required)
- `language`: Detected language code (required)
  - `ar`: Arabic
  - `en`: English
  - `ar-EG`: Egyptian Arabic
- `duration_ms`: Audio duration in milliseconds (required)
- `segments`: Array of transcription segments (optional)
  - `text`: Segment text
  - `start`: Start time in milliseconds
  - `end`: End time in milliseconds
  - `confidence`: Segment confidence score
- `alternatives`: Array of alternative transcriptions (optional)
  - `text`: Alternative transcription
  - `confidence`: Alternative confidence score
- `processing_time_ms`: Processing time in milliseconds (required)
- `model`: Model name used (required)
- `timestamp`: Response timestamp in ISO 8601 format (required)

#### Error Response

**Status Code**: `4xx` or `5xx`

**Headers**:

```http
Content-Type: application/json
X-Request-ID: <uuid>
```

**Body**:

```json
{
  "success": false,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": {
    "code": "INVALID_AUDIO_FORMAT",
    "message": "Unsupported audio format",
    "details": {
      "provided_format": "audio/mp3",
      "supported_formats": ["audio/wav", "audio/webm", "audio/ogg", "audio/raw"]
    }
  },
  "timestamp": "2026-04-16T10:30:00Z"
}
```

**Error Fields**:

- `success`: Boolean indicating failure (required)
- `request_id`: Request identifier (required)
- `error`: Error object (required)
  - `code`: Error code (required)
  - `message`: Human-readable error message (required)
  - `details`: Additional error details (optional)
- `timestamp`: Response timestamp in ISO 8601 format (required)

### Error Codes

#### Client Errors (4xx)

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_REQUEST` | 400 | Invalid request format or parameters |
| `INVALID_AUDIO_FORMAT` | 400 | Unsupported audio format |
| `INVALID_AUDIO_DATA` | 400 | Invalid or corrupted audio data |
| `AUDIO_TOO_SHORT` | 400 | Audio duration too short (<100ms) |
| `AUDIO_TOO_LONG` | 400 | Audio duration too long (>30s) |
| `AUDIO_TOO_LARGE` | 413 | Audio file too large (>10MB) |
| `MISSING_HEADER` | 400 | Required header missing |
| `INVALID_HEADER` | 400 | Invalid header value |
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |

#### Server Errors (5xx)

| Code | Status | Description |
|------|--------|-------------|
| `INTERNAL_ERROR` | 500 | Internal server error |
| `MODEL_LOAD_FAILED` | 500 | Failed to load STT model |
| `MODEL_INFERENCE_FAILED` | 500 | Model inference failed |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `TIMEOUT` | 504 | Request timeout |

### Rate Limiting

#### Rate Limits

- **Per Client**: 10 requests per minute
- **Per Session**: 30 requests per minute
- **Global**: 1000 requests per minute

#### Rate Limit Headers

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1713270000
```

**Header Descriptions**:

- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

#### Rate Limit Response

**Status Code**: `429 Too Many Requests`

**Body**:

```json
{
  "success": false,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 10,
      "window": "60s",
      "retry_after": 30
    }
  },
  "timestamp": "2026-04-16T10:30:00Z"
}
```

### Authentication

#### Authentication Methods

1. **Bearer Token** (Production)
   - Token-based authentication
   - Required for production endpoints
   - Token validation on each request

2. **No Authentication** (Development)
   - No authentication required
   - For local development only
   - Not recommended for production

#### Token Format

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Token Validation

- Token must be valid JWT
- Token must not be expired
- Token must have required scopes
- Token must be issued by trusted authority

### Performance Requirements

#### Latency

- **P50**: <500ms
- **P95**: <1000ms
- **P99**: <2000ms
- **Max**: 5000ms

#### Throughput

- **Concurrent Requests**: 10
- **Requests per Second**: 20
- **Requests per Minute**: 1000

#### Resource Usage

- **Memory per Request**: <100MB
- **CPU per Request**: <10%
- **GPU per Request**: <5%

### Retry Logic

#### Retry Strategy

- **Retryable Errors**: `500`, `502`, `503`, `504`
- **Non-Retryable Errors**: `400`, `401`, `403`, `404`, `413`, `429`

#### Retry Configuration

```typescript
interface RetryConfig {
  maxRetries: number;        // Maximum retry attempts (default: 3)
  initialDelay: number;      // Initial delay in ms (default: 1000)
  maxDelay: number;          // Maximum delay in ms (default: 10000)
  backoffFactor: number;     // Exponential backoff factor (default: 2)
  retryableErrors: number[]; // Retryable status codes
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffFactor: 2,
  retryableErrors: [500, 502, 503, 504],
};
```

#### Retry Algorithm

```typescript
async function transcribeWithRetry(
  audio: ArrayBuffer,
  config: RetryConfig = DEFAULT_RETRY_CONFIG
): Promise<STTResponse> {
  let lastError: Error;

  for (let attempt = 0; attempt < config.maxRetries; attempt++) {
    try {
      return await transcribe(audio);
    } catch (error) {
      lastError = error;

      if (!isRetryable(error)) {
        throw error;
      }

      const delay = Math.min(
        config.initialDelay * Math.pow(config.backoffFactor, attempt),
        config.maxDelay
      );

      await sleep(delay);
    }
  }

  throw lastError;
}
```

### Data Types

#### STTRequest

```typescript
interface STTRequest {
  headers: {
    'Content-Type': string;
    'X-Request-ID': string;
    'X-Client-ID': string;
    'X-Session-ID': string;
    'X-Audio-Format'?: string;
    'X-Audio-Sample-Rate'?: number;
    'X-Audio-Channels'?: number;
    'X-Audio-Duration'?: number;
    'Authorization'?: string;
  };
  body: ArrayBuffer;
}
```

#### STTResponse

```typescript
interface STTResponse {
  success: boolean;
  request_id: string;
  transcription: string;
  confidence: number;
  language: string;
  duration_ms: number;
  segments?: STTSegment[];
  alternatives?: STTAlternative[];
  processing_time_ms: number;
  model: string;
  timestamp: string;
}

interface STTSegment {
  text: string;
  start: number;
  end: number;
  confidence: number;
}

interface STTAlternative {
  text: string;
  confidence: number;
}
```

#### STTError

```typescript
interface STTError {
  success: false;
  request_id: string;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}
```

### Security Considerations

#### Data Privacy

- Audio data is processed in memory
- Audio data is not stored permanently
- Audio data is not shared with third parties
- Transcription results are not logged

#### Input Validation

- Validate audio format
- Validate audio duration
- Validate audio size
- Validate header values
- Sanitize all inputs

#### Rate Limiting

- Enforce rate limits per client
- Enforce rate limits per session
- Enforce global rate limits
- Return rate limit headers

#### Authentication

- Validate authentication tokens
- Check token expiration
- Verify token scopes
- Log authentication attempts

### Testing Requirements

#### Unit Tests

- Test request validation
- Test audio format conversion
- Test model inference
- Test error handling
- Test rate limiting

#### Integration Tests

- Test with real audio data
- Test with various audio formats
- Test with different languages
- Test error scenarios
- Test rate limiting

#### Performance Tests

- Measure latency (P50, P95, P99)
- Measure throughput
- Measure resource usage
- Test under load
- Compare with baseline

### Implementation Notes

#### Processing Pipeline

1. Receive request
2. Validate headers
3. Validate audio data
4. Convert audio format if needed
5. Resample audio if needed
6. Run STT model inference
7. Generate transcription
8. Calculate confidence scores
9. Format response
10. Send response

#### Audio Processing

- Convert audio to required format (PCM 16-bit, 16kHz, mono)
- Normalize audio levels
- Remove silence if needed
- Split into segments if needed

#### Model Inference

- Load model on startup
- Keep model in memory
- Batch requests if possible
- Use GPU acceleration if available

#### Error Handling

- Log all errors
- Return appropriate error codes
- Include error details
- Maintain error statistics

## Examples

### Basic Request

```javascript
const audioData = await fetchAudioFromMicrophone();

const response = await fetch('http://localhost:8000/api/stt/transcribe', {
  method: 'POST',
  headers: {
    'Content-Type': 'audio/wav',
    'X-Request-ID': generateUUID(),
    'X-Client-ID': 'web-client-v1',
    'X-Session-ID': getSessionID(),
    'X-Audio-Format': 'wav',
    'X-Audio-Sample-Rate': '16000',
    'X-Audio-Channels': '1',
    'X-Audio-Duration': '5000',
  },
  body: audioData,
});

const result = await response.json();
console.log('Transcription:', result.transcription);
console.log('Confidence:', result.confidence);
```

### With Retry Logic

```javascript
async function transcribeWithRetry(audioData: ArrayBuffer) {
  const maxRetries = 3;
  const initialDelay = 1000;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch('http://localhost:8000/api/stt/transcribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'audio/wav',
          'X-Request-ID': generateUUID(),
          'X-Client-ID': 'web-client-v1',
          'X-Session-ID': getSessionID(),
        },
        body: audioData,
      });

      if (response.ok) {
        return await response.json();
      }

      if (!isRetryable(response.status)) {
        throw new Error(`Non-retryable error: ${response.status}`);
      }

      const delay = initialDelay * Math.pow(2, attempt);
      await sleep(delay);
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
    }
  }
}
```

### With Authentication

```javascript
const token = getAuthToken();

const response = await fetch('https://api.wanis.ai/api/stt/transcribe', {
  method: 'POST',
  headers: {
    'Content-Type': 'audio/wav',
    'X-Request-ID': generateUUID(),
    'X-Client-ID': 'web-client-v1',
    'X-Session-ID': getSessionID(),
    'Authorization': `Bearer ${token}`,
  },
  body: audioData,
});

const result = await response.json();
console.log('Transcription:', result.transcription);
```

## References

- [NeMo ASR Documentation](https://docs.nvidia.com/deeplearning/nemo/user-guide/docs/stable/asr/intro.html)
- [EgypTalk-ASR-v2 Model](https://huggingface.co/NAMAA-Space/EgypTalk-ASR-v2)
- [HTTP/1.1 Specification](https://www.rfc-editor.org/rfc/rfc7231)
- [JWT Authentication](https://jwt.io/)

## Changelog

### Version 1.0.0 (2026-04-16)
- Initial version
- Defined HTTP POST interface
- Defined request/response formats
- Defined error handling
- Defined rate limiting
- Defined authentication
- Defined retry logic
