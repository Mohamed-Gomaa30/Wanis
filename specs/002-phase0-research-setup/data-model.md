# Data Model: Phase 0 - Research and Setup

## Overview

This data model defines the structure and relationships for research findings and development environment setup for client-side VAD implementation.

---

## Entities

### VAD Library Documentation

**Entity:** VADLibraryDocumentation

**Fields:**
- `library_name` (string) - Name of the VAD library (e.g., "@ricky0123/vad")
- `version` (string) - Version of the library (e.g., "0.0.14")
- `repository` (string) - GitHub repository URL
- `documentation_url` (string) - Documentation URL
- `license` (string) - License type (e.g., "MIT")
- `capabilities` (array) - List of VAD capabilities
- `configuration_options` (array) - List of configuration options
- `supported_formats` (array) - List of supported audio formats
- `supported_sample_rates` (array) - List of supported sample rates
- `api_methods` (array) - List of API methods
- `events` (array) - List of events
- `limitations` (array) - List of known limitations

**Relationships:**
- Has many `configuration_options`
- Has many `supported_formats`
- Has many `supported_sample_rates`
- Has many `api_methods`
- Has many `events`
- Has many `limitations`

### Browser Compatibility Matrix

**Entity:** BrowserCompatibilityMatrix

**Fields:**
- `browser_name` (string) - Name of the browser (e.g., "Chrome", "Firefox", "Safari", "Edge")
- `version` (string) - Browser version (e.g., "Current stable from last 6 months")
- `webassembly_support` (boolean) - Whether WebAssembly is supported
- `vad_support` (boolean) - Whether @ricky0123/vad is supported
- `vad_performance` (string) - VAD performance rating (e.g., "Excellent", "Good", "Fair", "Poor")
- `status` (string) - Compatibility status (e.g., "✅ Tested", "⚠️ Issues", "❌ Not Supported")
- `notes` (string) - Browser-specific notes or issues

**Relationships:**
- Has many `browser_compatibility_entries`

### Performance Analysis Report

**Entity:** PerformanceAnalysisReport

**Fields:**
- `memory_usage` (object) - Memory usage measurements
  - `target_mb` (number) - Target memory usage in MB
  - `measured_mb` (object) - Measured memory usage by browser
    - `chrome` (number) - Chrome memory usage in MB
    - `firefox` (number) - Firefox memory usage in MB
    - `safari` (number) - Safari memory usage in MB
    - `edge` (number) - Edge memory usage in MB
- `cpu_usage` (object) - CPU usage measurements
  - `target_percent` (number) - Target CPU usage percentage
  - `measured_percent` (object) - Measured CPU usage by browser
    - `chrome` (number) - Chrome CPU usage percentage
    - `firefox` (number) - Firefox CPU usage percentage
    - `safari` (number) - Safari CPU usage percentage
    - `edge` (number) - Edge CPU usage percentage
- `latency` (object) - Latency measurements
  - `speech_start_ms` (number) - Speech start detection latency in ms
  - `speech_end_ms` (number) - Speech end detection latency in ms
  - `total_vad_latency_ms` (number) - Total VAD latency in ms
- `bottlenecks` (array) - List of performance bottlenecks
- `optimization_opportunities` (array) - List of optimization opportunities

**Relationships:**
- Has many `bottlenecks`
- Has many `optimization_opportunities`

### Development Environment Configuration

**Entity:** DevelopmentEnvironmentConfiguration

**Fields:**
- `package_name` (string) - Name of the npm package
- `version` (string) - Version of the package
- `description` (string) - Description of the package
- `main` (string) - Main entry point
- `scripts` (object) - Build and development scripts
- `dependencies` (object) - Required dependencies
- `dev_dependencies` (object) - Development dependencies
- `engines` (object) - Supported Node.js and npm versions

**Relationships:**
- Has many `scripts`
- Has many `dependencies`
- Has many `dev_dependencies`

### Test Data Configuration

**Entity:** TestDataConfiguration

**Fields:**
- `sample_audio_files` (array) - List of sample audio files
- `test_scenarios` (array) - List of test scenarios
- `edge_cases` (array) - List of edge cases

**Relationships:**
- Has many `sample_audio_files`
- Has many `test_scenarios`
- Has many `edge_cases`

---

## Data Relationships

```
VADLibraryDocumentation
├── has many → ConfigurationOption
├── has many → SupportedFormat
├── has many → SupportedSampleRate
├── has many → APIMethod
├── has many → Event
└── has many → Limitation

BrowserCompatibilityMatrix
└── has many → BrowserCompatibilityEntry

PerformanceAnalysisReport
├── has many → PerformanceBottleneck
└── has many → OptimizationOpportunity

DevelopmentEnvironmentConfiguration
├── has many → Script
├── has many → Dependency
└── has many → DevDependency

TestDataConfiguration
├── has many → SampleAudioFile
├── has many → TestScenario
└── has many → EdgeCase
```

---

## Validation Rules

### VAD Library Documentation

- `library_name` must be non-empty
- `version` must be non-empty
- `repository` must be a valid URL
- `documentation_url` must be a valid URL
- `license` must be non-empty
- `capabilities` must be non-empty
- `configuration_options` must be non-empty
- `supported_formats` must be non-empty
- `supported_sample_rates` must be non-empty
- `api_methods` must be non-empty
- `events` must be non-empty
- `limitations` must be non-empty

### Browser Compatibility Matrix

- `browser_name` must be non-empty
- `version` must be non-empty
- `webassembly_support` must be boolean
- `vad_support` must be boolean
- `vad_performance` must be non-empty
- `status` must be non-empty
- `notes` may be empty

### Performance Analysis Report

- `memory_usage.target_mb` must be > 0
- `memory_usage.measured_mb.*` must be > 0
- `cpu_usage.target_percent` must be > 0
- `cpu_usage.measured_percent.*` must be > 0
- `latency.speech_start_ms` must be >= 0
- `latency.speech_end_ms` must be >= 0
- `latency.total_vad_latency_ms` must be >= 0
- `bottlenecks` must be non-empty
- `optimization_opportunities` must be non-empty

### Development Environment Configuration

- `package_name` must be non-empty
- `version` must be non-empty
- `description` must be non-empty
- `main` must be non-empty
- `scripts` must be non-empty
- `dependencies` must be non-empty
- `dev_dependencies` may be empty
- `engines.node` must be >= 16.0.0
- `engines.npm` must be >= 8.0.0

### Test Data Configuration

- `sample_audio_files` must be non-empty
- `test_scenarios` must be non-empty
- `edge_cases` must be non-empty

---

## State Transitions

### VAD Library Documentation

**States:**
- `Not Researched` → `Researching` → `Documented`

**Transitions:**
- `Not Researched` → `Researching` - When research begins
- `Researching` → `Documented` - When research is complete

### Browser Compatibility Matrix

**States:**
- `Not Tested` → `Testing` → `Documented`

**Transitions:**
- `Not Tested` → `Testing` - When testing begins
- `Testing` → `Documented` - When testing is complete

### Performance Analysis Report

**States:**
- `Not Measured` → `Measuring` → `Documented`

**Transitions:**
- `Not Measured` → `Measuring` - When measurement begins
- `Measuring` → `Documented` - When measurement is complete

### Development Environment Configuration

**States:**
- `Not Configured` → `Configuring` → `Configured`

**Transitions:**
- `Not Configured` → `Configuring` - When configuration begins
- `Configuring` → `Configured` - When configuration is complete

### Test Data Configuration

**States:**
- `Not Created` → `Creating` → `Created`

**Transitions:**
- `Not Created` → `Creating` - When creation begins
- `Creating` → `Created` - When creation is complete

---

## Data Dictionary

### VAD Library Documentation

**library_name**: Name of the VAD library (e.g., "@ricky0123/vad")

**version**: Version of the library (e.g., "0.0.14")

**repository**: GitHub repository URL (e.g., "https://github.com/ricky0123/vad")

**documentation_url**: Documentation URL (e.g., "https://github.com/ricky0123/vad")

**license**: License type (e.g., "MIT")

**capabilities**: List of VAD capabilities (e.g., "Real-time speech detection", "WebAssembly-based execution", "Event-based interface")

**configuration_options**: List of configuration options (e.g., "positiveSpeechThreshold", "negativeSpeechThreshold", "redemptionFrames")

**supported_formats**: List of supported audio formats (e.g., "Float32", "Int16")

**supported_sample_rates**: List of supported sample rates (e.g., "16kHz", "8kHz", "44.1kHz")

**api_methods**: List of API methods (e.g., "start", "pause", "destroy")

**events**: List of events (e.g., "onSpeechStart", "onSpeechEnd", "onVADMisfire")

**limitations**: List of known limitations (e.g., "May have difficulty with very quiet speech", "May have difficulty with very fast speech")

### Browser Compatibility Matrix

**browser_name**: Name of the browser (e.g., "Chrome", "Firefox", "Safari", "Edge")

**version**: Browser version (e.g., "Current stable from last 6 months")

**webassembly_support**: Whether WebAssembly is supported (true/false)

**vad_support**: Whether @ricky0123/vad is supported (true/false)

**vad_performance**: VAD performance rating (e.g., "Excellent", "Good", "Fair", "Poor")

**status**: Compatibility status (e.g., "✅ Tested", "⚠️ Issues", "❌ Not Supported")

**notes**: Browser-specific notes or issues (e.g., "Slightly slower performance than Chrome")

### Performance Analysis Report

**memory_usage.target_mb**: Target memory usage in MB (e.g., 50)

**memory_usage.measured_mb.*`: Measured memory usage by browser (e.g., 35 for Chrome, 40 for Firefox, 45 for Safari, 40 for Edge)

**cpu_usage.target_percent**: Target CPU usage percentage (e.g., 5)

**cpu_usage.measured_percent.*`: Measured CPU usage percentage by browser (e.g., 2 for Chrome, 3 for Firefox, 3 for Safari, 2 for Edge)

**latency.speech_start_ms**: Speech start detection latency in ms (e.g., 10-20)

**latency.speech_end_ms**: Speech end detection latency in ms (e.g., 20-30)

**latency.total_vad_latency_ms**: Total VAD latency in ms (e.g., 30-50)

**bottlenecks**: List of performance bottlenecks (e.g., "VAD model loading", "Audio buffer management", "Audio processing", "Runtime overhead")

**optimization_opportunities**: List of optimization opportunities (e.g., "Preload VAD model", "Implement buffer pooling", "Optimize audio processing", "Optimize VAD model", "Optimize event handling")

### Development Environment Configuration

**package_name**: Name of the npm package (e.g., "wanis-frontend")

**version**: Version of the package (e.g., "1.0.0")

**description**: Description of the package (e.g., "Wanis frontend with client-side VAD")

**main**: Main entry point (e.g., "mediastream_app.js")

**scripts**: Build and development scripts (e.g., "dev", "build", "test", "start")

**dependencies**: Required dependencies (e.g., "@ricky0123/vad")

**dev_dependencies**: Development dependencies (e.g., "@types/node", "typescript", "eslint", "prettier")

**engines.node**: Supported Node.js version (e.g., ">=16.0.0")

**engines.npm**: Supported npm version (e.g., ">=8.0.0")

### Test Data Configuration

**sample_audio_files**: List of sample audio files (e.g., sample1.wav, sample2.wav, sample3.wav, sample4.wav, sample5.wav)

**test_scenarios**: List of test scenarios (e.g., "Basic VAD testing", "Browser compatibility testing", "WebAssembly performance analysis", "Development environment setup", "Testing environment creation")

**edge_cases**: List of edge cases (e.g., "Very quiet speech", "Very fast speech", "Overlapping speech", "Accented speech", "Different audio environments")

---

## Usage Examples

### VAD Library Documentation

```json
{
  "library_name": "@ricky0123/vad",
  "version": "0.0.14",
  "repository": "https://github.com/ricky0123/vad",
  "documentation_url": "https://github.com/ricky0123/vad",
  "license": "MIT",
  "capabilities": [
    "Real-time speech detection",
    "WebAssembly-based execution",
    "Event-based interface",
    "Configurable speech detection parameters"
  ],
  "configuration_options": [
    {
      "name": "positiveSpeechThreshold",
      "type": "number",
      "default": 0.5,
      "description": "Speech probability threshold"
    },
    {
      "name": "negativeSpeechThreshold",
      "type": "number",
      "default": 0.5,
      "description": "Non-speech probability threshold"
    },
    {
      "name": "redemptionFrames",
      "type": "number",
      "default": 10,
      "description": "Frames to wait before speech start"
    },
    {
      "name": "basePaddingMs",
      "type": "number",
      "default": 0,
      "description": "Padding before speech start"
    },
    {
      "name": "speechPadMs",
      "type": "number",
      "default": 0,
      "description": "Padding after speech end"
    },
    {
      "name": "minSpeechFrames",
      "type": "number",
      "default": 10,
      "description": "Minimum speech duration in frames"
    },
    {
      "name": "submitUserSpeakingOnPause",
      "type": "boolean",
      "default": false,
      "description": "Submit audio on pause"
    }
  ],
  "supported_formats": [
    "Float32",
    "Int16"
  ],
  "supported_sample_rates": [
    "16kHz",
    "8kHz",
    "44.1kHz"
  ],
  "api_methods": [
    {
      "name": "start",
      "description": "Start VAD processing"
    },
    {
      "name": "pause",
      "description": "Pause VAD processing"
    },
    {
      "name": "destroy",
      "description": "Clean up resources"
    }
  ],
  "events": [
    {
      "name": "onSpeechStart",
      "description": "Triggered when speech is detected"
    },
    {
      "name": "onSpeechEnd",
      "description": "Triggered when speech ends (provides audio)"
    },
    {
      "name": "onVADMisfire",
      "description": "Triggered when VAD misfires"
    }
  ],
  "limitations": [
    {
      "issue": "May have difficulty with very quiet speech",
      "severity": "Low",
      "mitigation": "Increase speech threshold"
    },
    {
      "issue": "May have difficulty with very fast speech",
      "severity": "Medium",
      "mitigation": "Adjust minSpeechFrames parameter"
    },
    {
      "issue": "May have difficulty with overlapping speech",
      "severity": "Medium",
      "mitigation": "Use server-side VAD as fallback"
    },
    {
      "issue": "May have difficulty with accented speech",
      "severity": "Low",
      "mitigation": "Test with target user audio"
    }
  ]
}
```

### Browser Compatibility Matrix

```json
{
  "browser_name": "Chrome",
  "version": "Current stable from last 6 months",
  "webassembly_support": true,
  "vad_support": true,
  "vad_performance": "Excellent",
  "status": "✅ Tested",
  "notes": "Primary target, best performance"
}
```

### Performance Analysis Report

```json
{
  "memory_usage": {
    "target_mb": 50,
    "measured_mb": {
      "chrome": 40,
      "firefox": 45,
      "safari": 50,
      "edge": 42
    }
  },
  "cpu_usage": {
    "target_percent": 5,
    "measured_percent": {
      "chrome": 2,
      "firefox": 3,
      "safari": 3,
      "edge": 2
    }
  },
  "latency": {
    "speech_start_ms": 15,
    "speech_end_ms": 25,
    "total_vad_latency_ms": 40
  },
  "bottlenecks": [
    {
      "name": "VAD model loading",
      "impact": "One-time cost, acceptable",
      "mitigation": "Preload VAD model on page load"
    },
    {
      "name": "Audio buffer management",
      "impact": "Minimal, acceptable",
      "mitigation": "Implement buffer pooling"
    },
    {
      "name": "Audio processing",
      "impact": "Minimal, acceptable",
      "mitigation": "Use SIMD for audio conversion"
    },
    {
      "name": "Runtime overhead",
      "impact": "Minimal, acceptable",
      "mitigation": "Optimize event handling"
    }
  ],
  "optimization_opportunities": [
    {
      "name": "Preload VAD model",
      "priority": "High",
      "impact": "Reduces initial load time"
    },
    {
      "name": "Implement buffer pooling",
      "priority": "Medium",
      "impact": "Reduces memory allocation"
    },
    {
      "name": "Optimize audio processing",
      "priority": "Medium",
      "impact": "Reduces CPU usage"
    },
    {
      "name": "Optimize VAD model",
      "priority": "Low",
      "impact": "Reduces CPU usage"
    },
    {
      "name": "Optimize event handling",
      "priority": "Low",
      "impact": "Reduces runtime overhead"
    }
  ]
}
```

### Development Environment Configuration

```json
{
  "package_name": "wanis-frontend",
  "version": "1.0.0",
  "description": "Wanis frontend with client-side VAD",
  "main": "mediastream_app.js",
  "scripts": {
    "dev": "python -m http.server 8080",
    "build": "npm run build",
    "test": "npm test",
    "start": "npm start"
  },
  "dependencies": {
    "@ricky0123/vad": "^0.0.14"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0",
    "eslint": "^8.0.0",
    "prettier": "^3.0.0"
  },
  "engines": {
    "node": ">=16.0.0",
    "npm": ">=8.0.0"
  }
}
```

### Test Data Configuration

```json
{
  "sample_audio_files": [
    {
      "file": "sample1.wav",
      "duration": 5,
      "speech_pattern": "Clear speech",
      "sample_rate": 16000,
      "channels": 1,
      "purpose": "Basic VAD testing"
    },
    {
      "file": "sample2.wav",
      "duration": 10,
      "speech_pattern": "Background noise",
      "sample_rate": 16000,
      "channels": 1,
      "purpose": "Noise robustness"
    },
    {
      "file": "sample3.wav",
      "duration": 8,
      "speech_pattern": "Multiple speakers",
      "sample_rate": 16000,
      "channels": 1,
      "purpose": "Multi-speaker detection"
    },
    {
      "file": "sample4.wav",
      "duration": 6,
      "speech_pattern": "Silence",
      "sample_rate": 16000,
      "channels": 1,
      "purpose": "False positive testing"
    },
    {
      "file": "sample5.wav",
      "duration": 7,
      "speech_pattern": "Fast speech",
      "sample_rate": 16000,
      "channels": 1,
      "purpose": "Rapid speech detection"
    }
  ],
  "test_scenarios": [
    {
      "id": "TS1",
      "name": "Basic VAD Testing",
      "description": "Test with clear speech",
      "steps": [
        "Load sample1.wav",
        "Initialize VAD",
        "Process audio",
        "Verify speech detection",
        "Verify speech_end event"
      ]
    },
    {
      "id": "TS2",
      "name": "Browser Compatibility Testing",
      "description": "Test @ricky0123/vad across different browsers",
      "steps": [
        "Test on Chrome",
        "Test on Firefox",
        "Test on Safari",
        "Test on Edge",
        "Document compatibility issues"
      ]
    },
    {
      "id": "TS3",
      "name": "WebAssembly Performance Analysis",
      "description": "Analyze WebAssembly performance characteristics",
      "steps": [
        "Measure memory usage",
        "Measure CPU usage",
        "Identify performance bottlenecks",
        "Document optimization opportunities"
      ]
    },
    {
      "id": "TS4",
      "name": "Development Environment Setup",
      "description": "Set up development environment",
      "steps": [
        "Create package.json",
        "Install dependencies",
        "Configure build scripts",
        "Test on different operating systems"
      ]
    },
    {
      "id": "TS5",
      "name": "Testing Environment Creation",
      "description": "Create testing environment",
      "steps": [
        "Create sample audio files",
        "Create test scenarios",
        "Configure test data",
        "Validate testing environment"
      ]
    }
  ],
  "edge_cases": [
    {
      "id": "EC1",
      "name": "Very Quiet Speech",
      "description": "Test with very quiet speech",
      "severity": "Low",
      "mitigation": "Increase speech threshold"
    },
    {
      "id": "EC2",
      "name": "Very Fast Speech",
      "description": "Test with very fast speech",
      "severity": "Medium",
      "mitigation": "Adjust minSpeechFrames parameter"
    },
    {
      "id": "EC3",
      "name": "Overlapping Speech",
      "description": "Test with overlapping speech",
      "severity": "Medium",
      "mitigation": "Use server-side VAD as fallback"
    },
    {
      "id": "EC4",
      "name": "Accented Speech",
      "description": "Test with accented speech",
      "severity": "Low",
      "mitigation": "Test with target user audio"
    },
    {
      "id": "EC5",
      "name": "Different Audio Environments",
      "description": "Test with different audio environments",
      "severity": "Low",
      "mitigation": "Test with target user audio"
    }
  ]
}
```