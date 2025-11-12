import torch
import pandas as pd
from datasets import load_dataset
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from evaluate import load
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

from .preprocessing import normalize_arabic_text


# Whisper Eval
class STTEvaluator:
    """
    Evaluate Whisper models on Egyptian Arabic datasets
    """
    
    def __init__(self, config):
        self.config = config
        self.device = config['evaluation']['device'] if torch.cuda.is_available() else "cpu"
        print(f"🔧 Initialized STT Evaluator on {self.device}")
    
    def load_model(self, model_name):
        """Load a Whisper model and processor"""
        print(f"Loading {model_name}...")
        try:
            processor = WhisperProcessor.from_pretrained(model_name)
            model = WhisperForConditionalGeneration.from_pretrained(model_name)
            model = model.to(self.device)
            model.eval()
            return processor, model
        except Exception as e:
            print(f"Error loading {model_name}: {e}")
            return None, None
    
    def transcribe_audio(self, processor, model, audio_array, sampling_rate):
        """Transcribe a single audio sample"""
        try:
            # Process audio
            inputs = processor(
                audio_array, 
                sampling_rate=sampling_rate, 
                return_tensors="pt"
            ).to(self.device)
            
            # Generate transcription with Arabic language forcing
            forced_decoder_ids = processor.get_decoder_prompt_ids(
                language="arabic", 
                task="transcribe"
            )
            
            with torch.no_grad():
                generated_ids = model.generate(
                    **inputs, 
                    forced_decoder_ids=forced_decoder_ids,
                    max_length=448
                )
            
            transcription = processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            return transcription
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    def evaluate_model_dataset(self, model_name, dataset_config):
        """Evaluate a single model on a single dataset"""
        print(f"\nEvaluating {model_name} on {dataset_config['name']}")
        
        processor, model = self.load_model(model_name)
        if processor is None or model is None:
            return None
        
        try:
            # Load dataset
            dataset = load_dataset(
                dataset_config["name"], 
                split=dataset_config["split"],
                trust_remote_code=True
            )
            # ----------------------------------------------------------------------------------
            dataset = dataset.select(range(100))
            
            # Limit samples
            max_samples = self.config['evaluation']['max_samples']
            if len(dataset) > max_samples:
                dataset = dataset.select(range(max_samples))
            
            references = []
            predictions = []
            processing_times = []
            
            # Process each sample
            for sample in tqdm(dataset, desc=f"Processing {model_name.split('/')[-1]}"):
                audio = sample[dataset_config["audio_col"]]
                reference_text = sample[dataset_config["text_col"]]
                
                import time
                start_time = time.time()
                
                # Transcribe audio
                transcription = self.transcribe_audio(
                    processor, model, audio["array"], audio["sampling_rate"]
                )
                
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
                
                # Apply normalization
                references.append(normalize_arabic_text(reference_text))
                predictions.append(normalize_arabic_text(transcription))
            
            # Calculate metrics
            wer_metric = load("wer")
            cer_metric = load("cer")
            
            wer_score = wer_metric.compute(references=references, predictions=predictions)
            cer_score = cer_metric.compute(references=references, predictions=predictions)
            
            exact_matches = sum(1 for ref, pred in zip(references, predictions) if ref == pred)
            accuracy = exact_matches / len(references)
            avg_processing_time = sum(processing_times) / len(processing_times)
            
            result = {
                "model": model_name,
                "dataset": dataset_config["name"],
                "wer": wer_score,
                "cer": cer_score,
                "accuracy": accuracy,
                "samples_tested": len(references),
                "avg_processing_time": avg_processing_time,
                "total_processing_time": sum(processing_times)
            }
            
            print(f"✅ {model_name}: WER={wer_score:.3f}, CER={cer_score:.3f}, Accuracy={accuracy:.3f}")
            return result
            
        except Exception as e:
            print(f"❌ Error evaluating {model_name}: {str(e)}")
            return None
    
    def evaluate_all_models(self):
        """Evaluate all models on all datasets"""
        all_results = []
        
        for dataset_name, dataset_config in self.config['datasets'].items():
            print(f"\n{'='*60}")
            print(f"📊 DATASET: {dataset_name}")
            print(f"{'='*60}")
            
            for model_name in self.config['models']['baseline']:
                result = self.evaluate_model_dataset(model_name, dataset_config)
                if result is not None:
                    all_results.append(result)
        
        return pd.DataFrame(all_results)
    
    def get_best_model(self, results_df, metric="wer"):
        """Get the best performing model based on specified metric"""
        if metric == "wer":
            best_idx = results_df['wer'].idxmin()
        elif metric == "accuracy":
            best_idx = results_df['accuracy'].idxmax()
        else:
            best_idx = results_df['cer'].idxmin()
            
        return results_df.loc[best_idx]