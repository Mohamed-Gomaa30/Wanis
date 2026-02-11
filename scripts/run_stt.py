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
    # 1. Install required system packages
    .apt_install("libsndfile1", "ffmpeg") 
    .pip_install(
        # Standard Python packages
        "python-dotenv", 
        "datasets",
        "evaluate",
        "jiwer",
        "librosa",
        "soundfile", 
        "whisper_normalizer==0.1.12",
        
        # PyTorch dependencies (use compatible versions)
        "torch==2.8.0",
        "torchcodec==0.7.0",
        # Consider adding a specific torchaudio version if 2.8.0 requires one:
        # "torchaudio==2.8.0", 
    )
    # 2. Install NeMo from GitHub with the '[all]' extras
    # .pip_install(
    #     "Cython",
    #     # Use the git+URL format and append '#egg=nemo_toolkit[all]' 
    #     # to install all collections (like nemo.collections.asr)
    #     "git+https://github.com/NVIDIA/NeMo.git#egg=nemo_toolkit[all]" 
    # )
    # This is the line you must include/uncomment:
    .pip_install("nemo_toolkit[all]")
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
            # gpu="A10",
            timeout=3600*6)
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
            # gpu="A10",
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

    config_path = '/root/configs/asr_stt/nemo_config.yaml'
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

# Fine Tune Nemo 
@app.function(
    image=whisper_nemo_image,
    gpu="t4",  
    timeout=14400,
    volumes={"/root/nemo_dataset": modal.Volume.from_name("nemo-manifests", create_if_missing=True)}
)
def fine_tune_nemo(*arglist):
    """Fine-tune NeMo models"""
    import argparse
    import yaml
    import os
    import sys
    
    sys.path.insert(0, '/root/stt/train/nemo')
    from nemo_finetuner import NeMoFineTuner  
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="/root/fine_tuned_models")
    parser.add_argument("--force-recreate-manifests", action="store_true", 
                       help="Force recreation of manifest files")
    args = parser.parse_args(args=arglist)
    
    config_path = '/root/configs/asr_stt/nemo_config.yaml'
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"Fine-tuning {args.model} on {args.dataset}")
    
    fine_tuner = NeMoFineTuner(config)
    
    # Call fine_tune_model without train_manifest and val_manifest arguments
    # The method will use paths from the config file
    result = fine_tuner.fine_tune_model(
        base_model=args.model,
        dataset_name=args.dataset,
        output_dir=os.path.join(args.output_dir, f"{args.model.replace('/', '_')}_{args.dataset}"),
        force_recreate_manifests=args.force_recreate_manifests
    )
    
    print(f"Fine-tuning completed! Model saved to: {result}")
    return result
# @app.function(image=whisper_nemo_image_2,
#             # gpu="t4",
#             timeout=14400)
# def fine_tune_nemo(*arglist):
#     """Fine-tune NeMo models"""
#     import argparse
#     import yaml
#     import os
#     import sys
    
#     sys.path.insert(0, '/root/stt/train')
#     from nemo_finetuner import NeMoFineTuner  

#     parser = argparse.ArgumentParser()
#     parser.add_argument("--model", type=str, required=True)
#     parser.add_argument("--dataset", type=str, required=True)
#     parser.add_argument("--output-dir", type=str, default="/root/fine_tuned_models")
#     args = parser.parse_args(args=arglist)

#     config_path = '/root/configs/asr_stt/nemo_config.yaml'
   
#     with open(config_path, 'r') as f:
#         config = yaml.safe_load(f)
    
#     print(f"Fine-tuning {args.model} on {args.dataset}")
    
#     fine_tuner = NeMoFineTuner(config)
#     result = fine_tuner.fine_tune_model(
#         base_model=args.model,
#         dataset_name=args.dataset,
#         output_dir=os.path.join(args.output_dir, f"{args.model.replace('/', '_')}_{args.dataset}")
#     )
    
#     print(f"Fine-tuning completed! Model saved to: {result}")
#     return result

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
