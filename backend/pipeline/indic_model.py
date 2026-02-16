import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import os
import re

# Global caching
model = None
tokenizer = None
current_model_name = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Switching to NLLB-200 for stability and quality.
# This model is extremely reliable for Indic languages and doesn't require custom toolkits.
MODEL_NAME = "facebook/nllb-200-distilled-600M"

def load_indic_model():
    """
    Loads the NLLB-200 model and tokenizer.
    """
    global model, tokenizer, current_model_name
    
    if model is not None and current_model_name == MODEL_NAME:
        return model, tokenizer
        
    print(f"Loading NLLB-200 model {MODEL_NAME} on {DEVICE}...")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_NAME, 
            torch_dtype=torch.float32, 
            low_cpu_mem_usage=True
        ).to(DEVICE)
            
        model.eval()
        current_model_name = MODEL_NAME
        print("NLLB-200 Model loaded successfully.")
    except Exception as e:
        print(f"Error loading NLLB-200 model: {e}")
        raise e

    return model, tokenizer

def translate_batch(sentences: list, target_lang_code: str) -> list:
    """
    Translates a batch of sentences using NLLB-200.
    target_lang_code: 'tam_Taml', 'hin_Deva'
    """
    global model, tokenizer
    
    if model is None:
        load_indic_model()
    
    # Filter valid sentences
    valid_indices = []
    valid_sentences = []
    for i, s in enumerate(sentences):
        stripped = s.strip()
        if stripped:
            valid_indices.append(i)
            valid_sentences.append(stripped)
    
    if not valid_sentences:
        return sentences
        
    # NLLB usage
    tokenizer.src_lang = "eng_Latn"
    inputs = tokenizer(valid_sentences, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
    
    try:
        with torch.no_grad():
            # Determination of target language token ID
            # Usually NLLB expects something like 'hin_Deva' or 'tam_Taml'
            # If the input target_lang_code is just 'hi' or 'ta', we might need mapping
            # But let's revert to the version that was working before the blank issue
            
            outputs = model.generate(
                **inputs,
                forced_bos_token_id=tokenizer.convert_tokens_to_ids(target_lang_code),
                num_beams=5,
                no_repeat_ngram_size=3,
                max_length=256
            )
            
        decoded = tokenizer.batch_decode(
            outputs, 
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        
        # Map back to original indices
        result = list(sentences)
        for idx, valid_idx in enumerate(valid_indices):
            if idx < len(decoded):
                result[valid_idx] = decoded[idx].strip()
        
        return result
    except Exception as e:
        print(f"Translation Error: {e}")
        return [""] * len(sentences) # Return empty strings on error to prevent English leakage
