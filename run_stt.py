import modal
from pathlib import Path

training_code_dir = Path(__file__).parent / "src/stt"
configs_dir = Path(__file__).parent / "configs"

image = (modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "torch==2.8",
        "torchaudio==2.8",
        "transformers==4.26.1",
        "datasets",
        "librosa", 
        "soundfile",
        "evaluate==0.4.0",
        "jiwer==2.5.1",
        "numpy==1.24.3",
        "pandas==2.0.3",   
        "tqdm==4.65.0",
        "pyyaml==6.0",
        "soundfile==0.12.0",
        "peft"
    )
    .add_local_dir(training_code_dir, remote_path="/root/stt")
    .add_local_dir(configs_dir, remote_path="/root/configs")
)

app = modal.App("stt", image=image)

@app.function(
    # gpu="t4",
    timeout=3600,
)
def evaluate_model(*arglist):
    """Run STT evaluation on Modal - direct function call"""

    import argparse
    import yaml
    import os
    import pandas as pd
    from stt.baseline_evaluation import STTEvaluator


    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str)
    parser.add_argument("--dataset", type=str)
    args = parser.parse_args(args = arglist)

    model_name = args.model
    dataset_name = args.dataset
    
    config_path = '/root/configs/stt_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    evaluator = STTEvaluator(config)
    
    print(f"Starting Evaluation - Model: {model_name}, Dataset: {dataset_name}")

    if dataset_name not in config['datasets']:
    
        available_datasets = list(config['datasets'].keys())
        raise ValueError(f"Dataset '{dataset_name}' not found in config. Available datasets: {available_datasets}")
    
    dataset_config = config['datasets'][dataset_name]
    
    result = evaluator.evaluate_model_dataset(model_name, dataset_config)

    
    output_dir = '/root/results'
    os.makedirs(output_dir, exist_ok=True)
    
    if result:
        results_df = pd.DataFrame([result])
        safe_model_name = model_name.replace("/", "_")
        results_path = os.path.join(output_dir, f'stt_evaluation_{safe_model_name}_{dataset_name}.csv')
        results_df.to_csv(results_path, index=False)
        
        print(f"\nEvaluation completed! Results saved to: {results_path}")
        print("\nResults:")
        for key, value in result.items():
            print(f"{key}: {value}")
        
        return result
    else:
        print("Evaluation failed!")
        return None

# @app.local_entrypoint()
# def main():
#     # parser = argparse.ArgumentParser()
#     # parser.add_argument("--model", type=str, default="openai/whisper-tiny")
#     # parser.add_argument("--dataset", type=str, default="egyptian_asr")
    
#     # args = parser.parse_args()

#     evaluate_model.remote("openai/whisper-tiny","egyptian_asr")