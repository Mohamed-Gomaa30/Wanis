# Data Model for Server‑Side Adaptation

## Entities

### AudioChunk
- **sequence** (int): Order of the chunk within an utterance.
- **timestamp** (int): Unix epoch ms when captured.
- **data** (base64 string): PCM audio payload (16‑bit, 16 kHz, mono).
- **audio_format** (object, optional): `sample_rate`, `channels`, `encoding`.

### Utterance
- **chunks** (list of AudioChunk): Ordered collection forming a speech segment.
- **start_time** (int): Timestamp of first chunk.
- **end_time** (int): Timestamp of last chunk.
- **duration_ms** (int): Total utterance length.

### VADResult
- **start_timestamp** (int): Detected speech start.
- **end_timestamp** (int): Detected speech end.
- **confidence** (float 0‑1): Confidence score.
- **mode** (enum): `client` or `server`.

### Metrics
- **request_id** (UUID): Request identifier.
- **processing_time_ms** (int): End‑to‑end latency.
- **vad_mode** (enum): Same as VADResult.mode.
- **error_count** (int): Number of errors for the request.

## Relationships
- An Utterance aggregates multiple AudioChunk records.
- Each Utterance yields one VADResult.
- Metrics are linked one‑to‑one with a request_id.

## Validation Rules
- `sequence` must be positive and strictly increasing.
- `data` must decode to PCM matching the declared format.
- `confidence` must be ≥ 0.5 for successful detection.
- `processing_time_ms` must satisfy ≤ 500 ms latency bound.
