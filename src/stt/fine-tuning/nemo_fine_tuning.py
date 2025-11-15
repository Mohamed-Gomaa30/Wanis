import torch
import nemo.collections.asr as nemo_asr
from omegaconf import DictConfig
import yaml
from datasets import load_dataset
import os
from typing import Dict

from stt.preprocessing import normalize_arabic_text

class NeMoFineTuner:
    def __init__(self, config: Dict):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def prepare_manifest(self, dataset_name: str, split: str = "train"):
        """Create NeMo-compatible manifest file"""
        dataset_config = self.config['datasets'][dataset_name]
        
        dataset = load_dataset(
            dataset_config['path'],
            split=split
        )
        
        manifest_data = []
        output_dir = "/tmp/nemo_manifests"
        os.makedirs(output_dir, exist_ok=True)
        
        for i, item in enumerate(dataset):
            audio_path = f"audio_{i}.wav"  # Placeholder - in real scenario, you'd save audio files
            text = normalize_arabic_text(item[dataset_config['text_col']])
            
            manifest_data.append({
                "audio_filepath": audio_path,
                "duration": len(item[dataset_config['audio_col']]['array']) / item[dataset_config['audio_col']]['sampling_rate'],
                "text": text
            })
        
        manifest_path = os.path.join(output_dir, f"{dataset_name}_{split}_manifest.json")
        
        # In a real implementation, you'd save the manifest and audio files
        # For now, we'll use a simplified approach
        
        return manifest_path
    
    def fine_tune_model(self, base_model: str, dataset_name: str, output_dir: str):
        """Fine-tune a NeMo model"""
        print(f"Fine-tuning {base_model} on {dataset_name}")
        
        # Load pretrained model
        asr_model = nemo_asr.models.ASRModel.from_pretrained(base_model)
        
        # Setup training configuration
        asr_model.setup_training_data(
            train_data_config={
                'manifest_filepath': self.prepare_manifest(dataset_name, 'train'),
                'batch_size': self.config['training']['batch_size'],
                'sample_rate': 16000,
            }
        )
        
        asr_model.setup_validation_data(
            val_data_config={
                'manifest_filepath': self.prepare_manifest(dataset_name, 'test'),
                'batch_size': self.config['training']['batch_size'],
                'sample_rate': 16000,
            }
        )
        
        # Configure optimizer
        asr_model.setup_optimization(
            optimizer_config={
                'name': 'adamw',
                'lr': self.config['training']['learning_rate']
            }
        )
        
        # Start fine-tuning
        asr_model.train()
        
        trainer = nemo_asr.models.ASRModel.Trainer(
            asr_model,
            training_config={
                'max_epochs': self.config['training'].get('epochs', 3),
                'precision': 16,
            }
        )
        
        trainer.fit(asr_model)
        
        # Save fine-tuned model
        asr_model.save_to(os.path.join(output_dir, "model.nemo"))
        
        return output_dir