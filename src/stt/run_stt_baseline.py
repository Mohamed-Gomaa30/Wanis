"""
Script to run STT baseline evaluation
"""

import os
import yaml
import pandas as pd
import argparse
from stt.baseline_evaluation import STTEvaluator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, help="Model name")
    parser.add_argument("--dataset", type=str, required=True, help="Dataset name") 
    parser.add_argument("--mode", type=str, default="evaluate", help="Run mode")
    
    args = parser.parse_args()
    
    # Load config
    config_path = '/root/configs/stt_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize evaluator
    evaluator = STTEvaluator(config)
    
    print(f"Starting Evaluation - Model: {args.model}, Dataset: {args.dataset}")
    
    # Get dataset config
    if args.dataset not in config['datasets']:
        raise ValueError(f"Dataset {args.dataset} not found in config. Available: {list(config['datasets'].keys())}")
    
    dataset_config = config['datasets'][args.dataset]
    
    # Run evaluation
    result = evaluator.evaluate_model_dataset(args.model, dataset_config)
    
    # Save results
    output_dir = '/root/results'
    os.makedirs(output_dir, exist_ok=True)
    
    if result:
        results_df = pd.DataFrame([result])
        results_path = os.path.join(output_dir, f'stt_evaluation_{args.model.replace("/", "_")}_{args.dataset}.csv')
        results_df.to_csv(results_path, index=False)
        
        print(f"\nEvaluation completed! Results saved to: {results_path}")
        print("\nResults:")
        print(f"Model: {result['model']}")
        print(f"Dataset: {result['dataset']}")
        print(f"WER: {result['wer']:.3f}")
        print(f"CER: {result['cer']:.3f}")
        print(f"Accuracy: {result['accuracy']:.3f}")
        print(f"Samples tested: {result['samples_tested']}")
    else:
        print("Evaluation failed!")

if __name__ == "__main__":
    main()