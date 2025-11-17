"""
Whisper Fine-tuning Script
"""
import os
import torch
import logging
import evaluate
import datasets
import functools
import transformers
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Any, Dict, List, Union
from transformers import AutoProcessor
from huggingface_hub import create_repo
from stt.baseline_evaluation import normalize_arabic_text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = Path(__file__).parent.parent.parent.parent / ".env" # root/.env 
load_dotenv(dotenv_path)

HF_Token = os.environ.get("HUGGINGFACE_HUB_TOKEN")
HF_UserName = os.environ.get("HF_USER_NAME")


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
        
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        
        if (labels[:, 0] == self.decoder_start_token_id).all().cpu().item():
            labels = labels[:, 1:]
        
        batch["labels"] = labels
        return batch


def compute_metrics(pred, tokenizer):
    """Compute WER and CER metrics.
    """
    pred_ids = pred.predictions
    label_ids = pred.label_ids
    
    label_ids[label_ids == -100] = tokenizer.pad_token_id
    
    pred_str = tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = tokenizer.batch_decode(label_ids, skip_special_tokens=True)

    pred_str = [normalize_arabic_text(pred) for pred in pred_str]
    label_str = [normalize_arabic_text(label) for label in label_str]

    cer_metric = evaluate.load("cer")
    wer_metric = evaluate.load("wer")

    wer = 100 * wer_metric.compute(predictions=pred_str, references=label_str)
    cer = 100 * cer_metric.compute(predictions=pred_str, references=label_str)
    
    return {"wer": wer, "cer": cer}
    
def create_model_repo(repo_id: str): 
    """
    args: 
        repo: repo path 
    return: 
        created repo 
    """
    try: 
        create_repo(repo_id, token = HF_Token, private=True, exist_ok=True)
        print(f"Repository created/verified: {repo_id}")        
    except Exception as ex: 
        print(f"Failed to create repo: {ex}")

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
        model_name = base_model
        dataset_name = dataset_name
        
        dataset_config = self._get_dataset_config(dataset_name)
        models_config = self.config.get('models', {})
        training_config = self.config.get('training', {})
        data_config = self.config.get('data', {})
        
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

        eval_strategy=training_config.get("eval_strategy","epoch")
        save_strategy=training_config.get("save_strategy", "epoch")        
        logging_steps = training_config.get('logging_steps', 100)
        save_total_limit = training_config.get('save_total_limit', 2)
        generation_max_length = training_config.get('generation_max_length', 225)

        # A100 specific optimizations
        bf16 = training_config.get('bf16', True)  # bfloat16 for A100
        tf32 = training_config.get('tf32', True)  # TF32 for A100
        dataloader_num_workers = training_config.get('dataloader_num_workers', 8)

        # push to hub config 
        push_to_hub = training_config.get('push_to_hub', True)
        hub_private_repo = training_config.get("hub_private_repo", True)  
        

        # Generate repository name: modelName_datasetName
        model_name = base_model.split('/')[-1]
        repo_id = f"{HF_UserName}/{model_name}_{dataset_name}"

        create_model_repo(repo_id)
        training_args = transformers.Seq2SeqTrainingArguments(
            push_to_hub=push_to_hub,
            hub_private_repo=hub_private_repo, 
            output_dir=repo_id,
            hub_token = HF_Token, 
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            max_steps=max_steps,
            
            eval_strategy=eval_strategy,      
            save_strategy=save_strategy,   
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

            # A100-specific optimizations
            bf16=bf16,     
            tf32=tf32,    
            dataloader_num_workers=dataloader_num_workers, 
            dataloader_pin_memory=True,
        )
        
        print(f"\nTraining/evaluation parameters:")
        print(f"  Output dir: {training_args.output_dir}")
        print(f"  Epochs: {training_args.num_train_epochs}")
        print(f"  Batch size: {training_args.per_device_train_batch_size}")
        print(f"  Gradient accumulation: {training_args.gradient_accumulation_steps}")
        print(f"  Learning rate: {training_args.learning_rate}")
        
        print("\n2. Load pretrained model, tokenizer, and feature extractor")
        
        model_config = transformers.AutoConfig.from_pretrained(base_model)
        
        model_config.update({
            "apply_spec_augment": models_config.get('apply_spec_augment', False),
            "forced_decoder_ids": None,
            "suppress_tokens": [],
        })
        
        feature_extractor = transformers.WhisperFeatureExtractor.from_pretrained(base_model)
        
        language = models_config.get('language', 'arabic')
        
        tokenizer = transformers.WhisperTokenizer.from_pretrained(
            base_model,
            language=language,
            task=models_config.get('task', 'transcribe'),
        )
        
        model = transformers.WhisperForConditionalGeneration.from_pretrained(
            base_model,
            config=model_config,
        )
        model.config.use_cache = False
        
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
        
        # num_train_samples = data_config.get('num_train_samples', 5000)
        # num_eval_samples = data_config.get('num_eval_samples', 1000)
        
        print(f"Loading dataset: {dataset_config['path']}")

        full_train_dataset = datasets.load_dataset(
            dataset_config['path'],
            trust_remote_code=True,
        )

        train_dataset = full_train_dataset[dataset_config['train_split']]
        eval_dataset = full_train_dataset[dataset_config['eval_split']]
        test_dataset = full_train_dataset[dataset_config['test_split']]

        print(f"Dataset loaded. Total samples: {len(full_train_dataset)}")
        
        # total_samples_needed = num_train_samples + num_eval_samples
        # subset_dataset = eval_dataset.select(
        #     range(min(total_samples_needed, len(full_train_dataset)))
        # )
        
        # train_dataset = eval_dataset.select(100)
        # eval_dataset = eval_dataset.select(
        #     range(100, 150)
        # )
        
        raw_datasets = datasets.DatasetDict({
            "train": train_dataset,
            "eval": eval_dataset,
            "test": test_dataset
        })
        
        print(f"Train samples: {len(raw_datasets['train'])}")
        print(f"Eval samples: {len(raw_datasets['eval'])}")
        print(f"Eval samples: {len(raw_datasets['test'])}")

        
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
        
        forward_attention_mask = (
            models_config.get('apply_spec_augment', False)
        )
        
        print(f"Forward attention mask: {forward_attention_mask}")
        
        def prepare_dataset(batch):
            """Prepare dataset by extracting features and tokenizing."""
            sample = batch[audio_col]
            inputs = feature_extractor(
                sample["array"],
                sampling_rate=sample["sampling_rate"],
                return_attention_mask=forward_attention_mask,
            )
            
            batch[model_input_name] = inputs.get(model_input_name)[0]
            batch["input_length"] = len(sample["array"])
            
            if forward_attention_mask:
                batch["attention_mask"] = inputs.get("attention_mask")[0]
            
            input_str = batch[text_col]
            if data_config.get('do_lower_case', False):
                input_str = input_str.lower()
            
            normalized_text = normalize_arabic_text(input_str)
            batch["labels"] = tokenizer(normalized_text).input_ids
            
            return batch
        
        num_workers = data_config.get('preprocessing_num_workers', 1)
        vectorized_datasets = raw_datasets.map(
            prepare_dataset,
            remove_columns=raw_datasets["train"].column_names,
            num_proc=num_workers,
            desc="Preprocessing dataset",
        )
        
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
        print(f"  Eval samples: {len(vectorized_datasets['test'])}")
        
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
        
        output_path.mkdir(parents=True, exist_ok=True)
        feature_extractor.save_pretrained(output_path)
        tokenizer.save_pretrained(output_path)
        model_config.save_pretrained(output_path)
        
        try:
            processor = AutoProcessor.from_pretrained(output_path)
            print("Processor created successfully")
        except:
            processor = feature_extractor
            print("Using feature extractor as processor")
        
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
        
        trainer.train()
        
        print("Saving model...")
        # trainer.save_model()

        trainer.push_to_hub()

        print("\n10. Running final evaluation on testset")
        
        if vectorized_datasets.get("test") is not None:
            test_metrics = trainer.evaluate(
                eval_dataset=vectorized_datasets["test"],
                metric_key_prefix="test",          
                max_length=training_args.generation_max_length,
                num_beams=training_args.generation_num_beams,
            )
            
            print(f"\nFinal TEST WER: {test_metrics.get('test_wer', 'N/A'):.2f}%")
            print(f"Final TEST CER: {test_metrics.get('test_cer', 'N/A'):.2f}%")
        else:
            print("Skipping test evaluation (no test dataset)")
        
        print("\n" + "=" * 80)
        print("Training complete!")
        print("=" * 80)
        print(f"Model saved to: {output_path}")
        
        return str(output_path)