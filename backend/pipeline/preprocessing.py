import json
import re
import nltk
from typing import Dict, List, Tuple

# Download nltk data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

def load_glossary(path: str) -> Dict[str, Dict[str, str]]:
    """Loads the multilingual glossary from a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        glossary = json.load(f)
    return glossary

def classify_terms(glossary: Dict[str, Dict[str, str]], target_lang: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Splits glossary into PROTECTED and PREFERRED for the specific target language.
    target_lang: 'ta' (Tamil) or 'hi' (Hindi)
    """
    protected = {}
    preferred = {}
    
    # Map 'Tamil' -> 'ta', 'Hindi' -> 'hi' if full names passed, or assume code
    lang_code = 'ta' if 'tamil' in target_lang.lower() else 'hi' if 'hindi' in target_lang.lower() else 'ta'

    for term, translations in glossary.items():
        if lang_code not in translations:
            continue
            
        trans_value = translations[lang_code]
        
        # Clean Hindi values: remove parenthetical english e.g. "एअर बॅग(Air Bag)" -> "एअर बॅग"
        if lang_code == 'hi':
            trans_value = re.sub(r'\s*\(.*?\)', '', trans_value).strip()

        # Heuristic: If term has digits or is an abbreviation (all caps 3+ chars), likely protected ID/code
        if any(char.isdigit() for char in term):
            protected[term] = trans_value
        else:
            preferred[term] = trans_value
            
    return protected, preferred

def segment_text(text: str) -> List[str]:
    """Segments text into sentences using NLTK."""
    return nltk.sent_tokenize(text)

def protect_terms(text: str, protected_glossary: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """
    Masks ONLY terms in the protected_glossary.
    Returns: (masked_text, placeholder_map)
    """
    # Sort by length desc for longest match
    sorted_terms = sorted(protected_glossary.keys(), key=len, reverse=True)
    
    placeholder_map = {}
    protected_text = text
    counter = 0
    
    for term in sorted_terms:
        # Match whole words only
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        
        if pattern.search(protected_text):
            placeholder = f"__TERM_{counter}__"
            # We map placeholder -> ORIGINAL translated term value
            # Actually for protected terms (like 'ISO 123'), the translation might be transliteration or same.
            # We use the value from glossary.
            placeholder_map[placeholder] = protected_glossary[term]
            
            protected_text = pattern.sub(placeholder, protected_text)
            counter += 1
            
    return protected_text, placeholder_map
