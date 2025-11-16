import torch
import pandas as pd
from datasets import load_dataset
from transformers import WhisperProcessor, WhisperForConditionalGeneration # torch==2.9 torchcodec==0.8 
# from speechbrain.pretrained import EncoderASR  # torch==2.8 torchcodec==0.7
# import nemo.collections.asr as nemo_asr # torch==2.9 torchcodec==0.8
from jiwer import wer, cer
from tqdm import tqdm
import warnings
import numpy as np
import librosa

warnings.filterwarnings('ignore')

from stt.preprocessing import normalize_arabic_text


class STTEvaluator:
    """
    Evaluate ASR models on Egyptian Arabic datasets
    Supports Whisper, NeMo, and SpeechBrain models
    """
    
    def __init__(self, config):
        self.config = config
        self.device = config['evaluation']['device'] if torch.cuda.is_available() else "cpu"
        print(f"Initialized STT Evaluator on {self.device}")
    
    def load_model(self, model_name):
        """Load a Whisper, NeMo, or SpeechBrain model"""
        print(f"Loading {model_name}...")
        try:
            if model_name.startswith("openai/"): 
                # Load Whisper model
                processor = WhisperProcessor.from_pretrained(model_name)
                model = WhisperForConditionalGeneration.from_pretrained(model_name)
                model = model.to(self.device)
                model.eval()
                return {"type": "whisper", "processor": processor, "model": model}
            
            elif model_name.startswith("nvidia/"):
                # Load NeMo model
                asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name) 
                asr_model = asr_model.to(self.device)
                asr_model.eval()
                return {"type": "nemo", "model": asr_model}
            
            elif model_name.startswith("speechbrain/"): 
                # Load SpeechBrain model
                speechbrain_model = EncoderASR.from_hparams(model_name)
                speechbrain_model = speechbrain_model.to(self.device)
                speechbrain_model.eval()
                return {"type": "speechbrain", "model": speechbrain_model}
            else:
                print(f"Unsupported model type: {model_name}")
                return None

        except Exception as e:
            print(f"Error loading {model_name}: {e}")
            return None
    
    def transcribe_audio_whisper(self, processor, model, audio_array, sampling_rate):
        """Transcribe a single audio sample using Whisper"""
        try:
            inputs = processor(
                audio_array, 
                sampling_rate=sampling_rate, 
                return_tensors="pt"
            ).to(self.device)
            
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
            print(f"Whisper transcription error: {e}")
            return ""
    
    def transcribe_audio_nemo(self, model, audio_array, sampling_rate):
        """Transcribe a single audio sample using NeMo"""
        try:
            if sampling_rate != 16000:
                audio_array = librosa.resample(
                    y=audio_array, 
                    orig_sr=sampling_rate, 
                    target_sr=16000
                )
                sampling_rate = 16000
            
            with torch.no_grad():
                transcriptions = model.transcribe([audio_array])
            
            if transcriptions:
                return transcriptions[0]
            else:
                return ""
                
        except Exception as e:
            print(f"NeMo transcription error: {e}")
            return ""
    
    def transcribe_audio_speechbrain(self, model, audio_array, sampling_rate):
        """Transcribe a single audio sample using SpeechBrain"""
        try:
            if isinstance(audio_array, np.ndarray):
                audio_tensor = torch.from_numpy(audio_array)
            else:
                audio_tensor = torch.FloatTensor(audio_array)
            
            audio_tensor = audio_tensor.float()
            
            if audio_tensor.dim() == 2:
                audio_tensor = audio_tensor[0]
            
            audio_tensor = audio_tensor.squeeze()
            
            wavs_batch = audio_tensor.unsqueeze(0)  # [1, time]
            wav_lens = torch.tensor([1.0], dtype=torch.float32)  # Relative length
            
            if self.device == "cuda":
                wavs_batch = wavs_batch.cuda()
                wav_lens = wav_lens.cuda()
            
            with torch.no_grad():
                transcriptions = model.transcribe_batch(wavs_batch, wav_lens)[0]
            
            if transcriptions:
                return transcriptions[0]
            else:
                return ""
                
        except Exception as e:
            print(f"SpeechBrain transcription error: {e}")
            return ""
    
    def preprocess_audio(self, audio_array, sampling_rate, target_sr=16000):
        """Preprocess audio for ASR models"""
        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)
        
        if np.max(np.abs(audio_array)) > 0:
            audio_array = audio_array / np.max(np.abs(audio_array))
        
        if sampling_rate != target_sr:
            audio_array = librosa.resample(
                y=audio_array,
                orig_sr=sampling_rate,
                target_sr=target_sr
            )
            sampling_rate = target_sr
        
        return audio_array, sampling_rate
    
    def evaluate_model_dataset(self, model_name, dataset_config):
        """Evaluate a single model on a single dataset"""
        print(f"\nEvaluating {model_name} on {dataset_config['name']}")

        model_info = self.load_model(model_name)
        if model_info is None:
            return None
        
        try:
            dataset = load_dataset(
                dataset_config["path"], 
                split=dataset_config["test_split"],
                trust_remote_code=True
            )

            max_samples = self.config['evaluation']['max_samples']
            if max_samples is not None and len(dataset) > max_samples:
                dataset = dataset.select(range(max_samples))
            
            references = []
            predictions = []
            processing_times = []
            
            for sample in tqdm(dataset, desc=f"Processing {model_name.split('/')[-1]}"):
                audio = sample[dataset_config["audio_col"]]
                reference_text = sample[dataset_config["text_col"]]
                
                import time
                start_time = time.time()
                
                audio_array = audio['array']
                sampling_rate = audio["sampling_rate"]
                
                audio_array, sampling_rate = self.preprocess_audio(audio_array, sampling_rate)
                
                transcription = ""
                if model_info["type"] == "whisper":
                    transcription = self.transcribe_audio_whisper(
                        model_info["processor"], 
                        model_info["model"], 
                        audio_array, 
                        sampling_rate
                    )
                elif model_info["type"] == "nemo":
                    transcription = self.transcribe_audio_nemo(
                        model_info["model"],
                        audio_array,
                        sampling_rate
                    )
                elif model_info["type"] == "speechbrain":
                    transcription = self.transcribe_audio_speechbrain(
                        model_info["model"],
                        audio_array,
                        sampling_rate
                    )
                
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
                
                normalized_reference = normalize_arabic_text(reference_text)
                normalized_prediction = normalize_arabic_text(transcription)
                
                references.append(normalized_reference)
                predictions.append(normalized_prediction)
            
            wer_score = wer(references, predictions)
            cer_score = cer(references, predictions)
            
            exact_matches = sum(1 for ref, pred in zip(references, predictions) if ref == pred)
            accuracy = exact_matches / len(references) if references else 0
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
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
            
            print(f"{model_name}: WER={wer_score:.3f}, CER={cer_score:.3f}, Accuracy={accuracy:.3f}")
            return result
            
        except Exception as e:
            print(f"Error evaluating {model_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def evaluate_all_models(self):
        """Evaluate all models on all datasets"""
        all_results = []
        
        for dataset_name, dataset_config in self.config['datasets'].items():
            print(f"\n{'='*60}")
            print(f"DATASET: {dataset_name}")
            print(f"{'='*60}")
            
            for model_name in self.config['models']['baseline']:
                result = self.evaluate_model_dataset(model_name, dataset_config)
                if result is not None:
                    all_results.append(result)
        
        return pd.DataFrame(all_results)
    
    def get_best_model(self, results_df, metric="wer"):
        """Get the best performing model based on specified metric"""
        if results_df.empty:
            print("No results to analyze")
            return None
            
        if metric == "wer":
            best_idx = results_df['wer'].idxmin()
        elif metric == "accuracy":
            best_idx = results_df['accuracy'].idxmax()
        else:
            best_idx = results_df['cer'].idxmin()
            
        return results_df.loc[best_idx]