import re
from typing import Dict

def restore_placeholders(translated_text: str, placeholder_map: Dict[str, str]) -> str:
    """
    Restores PROTECTED placeholders (e.g., __TERM_0__) to their target values.
    """
    restored_text = translated_text
    for placeholder, target_term in placeholder_map.items():
        if placeholder in restored_text:
            restored_text = restored_text.replace(placeholder, target_term)
    return restored_text

def apply_preferred_translations(text: str, preferred_glossary: Dict[str, str], target_lang: str = "tam") -> str:
    """
    Applies PREFERRED translations (Substitution) in a language-aware manner.
    """
    final_text = text
    
    # Sort to avoid partial replacements
    sorted_terms = sorted(preferred_glossary.keys(), key=len, reverse=True)
    
    for term in sorted_terms:
        target_val = preferred_glossary[term]
        
        # Regex to find English term leftovers or specific placeholders if we used them
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        
        if pattern.search(final_text):
             final_text = pattern.sub(target_val, final_text)
             
    # Language-specific cleanup (Placeholder for user's strict requirement)
    if 'hindi' in target_lang.lower():
        # Hindi specific normalization if needed (e.g. danda spacing)
        # For now, just ensuring it doesn't run Tamil rules
        pass
    elif 'tamil' in target_lang.lower():
        # Tamil specific rules
        pass
             
    return final_text
