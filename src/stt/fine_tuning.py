from transformers import WhisperForConditionalGeneration, WhisperProcessor
from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer
from peft import LoraConfig, get_peft_model, TaskType
import torch
from datasets import Dataset, Audio, load_dataset
import evaluate
from typing import Dict
import os

from .preprocessing import normalize_arabic_text

class STTFineTuner:
    def __init__(self, config: Dict):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def prepare_lora_config(self) -> LoraConfig:
        """Prepare LoRA configuration for efficient fine-tuning"""
        return LoraConfig(
            r=self.config['training']['lora_r'],
            lora_alpha=self.config['training']['lora_alpha'],
            target_modules=self.config['training']['target_modules'],
            lora_dropout=self.config['training']['lora_dropout'],
            bias="none",
            task_type=TaskType.SEQ_2_SEQ_LM,
        )
    
    def load_and_prepare_data(self):
        """Load and preprocess Egyptian Arabic datasets"""
        datasets = {}
        
        for dataset_name, dataset_config in self.config['datasets'].items():
            dataset = load_dataset(
                dataset_config['name'], 
                split=dataset_config['split']
            )
            dataset = dataset.map(self._preprocess_function, batched=True)
            datasets[dataset_name] = dataset
            
        return datasets
    
    def _preprocess_function(self, batch):
        """Preprocess audio and text for training"""

        audio = batch[self.config['datasets']['egyptian_asr']['audio_col']]
        batch["input_features"] = self.processor(
            audio["array"], 
            sampling_rate=audio["sampling_rate"],
            return_tensors="pt"
        ).input_features[0]
        
        batch["labels"] = self.processor.tokenizer(
            normalize_arabic_text(batch[self.config['datasets']['egyptian_asr']['text_col']])
        ).input_ids
        
        return batch
    
    def fine_tune_model(self, base_model: str, output_dir: str):
        """Fine-tune a Whisper model"""

        self.processor = WhisperProcessor.from_pretrained(base_model, language="arabic", task="transcribe")
        model = WhisperForConditionalGeneration.from_pretrained(base_model)
        
        # Apply LoRA if specified
        if self.config['training']['use_lora']:
            lora_config = self.prepare_lora_config()
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()
        
        # Load datasets
        datasets = self.load_and_prepare_data()
        # Combine datasets
        combined_dataset = datasets["egyptian_asr"]
        if "arabic_egy" in datasets:
            combined_dataset = combined_dataset.concatenate(datasets["arabic_egy"])
        
        # Split train/eval
        dataset_splits = combined_dataset.train_test_split(test_size=0.1, seed=42)
        train_dataset = dataset_splits["train"]
        eval_dataset = dataset_splits["test"]
        
        # Training arguments
        training_args = Seq2SeqTrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=self.config['training']['batch_size'],
            gradient_accumulation_steps=self.config['training']['gradient_accumulation_steps'],
            learning_rate=self.config['training']['learning_rate'],
            warmup_steps=self.config['training']['warmup_steps'],
            max_steps=self.config['training']['max_steps'],
            gradient_checkpointing=True,
            fp16=True,
            evaluation_strategy="steps",
            eval_steps=self.config['training']['eval_steps'],
            save_steps=self.config['training']['save_steps'],
            logging_dir=os.path.join(output_dir, "logs"),
            logging_steps=self.config['training']['logging_steps'],
            report_to=["tensorboard"],
            predict_with_generate=True,
            generation_max_length=225,
        )
        
        # Create trainer
        trainer = Seq2SeqTrainer(
            args=training_args,
            model=model,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.processor.tokenizer,
            data_collator=self._data_collator,
            compute_metrics=self._compute_metrics,
        )
        
        # Start training
        trainer.train()
        
        # Save model
        trainer.save_model()
        self.processor.save_pretrained(output_dir)
        
        return trainer
    
    def _data_collator(self, features):
        """Data collator for Whisper"""
        return {
            "input_features": torch.stack([f["input_features"] for f in features]),
            "labels": torch.tensor([f["labels"] for f in features]),
        }
    
    def _compute_metrics(self, eval_pred):
        """Compute WER and CER for evaluation"""
        predictions = eval_pred.predictions
        labels = eval_pred.label_ids
        
        # Replace -100 with the pad_token_id
        labels[labels == -100] = self.processor.tokenizer.pad_token_id
        
        # Convert predictions and labels to strings
        pred_str = self.processor.batch_decode(predictions, skip_special_tokens=True)
        label_str = self.processor.batch_decode(labels, skip_special_tokens=True)
        
        # Normalize
        pred_str = [normalize_arabic_text(pred) for pred in pred_str]
        label_str = [normalize_arabic_text(label) for label in label_str]
        
        wer_metric = evaluate.load("wer")
        cer_metric = evaluate.load("cer")
        
        wer = wer_metric.compute(predictions=pred_str, references=label_str)
        cer = cer_metric.compute(predictions=pred_str, references=label_str)
        
        return {"wer": wer, "cer": cer}