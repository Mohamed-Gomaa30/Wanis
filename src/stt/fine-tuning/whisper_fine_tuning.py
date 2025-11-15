"""
Whisper Fine-tuning Script
"""

import functools
import os
from pathlib import Path
import evaluate
import torch
from dataclasses import dataclass
from typing import Any, Dict, List, Union
import datasets
import transformers
from transformers import AutoProcessor
import yaml
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from stt.baseline_evaluation import normalize_arabic_text


@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    """
    Data collator that will dynamically pad the inputs received.
    Args:
        processor: The processor used for processing the data.
        decoder_start_token_id: The begin-of-sentence of the decoder.
        forward_attention_mask: Whether to return attention_mask.
    """
    processor: Any
    decoder_start_token_id: int
    forward_attention_mask: bool = False
    
    def __call__(
        self, features: List[Dict[str, Union[List[int], torch.Tensor]]]
    ) -> Dict[str, torch.Tensor]:
        # split inputs and labels since they have to be of different lengths and need
        # different padding methods
        model_input_name = self.processor.model_input_names[0]
        input_features = [
            {model_input_name: feature[model_input_name]} for feature in features
        ]
        label_features = [{"input_ids": feature["labels"]} for feature in features]
        
        batch = self.processor.feature_extractor.pad(
            input_features, return_tensors="pt"
        )
        
        if self.forward_attention_mask:
            batch["attention_mask"] = torch.LongTensor(
                [feature["attention_mask"] for feature in features]
            )
        
        labels_batch = self.processor.tokenizer.pad(
            label_features, return_tensors="pt"
        )
        
        # replace padding with -100 to ignore loss correctly
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        
        # if bos token is appended in previous tokenization step,
        # cut bos token here as it's append later anyways
        if (labels[:, 0] == self.decoder_start_token_id).all().cpu().item():
            labels = labels[:, 1:]
        
        batch["labels"] = labels
        return batch


def compute_metrics(pred, tokenizer, metric):
    """Compute WER and CER metrics."""
    pred_ids = pred.predictions
    label_ids = pred.label_ids
    
    # replace -100 with the pad_token_id
    label_ids[label_ids == -100] = tokenizer.pad_token_id
    
    # decode predictions and labels
    pred_str = tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = tokenizer.batch_decode(label_ids, skip_special_tokens=True)

    # Normalize text
    pred_str = [normalize_arabic_text(pred) for pred in pred_str]
    label_str = [normalize_arabic_text(label) for label in label_str]

    cer_metric = evaluate.load("cer")
    wer_metric = evaluate.load("wer")

    wer = 100 * wer_metric.compute(predictions=pred_str, references=label_str)
    cer = 100 * cer_metric.compute(predictions=pred_str, references=label_str)
    
    return {"wer": wer, "cer": cer}
    

class WhisperFineTuner:
    def __init__(self, config): 
        """
        Initialize WhisperFineTuner
        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
    
    def _get_dataset_config(self, dataset_name: str):
        """Get dataset configuration from YAML"""
        datasets_config = self.config.get('datasets', {})
        
        if dataset_name in datasets_config:
            return datasets_config[dataset_name]
        else:
            raise ValueError(f"Dataset '{dataset_name}' not found in configuration")
    
    def fine_tune_model(self, base_model: str, dataset_name: str, output_dir: str):
        """Main fine-tuning method compatible with Modal app"""
        self.model_name = base_model
        self.dataset_name = dataset_name
        
        # Get configs
        dataset_config = self._get_dataset_config(dataset_name)
        models_config = self.config.get('models', {})
        training_config = self.config.get('training', {})
        data_config = self.config.get('data', {})
        
        # Setup output directory
        output_path = Path(output_dir)
        
        print("=" * 80)
        print(f"Fine-tuning {base_model} on {dataset_name}")
        print("=" * 80)
        
        print("\n1. Setting up training arguments")
        
        # Get training parameters from YAML
        num_train_epochs = training_config.get('num_train_epochs', 3)
        batch_size = training_config.get('batch_size', 8)
        gradient_accumulation_steps = training_config.get('gradient_accumulation_steps', 2)
        learning_rate = training_config.get('learning_rate', 1e-5)
        warmup_steps = training_config.get('warmup_steps', 500)
        max_steps = training_config.get('max_steps', -1)
        eval_strategy = training_config.get('eval_strategy', 'steps')
        eval_steps = training_config.get('eval_steps', 500)
        save_steps = training_config.get('save_steps', 500)
        logging_steps = training_config.get('logging_steps', 100)
        save_total_limit = training_config.get('save_total_limit', 2)
        generation_max_length = training_config.get('generation_max_length', 225)
        
        training_args = transformers.Seq2SeqTrainingArguments(
            output_dir=output_path.as_posix(),
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            max_steps=max_steps,
            eval_strategy=eval_strategy,
            eval_steps=eval_steps,
            save_steps=save_steps,
            save_total_limit=save_total_limit,
            gradient_checkpointing=training_config.get('gradient_checkpointing', True),
            gradient_checkpointing_kwargs={"use_reentrant": False},
            fp16=training_config.get('fp16', True) and torch.cuda.is_available(),
            group_by_length=training_config.get('group_by_length', True),
            length_column_name="input_length",
            predict_with_generate=training_config.get('predict_with_generate', True),
            generation_max_length=generation_max_length,
            generation_num_beams=training_config.get('generation_num_beams', 1),
            do_train=True,
            do_eval=True,
            report_to="none",
            logging_steps=logging_steps,
            remove_unused_columns=False,
            load_best_model_at_end=True,
            metric_for_best_model="eval_wer",
            greater_is_better=False,
        )
        
        print(f"\nTraining/evaluation parameters:")
        print(f"  Output dir: {training_args.output_dir}")
        print(f"  Epochs: {training_args.num_train_epochs}")
        print(f"  Batch size: {training_args.per_device_train_batch_size}")
        print(f"  Gradient accumulation: {training_args.gradient_accumulation_steps}")
        print(f"  Learning rate: {training_args.learning_rate}")
        
        print("\n2. Load pretrained model, tokenizer, and feature extractor")
        
        # Load config
        model_config = transformers.AutoConfig.from_pretrained(base_model)
        
        # Update config with settings
        model_config.update({
            "apply_spec_augment": models_config.get('apply_spec_augment', False),
            "forced_decoder_ids": None,
            "suppress_tokens": [],
        })
        
        # Load feature extractor
        feature_extractor = transformers.WhisperFeatureExtractor.from_pretrained(base_model)
        
        # Get language from YAML
        language = models_config.get('language', 'arabic')
        
        # Load tokenizer
        tokenizer = transformers.WhisperTokenizer.from_pretrained(
            base_model,
            language=language,
            task=models_config.get('task', 'transcribe'),
        )
        
        # Load model
        model = transformers.WhisperForConditionalGeneration.from_pretrained(
            base_model,
            config=model_config,
        )
        model.config.use_cache = False
        
        # Apply freezing if requested
        if models_config.get('freeze_feature_encoder', False):
            if hasattr(model, 'freeze_feature_encoder'):
                model.freeze_feature_encoder()
                print("Feature encoder frozen")
        
        if models_config.get('freeze_encoder', False):
            if hasattr(model, 'freeze_encoder'):
                model.freeze_encoder()
                if hasattr(model.model, 'encoder'):
                    model.model.encoder.gradient_checkpointing = False
                print("Encoder frozen")
        
        if model.config.decoder_start_token_id is None:
            raise ValueError("Make sure that `config.decoder_start_token_id` is correctly defined")
        
        print(f"Model loaded: {base_model}")
        print(f"Decoder start token ID: {model.config.decoder_start_token_id}")
        
        print("\n3. Load and prepare dataset")
        
        # Get data parameters from YAML
        num_train_samples = data_config.get('num_train_samples', 5000)
        num_eval_samples = data_config.get('num_eval_samples', 1000)
        
        # Load dataset
        print(f"Loading dataset: {dataset_config['path']}")
        full_train_dataset = datasets.load_dataset(
            dataset_config['path'],
            split=dataset_config.get('split', 'train'),
            trust_remote_code=True,
        )
        
        print(f"Dataset loaded. Total samples: {len(full_train_dataset)}")
        
        # Select subsets
        total_samples_needed = num_train_samples + num_eval_samples
        subset_dataset = full_train_dataset.select(
            range(min(total_samples_needed, len(full_train_dataset)))
        )
        
        # Split into train and eval
        train_dataset = subset_dataset.select(range(num_train_samples))
        eval_dataset = subset_dataset.select(
            range(num_train_samples, min(total_samples_needed, len(subset_dataset)))
        )
        
        raw_datasets = datasets.DatasetDict({
            "train": train_dataset,
            "eval": eval_dataset,
        })
        
        print(f"Train samples: {len(raw_datasets['train'])}")
        print(f"Eval samples: {len(raw_datasets['eval'])}")
        
        print("\n4. Resample audio if necessary")
        
        audio_col = dataset_config.get('audio_col', 'audio')
        text_col = dataset_config.get('text_col', 'sentence')
        
        dataset_sampling_rate = (
            raw_datasets["train"].features[audio_col].sampling_rate
        )
        
        if dataset_sampling_rate != feature_extractor.sampling_rate:
            print(f"Resampling from {dataset_sampling_rate} to {feature_extractor.sampling_rate}")
            raw_datasets = raw_datasets.cast_column(
                audio_col,
                datasets.features.Audio(sampling_rate=feature_extractor.sampling_rate),
            )
        else:
            print(f"No resampling needed. Rate: {dataset_sampling_rate}")
        
        print("\n5. Preprocessing the datasets")
        
        max_duration = data_config.get('max_duration_in_seconds', 30.0)
        min_duration = data_config.get('min_duration_in_seconds', 0.5)
        max_input_length = max_duration * feature_extractor.sampling_rate
        min_input_length = min_duration * feature_extractor.sampling_rate
        model_input_name = feature_extractor.model_input_names[0]
        
        # Determine if we need to forward attention mask for SpecAugment
        forward_attention_mask = (
            models_config.get('apply_spec_augment', False)
        )
        
        print(f"Forward attention mask: {forward_attention_mask}")
        
        def prepare_dataset(batch):
            """Prepare dataset by extracting features and tokenizing."""
            # Process audio
            sample = batch[audio_col]
            inputs = feature_extractor(
                sample["array"],
                sampling_rate=sample["sampling_rate"],
                return_attention_mask=forward_attention_mask,
            )
            
            # Process audio length
            batch[model_input_name] = inputs.get(model_input_name)[0]
            batch["input_length"] = len(sample["array"])
            
            if forward_attention_mask:
                batch["attention_mask"] = inputs.get("attention_mask")[0]
            
            # Process targets with text normalization
            input_str = batch[text_col]
            if data_config.get('do_lower_case', False):
                input_str = input_str.lower()
            
            # Apply Arabic text normalization
            normalized_text = normalize_arabic_text(input_str)
            batch["labels"] = tokenizer(normalized_text).input_ids
            
            return batch
        
        # Map preprocessing function
        num_workers = data_config.get('preprocessing_num_workers', 1)
        vectorized_datasets = raw_datasets.map(
            prepare_dataset,
            remove_columns=raw_datasets["train"].column_names,
            num_proc=num_workers,
            desc="Preprocessing dataset",
        )
        
        # Filter by audio length
        def is_audio_in_length_range(length):
            return min_input_length < length < max_input_length
        
        vectorized_datasets = vectorized_datasets.filter(
            is_audio_in_length_range,
            num_proc=num_workers,
            input_columns=["input_length"],
        )
        
        print(f"After filtering:")
        print(f"  Train samples: {len(vectorized_datasets['train'])}")
        print(f"  Eval samples: {len(vectorized_datasets['eval'])}")
        
        # Check if we have enough samples after filtering
        if len(vectorized_datasets['train']) == 0:
            raise ValueError(
                "No training samples left after filtering! "
                f"Try increasing max_duration_in_seconds (current: {max_duration}) "
                f"or decreasing min_duration_in_seconds (current: {min_duration})"
            )
        
        if len(vectorized_datasets['eval']) == 0:
            print("WARNING: No eval samples after filtering! Skipping evaluation.")
            training_args.do_eval = False
            vectorized_datasets['eval'] = None
        
        print("\n6. Create processor and data collator")
        
        # Save components to output dir for processor creation
        output_path.mkdir(parents=True, exist_ok=True)
        feature_extractor.save_pretrained(output_path)
        tokenizer.save_pretrained(output_path)
        model_config.save_pretrained(output_path)
        
        # Create processor
        try:
            processor = AutoProcessor.from_pretrained(output_path)
            print("Processor created successfully")
        except:
            processor = feature_extractor
            print("Using feature extractor as processor")
        
        # Create data collator
        data_collator = DataCollatorSpeechSeq2SeqWithPadding(
            processor=processor,
            decoder_start_token_id=model.config.decoder_start_token_id,
            forward_attention_mask=forward_attention_mask,
        )
        
        print("Data collator created")
        
        print("\n7. Setup metrics")
        
        metric = evaluate.load("wer")
        
        compute_metrics_fn = functools.partial(
            compute_metrics,
            tokenizer=tokenizer,
            metric=metric,
        )
        
        print("\n8. Initialize Trainer")
        
        trainer = transformers.Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=vectorized_datasets["train"] if training_args.do_train else None,
            eval_dataset=vectorized_datasets["eval"] if training_args.do_eval else None,
            tokenizer=feature_extractor,
            data_collator=data_collator,
            compute_metrics=compute_metrics_fn if training_args.predict_with_generate else None,
        )
        
        print("Trainer initialized")
        
        print("\n9. Starting Training")
        
        train_result = trainer.train()
        
        # Save model
        print("Saving model...")
        trainer.save_model()
        
        # Save processor components
        feature_extractor.save_pretrained(output_path)
        tokenizer.save_pretrained(output_path)
        
        print("\n10. Running final evaluation")
        
        if training_args.do_eval and vectorized_datasets["eval"] is not None:
            metrics = trainer.evaluate(
                metric_key_prefix="eval",
                max_length=training_args.generation_max_length,
                num_beams=training_args.generation_num_beams,
            )
            
            print(f"\nFinal eval WER: {metrics.get('eval_wer', 'N/A'):.2f}%")
            print(f"Final eval CER: {metrics.get('eval_cer', 'N/A'):.2f}%")
        else:
            print("Skipping final evaluation (no eval dataset)")
        
        print("\n" + "=" * 80)
        print("Training complete!")
        print("=" * 80)
        print(f"Model saved to: {output_path}")
        
        return str(output_path)