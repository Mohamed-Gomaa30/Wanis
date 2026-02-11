import torch
from speechbrain.inference.ASR import EncoderASR
from speechbrain.core import Stage
from speechbrain.dataio.dataset import DynamicItemDataset
from speechbrain.dataio.dataloader import SaveableDataLoader
from speechbrain.dataio.batch import PaddedBatch
from speechbrain.lobes.models.huggingface_transformers import HuggingFaceWav2Vec2
from speechbrain.utils.checkpoints import Checkpointer
from datasets import load_dataset
import os
from typing import Dict

from ..preprocessing import normalize_arabic_text

class SpeechBrainFineTuner:
    def __init__(self, config: Dict):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def prepare_data_pipeline(self, dataset_name: str):
        """Prepare data pipeline for SpeechBrain"""
        dataset_config = self.config['datasets'][dataset_name]
        
        # Load dataset
        dataset = load_dataset(
            dataset_config['path'],
            split=dataset_config['split']
        )
        
        # Limit samples for testing
        max_samples = self.config['training'].get('max_samples', len(dataset))
        if len(dataset) > max_samples:
            dataset = dataset.select(range(max_samples))
        
        def audio_pipeline(wav):
            return torch.tensor(wav['array']).float()
        
        def text_pipeline(text):
            return normalize_arabic_text(text)
        
        # Create DynamicItemDataset
        data = {
            'wav': [audio_pipeline(item[dataset_config['audio_col']]) for item in dataset],
            'text': [text_pipeline(item[dataset_config['text_col']]) for item in dataset]
        }
        
        return data
    
    def fine_tune_model(self, base_model: str, dataset_name: str, output_dir: str):
        """Fine-tune a SpeechBrain model"""
        print(f"Fine-tuning {base_model} on {dataset_name}")
        
        # Load pretrained model
        asr_model = EncoderASR.from_hparams(source=base_model)
        
        # Prepare data
        data = self.prepare_data_pipeline(dataset_name)
        
        # Create dataset and dataloader
        dataset = DynamicItemDataset(data)
        dataloader = SaveableDataLoader(
            dataset, 
            batch_size=self.config['training']['batch_size'],
            collate_fn=PaddedBatch
        )
        
        # Setup training
        asr_model.to(self.device)
        
        # Fine-tuning loop
        optimizer = torch.optim.AdamW(
            asr_model.parameters(), 
            lr=self.config['training']['learning_rate']
        )
        
        checkpointer = Checkpointer(
            checkpoints_dir=output_dir,
            recoverables={"model": asr_model, "optimizer": optimizer}
        )
        
        asr_model.train()
        
        for epoch in range(self.config['training'].get('epochs', 3)):
            total_loss = 0
            for batch in dataloader:
                wavs = batch['wav'].to(self.device)
                wav_lens = torch.tensor([1.0] * len(wavs)).to(self.device)
                texts = batch['text']
                
                # Forward pass
                outputs = asr_model.compute_forward(wavs, wav_lens, Stage.TRAIN)
                loss = asr_model.compute_objectives(outputs, texts, Stage.TRAIN)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(dataloader)
            print(f"Epoch {epoch + 1}, Average Loss: {avg_loss:.4f}")
            
            # Save checkpoint
            checkpointer.save_checkpoint(epoch=epoch)
        
        # Save final model
        asr_model.save_hparams(os.path.join(output_dir, "hyperparams.yaml"))
        torch.save(asr_model.state_dict(), os.path.join(output_dir, "model.ckpt"))
        
        return output_dir