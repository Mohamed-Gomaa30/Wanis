"""
Script to run STT baseline evaluation
"""

import sys
import os
import yaml
import pandas as pd


from stt.baseline_evaluation import STTEvaluator


def main(model_name: str, dataset_name:str, mode:str):
    config_path = '/root/configs/stt_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    evaluator = STTEvaluator(config)
    
    print(f"Starting Evaluate: {model_name}\t Dataset: {dataset_name}")
    # results_model 
    result = evaluator.evaluate_model_dataset(model_name, config['datasets'])
    
    
    output_dir = '/root/results'
    os.makedirs(output_dir, exist_ok=True)
    results_path = os.path.join(output_dir, 'stt_baseline_results.csv')
    print(f"\nEvaluation completed! Results saved to: {results_path}")
    print("\nSummary:")
    print(result[['model', 'dataset', 'wer', 'cer', 'accuracy']].to_string(index=False))



    # print("Starting STT Baseline Evaluation...")
    # results_df = evaluator.evaluate_all_models()

    
    
    # output_dir = '/root/results'
    # os.makedirs(output_dir, exist_ok=True)
    # results_path = os.path.join(output_dir, 'stt_baseline_results.csv')
    # results_df.to_csv(results_path, index=False)
    
    # print(f"\nEvaluation completed! Results saved to: {results_path}")
    # print("\nSummary:")
    # print(results_df[['model', 'dataset', 'wer', 'cer', 'accuracy']].to_string(index=False))

if __name__ == "__main__":
    main()