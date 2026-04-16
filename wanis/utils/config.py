"""
Configuration Loader for Wanis.

Loads configuration from YAML file and provides access to component configs.
Centralized config for: voice, agent, services, hardware, logging.
"""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_config: Optional[dict] = None
_config_path: Optional[Path] = None


def get_config(reload: bool = False) -> dict:
    """
    Get the global configuration.

    Args:
        reload: Force reload from file

    Returns:
        Configuration dictionary
    """
    global _config, _config_path

    if _config is not None and not reload:
        return _config

    # Default config path
    if _config_path is None:
        _config_path = Path(__file__).parent.parent / "configs" / "wanis_config.yaml"

    if not _config_path.exists():
        logger.warning(f"Config file not found: {_config_path}, using defaults")
        _config = get_default_config()
        return _config

    try:
        import yaml

        with open(_config_path) as f:
            _config = yaml.safe_load(f) or {}
        logger.debug(f"Loaded config from {_config_path}")
        return _config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        _config = get_default_config()
        return _config


def set_config_path(path: str | Path) -> None:
    """Set a custom config file path."""
    global _config_path, _config
    _config_path = Path(path)
    _config = None  # Force reload on next get_config()


def get_default_config() -> dict:
    """Get default configuration values."""
    return {
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size_ms": 30,
            "buffer_seconds": 30,
        },
        "stt": {
            "model_id": "NAMAA-Space/EgypTalk-ASR-v2",
            "local_model_path": "models/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo",
            "language": "ar-EG",
            "max_retries": 3,
            "retry_delay": 0.1,
        },
        "tts": {
            "model_id": "OmarSamir/EGTTS-V0.1",
            "language": "ar",
            "speed": 0.85,
            "sample_rate": 16000,
        },
        "vad": {
            "model": "silero_vad",
            "threshold": 0.5,
            "min_speech_ms": 250,
            "min_silence_ms": 700,
        },
        "sentence_buffer": {
            "min_length": 10,
        },
        "websocket": {
            "host": "0.0.0.0",
            "port": 8000,
        },
        "agent": {
            "model": "gemini-2.0-flash",
            "temperature": 0.7,
            "max_tokens": 512,
            "max_history_turns": 3,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }


def get_section(section: str) -> dict:
    """
    Get a specific configuration section.

    Args:
        section: Section name (e.g., "stt", "tts", "vad")

    Returns:
        Section dictionary or empty dict if not found
    """
    config = get_config()
    return config.get(section, {})


def get_value(section: str, key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value.

    Args:
        section: Section name
        key: Key name
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    section_data = get_section(section)
    return section_data.get(key, default)
