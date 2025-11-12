"""
Script to run STT baseline evaluation
"""

import sys
import os
import yaml
import pandas as pd

# Add src to path
# sys.path.append(os.path.join(os.path.dirname(__file__), 'training'))

# from training.baseline_evaluation import STTEvaluator
from stt.baseline_evaluation import STTEvaluator


def main():
    print("Hello ya hamoo")
    # Load configuration - works in Modal since configs is mounted at /root/configs
    config_path = '/root/configs/stt_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize evaluator
    evaluator = STTEvaluator(config)
    
    # Run evaluation
    print("Starting STT Baseline Evaluation...")
    results_df = evaluator.evaluate_all_models()
    
    # Save results - use absolute path for Modal
    output_dir = '/root/results'
    os.makedirs(output_dir, exist_ok=True)
    results_path = os.path.join(output_dir, 'stt_baseline_results.csv')
    results_df.to_csv(results_path, index=False)
    
    print(f"\nEvaluation completed! Results saved to: {results_path}")
    print("\nSummary:")
    print(results_df[['model', 'dataset', 'wer', 'cer', 'accuracy']].to_string(index=False))

if __name__ == "__main__":
    main()