from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import os

# Global caching
model = None
tokenizer = None
current_model_name = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_model(target_lang: str):
    """
    Loads the appropriate model based on target language.
    target_lang: 'Tamil' (uses en-dra) or 'Hindi' (uses en-hi)
    """
    global model, tokenizer, current_model_name
    
    # Determine model name
    if 'hindi' in target_lang.lower():
        req_model = "Helsinki-NLP/opus-mt-en-hi"
    else:
        req_model = "Helsinki-NLP/opus-mt-en-dra" # Default to Tamil/Dravidian
        
    # If already loaded, return
    if model is not None and current_model_name == req_model:
        return model, tokenizer
        
    # If switching models, clear garbage
    if model is not None:
        print("Switching models... clearing memory.")
        del model
        del tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
    print(f"Loading model {req_model} on {DEVICE}...")
    try:
        from transformers import MarianMTModel, MarianTokenizer
        tokenizer = MarianTokenizer.from_pretrained(req_model)
        model = MarianMTModel.from_pretrained(req_model).to(DEVICE)
        model.eval()
        current_model_name = req_model
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        model = "DUMMY"
        tokenizer = "DUMMY"
        current_model_name = "DUMMY"

    return model, tokenizer

def translate_sentences(sentences: list[str], target_lang: str) -> list[str]:
    """
    Translates a list of sentences.
    """
    global model, tokenizer
    load_model(target_lang)
        
    if model == "DUMMY":
        return [f"[{target_lang}] {s}" for s in sentences]

    # Prefix handling
    # en-hi usually doesn't need strict prefix if it's single pair, but good practice to check model card.
    # en-dra handles multiple, so we used >>tam<<.
    # For en-hi (Opus-MT), it is English to Hindi specific. No prefix usually needed.
    
    inputs = []
    if 'tamil' in target_lang.lower():
         inputs = [f">>tam<< {s}" for s in sentences]
    else:
         # Hindi
         inputs = sentences

    batch = tokenizer(inputs, return_tensors="pt", padding=True).to(DEVICE)
    
    with torch.no_grad():
        generated_tokens = model.generate(
            **batch,
            max_length=512,
            num_beams=5,
            num_return_sequences=1,
        )
        
    translated = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
    return translated
