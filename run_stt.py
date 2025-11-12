# import os
from pathlib import Path
import modal

training_code_dir = Path(__file__).parent / "src/stt"
configs_dir = Path(__file__).parent / "configs"

print(training_code_dir)

image = (modal.Image.debian_slim(python_version="3.10").pip_install(
    "torch==2.8",
    "torchcodec==0.7", 
    "transformers==4.26.1",
    "datasets",
    "librosa", 
    "evaluate==0.4.0",
    "jiwer==2.5.1",
    "numpy==1.24.3",
    "pandas==2.0.3",   
    "tqdm==4.65.0",
    "pyyaml==6.0",
    "soundfile")
    .add_local_dir(training_code_dir, remote_path="/root/stt")
    .add_local_dir(configs_dir, remote_path="/root/configs")
)
app = modal.App(
    "stt", 
    image=image
)

@app.function(
    gpu="t4",
    timeout=3600,
    # volumes={"/results": volume},
)
def run_stt_baseline_evaluation():
    import subprocess
    subprocess.run(["python", "stt/run_stt_baseline.py"])

@app.local_entrypoint()
def main():
    # if config.runtime == "runc":
    #     assert os.environ["MODAL_FUNCTION_RUNTIME"] == "runc"
    # else:
    #     assert "MODAL_FUNCTION_RUNTIME" not in os.environ
    run_stt_baseline_evaluation.remote()
