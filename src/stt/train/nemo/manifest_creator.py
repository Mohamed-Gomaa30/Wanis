import json
import os
from nemo.utils import logging
from typing import Dict, Union, Tuple
from pathlib import Path
from datasets import load_dataset, DatasetDict, Audio
import soundfile as sf
from tqdm import tqdm

from stt.preprocessing import normalize_arabic_text


class ManifestCreator:
    """Create NeMo manifest files from HuggingFace datasets"""
    
    def __init__(self, 
                 dataset_path: str,
                 audio_col: str,
                 text_col: str,
                 train_manifest_path: str,
                 val_manifest_path: str,
                 test_manifest_path: str,
                 audio_dir: str,
                 train_split: str = "train",
                 val_split: str = "validation",
                 test_split: str = "test",
                 sampling_rate: int = 16000,
                 min_duration: float = 0.5,
                 max_duration: float = 30.0):
                
        self.dataset_path = dataset_path
        self.audio_col = audio_col
        self.text_col = text_col
        
        # Predefined manifest paths
        self.train_manifest_path = train_manifest_path
        self.val_manifest_path = val_manifest_path
        self.test_manifest_path = test_manifest_path
        self.audio_dir = Path(audio_dir)
        
        self.train_split = train_split
        self.val_split = val_split
        self.test_split = test_split
        self.sampling_rate = sampling_rate
        self.min_duration = min_duration
        self.max_duration = max_duration
        
        # Create directories
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        Path(self.train_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.val_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.test_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        
    def load_dataset(self):
        """Load dataset from HuggingFace"""
        logging.info(f"Loading dataset: {self.dataset_path}")
        dataset = load_dataset(self.dataset_path, trust_remote_code=True)
        
        # Cast audio to target sampling rate
        dataset = dataset.cast_column(
            self.audio_col, 
            Audio(sampling_rate=self.sampling_rate)
        )
        
        return dataset
    
    def create_manifest_for_split(self, 
                                  split_data, 
                                  split_name: str,
                                  manifest_path: str) -> Tuple[str, int]:
        """Create manifest file for a single split at predefined path"""
        logging.info(f"Processing {split_name} split...")
        logging.info(f"Manifest will be saved to: {manifest_path}")
        
        # Create split-specific audio directory
        split_audio_dir = self.audio_dir / split_name
        split_audio_dir.mkdir(exist_ok=True)
        
        valid_samples = 0
        skipped_samples = 0
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            for idx, item in enumerate(tqdm(split_data, desc=f"Creating {split_name} manifest")):
                try:
                    # Get audio data
                    audio_data = item[self.audio_col]
                    
                    # Calculate duration
                    duration = len(audio_data['array']) / audio_data['sampling_rate']
                    
                    # Filter by duration
                    if duration < self.min_duration or duration > self.max_duration:
                        skipped_samples += 1
                        continue
                    
                    # Save audio file
                    audio_filename = f"{split_name}_{idx:06d}.wav"
                    audio_filepath = split_audio_dir / audio_filename
                    
                    # Write audio file
                    sf.write(
                        str(audio_filepath),
                        audio_data['array'],
                        audio_data['sampling_rate']
                    )
                    
                    # Get and normalize text
                    text = item[self.text_col]
                    text = normalize_arabic_text(text)
                    
                    # Create manifest entry
                    manifest_entry = {
                        "audio_filepath": str(audio_filepath),
                        "duration": float(duration),
                        "text": text
                    }
                    
                    f.write(json.dumps(manifest_entry, ensure_ascii=False) + '\n')
                    valid_samples += 1
                    
                except Exception as e:
                    logging.warning(f"Error processing sample {idx}: {e}")
                    skipped_samples += 1
                    continue
        
        logging.info(f"{split_name}: {valid_samples} valid samples, {skipped_samples} skipped")
        logging.info(f"Manifest saved to: {manifest_path}")
        return manifest_path, valid_samples
    
    def create_all_manifests(self) -> Dict[str, Dict[str, Union[str, int]]]:
        """Create manifests for all splits at predefined paths"""
        dataset = self.load_dataset()
        
        results = {}
        
        # Process train split
        if self.train_split in dataset:
            train_manifest, train_samples = self.create_manifest_for_split(
                dataset[self.train_split], 
                "train",
                self.train_manifest_path
            )
            results['train'] = {
                'manifest_path': train_manifest,
                'num_samples': train_samples
            }
        
        # Process validation split
        if self.val_split in dataset:
            val_manifest, val_samples = self.create_manifest_for_split(
                dataset[self.val_split], 
                "validation",
                self.val_manifest_path
            )
            results['validation'] = {
                'manifest_path': val_manifest,
                'num_samples': val_samples
            }
        
        # Process test split
        if self.test_split in dataset:
            test_manifest, test_samples = self.create_manifest_for_split(
                dataset[self.test_split], 
                "test",
                self.test_manifest_path
            )
            results['test'] = {
                'manifest_path': test_manifest,
                'num_samples': test_samples
            }
        
        # Save metadata
        metadata = {
            'dataset_path': self.dataset_path,
            'sampling_rate': self.sampling_rate,
            'min_duration': self.min_duration,
            'max_duration': self.max_duration,
            'splits': results
        }
        
        metadata_path = self.audio_dir.parent / "manifest_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logging.info(f"\nManifest creation completed!")
        logging.info(f"Audio directory: {self.audio_dir}")
        logging.info(f"Metadata saved to: {metadata_path}")
        
        return results
