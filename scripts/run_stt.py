import os
import modal
from pathlib import Path

training_code_dir = Path(__file__).parent.parent / "src/stt"
fine_tuning_code_dir = Path(__file__).parent.parent / "src/stt/train"
configs_dir = Path(__file__).parent.parent / "configs"
congig_env = Path(__file__).parent.parent / ".env" # .env path 

# Create separate images for different model types due to dependency conflicts
whisper_nemo_image = (
    modal.Image.debian_slim(python_version="3.10")
    # .uv_pip_install("nemo_toolkit[all]")
    .pip_install(
        # "torch==2.9",
        # "torchcodec==0.8", 
        # "transformers==4.26.1", 
        # "datasets",
        # "librosa", 
        # "soundfile",
        # "evaluate==0.4.0",
        # "jiwer==2.5.1",
        # "numpy==1.24.3",
        # "pandas==2.0.3",   
        # "tqdm==4.65.0",
        # "pyyaml==6.0",
        # "peft"
        "ipywidgets", 
        "transformers>=4.52.0", 
        "accelerate==1.8.1",
        "datasets==3.6.0",
        "evaluate==0.4.5",
        "jiwer==4.0.0",
        "librosa==0.11.0",
        "torch==2.8.0",
        "torchcodec==0.7",
        "torchaudio==2.8.0",
        "transformers==4.52.0",
        "whisper_normalizer==0.1.12", 
        "python-dotenv"
    ).uv_pip_install("huggingface_hub")
    .pip_install("huggingface_hub")
    .add_local_dir(training_code_dir, remote_path="/root/stt")
    .add_local_dir(fine_tuning_code_dir, remote_path="/root/stt/fine-tuning")
    .add_local_dir(configs_dir, remote_path="/root/configs")
    .add_local_file(congig_env, "/root/") # .env file 
    
)


# speechbrain_image = (
#     modal.Image.debian_slim(python_version="3.10")
#     .pip_install(
#         "jiwer",
#         "datasets",
#         "torch==2.8 ",
#         "torchcodec==0.7",
#         "speechbrain",
#         "transformers",
#         "huggingface-hub==0.20.3",
#         "librosa"
#     )
#     .add_local_dir(training_code_dir, remote_path="/root/stt")
#     .add_local_dir(fine_tuning_code_dir, remote_path="/root/stt/fine-tuning")  # Fixed path
#     .add_local_dir(configs_dir, remote_path="/root/configs")
# )

app = modal.App("stt")

# Evaluation functions
@app.function(image=whisper_nemo_image,
            # gpu="t4",
            timeout=3600)
def evaluate_model(*arglist):
    """Run STT evaluation on Modal"""
    import argparse
    import yaml
    import os
    import pandas as pd
    from stt.baseline_evaluation import STTEvaluator

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str)
    parser.add_argument("--dataset", type=str)
    args = parser.parse_args(args=arglist)

    model_name = args.model
    dataset_name = args.dataset
    
    config_path = '/root/configs/stt_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    evaluator = STTEvaluator(config)
    
    print(f"Starting Evaluation - Model: {model_name}, Dataset: {dataset_name}")

    if dataset_name not in config['datasets']:
        available_datasets = list(config['datasets'].keys())
        raise ValueError(f"Dataset '{dataset_name}' not found. Available: {available_datasets}")
    
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

# Fine-tuning functions 
@app.function(image=whisper_nemo_image,
            secrets=[modal.Secret.from_dotenv(Path(__file__).parent)], 
            gpu="A10",
            timeout=14400)
def fine_tune_whisper(*arglist):
    """Fine-tune Whisper models"""
    import argparse
    import yaml
    import os
    import sys
    
    
    sys.path.insert(0, '/root/stt/train')
    from whisper_fine_tuning import WhisperFineTuner  

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="/root/fine_tuned_models")
    args = parser.parse_args(args=arglist)

    config_path = '/root/configs/stt_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"Fine-tuning {args.model} on {args.dataset}")
    
    fine_tuner = WhisperFineTuner(config)
    result = fine_tuner.fine_tune_model(
        base_model=args.model,
        dataset_name=args.dataset,
        output_dir=os.path.join(args.output_dir, f"{args.model.replace('/', '_')}_{args.dataset}")
    )
    
    print(f"Fine-tuning completed! Model saved to: {result}")
    return result

@app.function(image=whisper_nemo_image,
            # gpu="a100",
            timeout=14400)
def fine_tune_nemo(*arglist):
    """Fine-tune NeMo models"""
    import argparse
    import yaml
    import os
    import sys
    
    sys.path.insert(0, '/root/stt/train')
    from nemo_fine_tuning import NeMoFineTuner  

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="/root/fine_tuned_models")
    args = parser.parse_args(args=arglist)

    config_path = '/root/configs/stt_config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"Fine-tuning {args.model} on {args.dataset}")
    
    fine_tuner = NeMoFineTuner(config)
    result = fine_tuner.fine_tune_model(
        base_model=args.model,
        dataset_name=args.dataset,
        output_dir=os.path.join(args.output_dir, f"{args.model.replace('/', '_')}_{args.dataset}")
    )
    
    print(f"Fine-tuning completed! Model saved to: {result}")
    return result

# @app.function(image=speechbrain_image,
#             # gpu="a100",
#             timeout=14400)
# def fine_tune_speechbrain(*arglist):
#     """Fine-tune SpeechBrain models"""
#     import argparse
#     import yaml
#     import os
#     import sys
    
#     # Add fine-tuning directory to Python path
#     sys.path.insert(0, '/root/stt/fine-tuning')
#     from speechbrain_fine_tuning import SpeechBrainFineTuner  # Direct import from fine-tuning directory

#     parser = argparse.ArgumentParser()
#     parser.add_argument("--model", type=str, required=True)
#     parser.add_argument("--dataset", type=str, required=True)
#     parser.add_argument("--output-dir", type=str, default="/root/fine_tuned_models")
#     args = parser.parse_args(args=arglist)

#     config_path = '/root/configs/stt_config.yaml'
#     with open(config_path, 'r') as f:
#         config = yaml.safe_load(f)
    
#     print(f"Fine-tuning {args.model} on {args.dataset}")
    
#     fine_tuner = SpeechBrainFineTuner(config)
#     result = fine_tuner.fine_tune_model(
#         base_model=args.model,
#         dataset_name=args.dataset,
#         output_dir=os.path.join(args.output_dir, f"{args.model.replace('/', '_')}_{args.dataset}")
#     )
    
#     print(f"Fine-tuning completed! Model saved to: {result}")
#     return result
