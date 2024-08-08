from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, EvalPrediction, TrainingArguments
from datasets import Dataset
from peft import LoraConfig #, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
import torch
import evaluate
from bert_score import score as bert_score
import numpy as np
from accelerate import PartialState

class InferencePEFT:
    def __init__(self, base_model_id):
        self.base_model_id = base_model_id

    def fine_tune_model(self, data, model_dir):
        quant_storage_dtype = torch.bfloat16

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_storage=quant_storage_dtype,
        )

        model = AutoModelForCausalLM.from_pretrained(
            self.base_model_id, 
            quantization_config=bnb_config,
            #load_in_4bit=True,
            #device_map="auto",
            trust_remote_code=True,
            # attn_implementation="flash_attention_2",
            torch_dtype=quant_storage_dtype,
            use_cache=False,
            # device_map={"": PartialState().process_index},
        )
        
        # Prepare the model for k-bit training (if needed)
        # model = prepare_model_for_kbit_training(model)
        
        # torch.backends.cuda.matmul.allow_tf32 = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant":False})#gradient_checkpointing_kwargs={"use_reentrant":False}
        # model.config.use_cache = False
        # model.config.gradient_checkpointing = True
        
        tokenizer = AutoTokenizer.from_pretrained(self.base_model_id)
        tokenizer.pad_token = tokenizer.eos_token

        # Assuming `tokenizer` is already defined and available
        def compute_metrics(p: EvalPrediction):
            logits, labels = p
            logits = np.argmax(logits, axis=-1)
            predictions = tokenizer.batch_decode(logits, skip_special_tokens=True)
            labels[labels < 0] = tokenizer.eos_token_id
            references = tokenizer.batch_decode(labels, skip_special_tokens=True)

            # Compute ROUGE scores
            rouge = evaluate.load('rouge')
            rouge_scores = rouge.compute(predictions=predictions, references=references)

            # Compute BERTScore
            P, R, F1 = bert_score(predictions, references, lang='en', rescale_with_baseline=True, batch_size=32)

            # Return combined metrics
            return {
                'bertscore_precision': P.mean().item(),
                'bertscore_recall': R.mean().item(),
                'bertscore_f1': F1.mean().item(),
                'rouge1': rouge_scores['rouge1'],
                'rouge2': rouge_scores['rouge2'],
                'rougeL': rouge_scores['rougeL'],
            }
        
        def formatting_prompts_func(data, is_train=True):
            prompts = data.exp_train_prompts if is_train else data.exp_valid_prompts
            references = data.exp_train_references if is_train else data.exp_valid_references
            return [
                f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

{prompt}

### Response:
{reference}
                """
                for prompt, reference in zip(prompts, references)
            ]
        
        train_dataset = Dataset.from_dict({
            "text": formatting_prompts_func(data)
        })
        valid_dataset = Dataset.from_dict({
            "text": formatting_prompts_func(data, is_train=False),
        })

        peft_config = LoraConfig(
            r=16,
            lora_alpha=8,
            target_modules="all-linear",
            bias="none",
            lora_dropout=0.05,
            task_type="CAUSAL_LM",
        )

        max_seq_length = 1024

        training_arguments = TrainingArguments(
            output_dir=model_dir,
            num_train_epochs=20,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            gradient_accumulation_steps=4,
            evaluation_strategy="epoch",
            eval_steps=10,
            save_strategy="epoch",
            save_steps=10,
            learning_rate=2.5e-5,
            bf16=True,
            # tf32=True,
            logging_steps=10,
            optim="paged_adamw_8bit",
            lr_scheduler_type="constant",  # Changed to constant
            weight_decay=0.01,
            report_to="tensorboard",
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={'use_reentrant':True} 
        )

        trainer = SFTTrainer(
            model=model,
            train_dataset=train_dataset,
            eval_dataset=valid_dataset,
            peft_config=peft_config,
            max_seq_length=max_seq_length,
            tokenizer=tokenizer,
            compute_metrics=compute_metrics,
            args=training_arguments,
            packing=True,
            eval_packing=False,
            dataset_text_field="text",
            dataset_kwargs={
            "add_special_tokens": False,  # We template with special tokens
            "append_concat_token": False,  # No need to add additional separator token
        },
        )
        
        if trainer.accelerator.is_main_process:
            trainer.model.print_trainable_parameters()

        ##########################
        # Train model
        ##########################
        trainer.train()

        ##########################
        # SAVE MODEL FOR SAGEMAKER
        ##########################
        if hasattr(trainer, 'is_fsdp_enabled') and trainer.is_fsdp_enabled:
            trainer.accelerator.state.fsdp_plugin.set_state_dict_type("FULL_STATE_DICT")
        trainer.save_model()
        print(f'Model {model_dir} has been fine-tuned!')