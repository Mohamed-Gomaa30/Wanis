#!/usr/bin/env python3
"""
Script to run STT fine-tuning
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.stt.fine_tuning import STTFineTuner
import yaml

def main():
    # Load configuration
    with open('configs/stt_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize fine-tuner
    fine_tuner = STTFineTuner(config)
    
    # Base model to fine-tune (you can choose from the baseline models)
    base_model = "openai/whisper-small"
    output_dir = "results/fine_tuned_whisper_small"
    
    # Run fine-tuning
    print("Starting fine-tuning...")
    fine_tuner.fine_tune_model(base_model, output_dir)
    print("Fine-tuning completed!")

if __name__ == "__main__":
    main()