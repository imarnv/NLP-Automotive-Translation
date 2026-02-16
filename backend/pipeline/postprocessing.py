import re
from typing import Dict

def restore_placeholders(translated_text: str, placeholder_map: Dict[str, str], highlight: bool = False) -> str:
    """
    Highly robust restoration of placeholders.
    Handles mangling like 'TERM 0', '__TERM0__', 'TERM_0' etc.
    If highlight=True, wraps restored terms in markers: @@TERM@@
    """
    restored_text = translated_text
    
    # Extract original term values and their indices
    # placeholder_map looks like {"__TERM_0__": "Value", "__TERM_1__": "Value"}
    val_map = {}
    for ph, val in placeholder_map.items():
        match = re.search(r'(\d+)', ph)
        if match:
            idx = match.group(1)
            val_map[idx] = val

    # Pass 1: "Character Set" approach for T-E-R-M
    # Matches any sequence starting with T and ending with a digit, 
    # containing only allowable placeholder characters/mangling bits.
    # Uses non-greedy ? to avoid consuming multiple placeholders in one line.
    pattern = re.compile(
        r'(?:__)?\s*T\s*[T E R M S \s _ a-z]*?\s*(\d+)\s*(?:__)?', 
        re.IGNORECASE
    )

    def replace_match(match):
        try:
            # Handle leading zeros (e.g. TERM01 -> index 1)
            raw_idx = match.group(1)
            idx = str(int(raw_idx))
            if idx in val_map:
                val = val_map[idx]
                if highlight:
                    return f" @@{val}@@ "
                return f" {val} "
        except (ValueError, KeyError):
            pass
        return match.group(0)

    # First pass
    restored_text = pattern.sub(replace_match, restored_text)
    
    # Pass 2: Extremely broken cases starting with M (e.g. __ m 1 __)
    broken_pattern = re.compile(r'__?\s*M\s*[M \s _ a-z]*?\s*(\d+)\s*__?', re.IGNORECASE)
    restored_text = broken_pattern.sub(replace_match, restored_text)
    
    # Pass 3: Last Resort - Look for digits surrounded by underscores/spaces 
    # even if all letters were lost (e.g. "__ 01 __")
    last_resort_pattern = re.compile(r'__\s*[ \s _ ]*(\d+)\s*[ \s _ ]*__', re.IGNORECASE)
    restored_text = last_resort_pattern.sub(replace_match, restored_text)
    
    # Pass 4: Clean up any remaining partial placeholder artifacts like "___", "__ __"
    # Often the model adds these at the end of a line/heading.
    restored_text = re.sub(r'__\s*__', '', restored_text)
    restored_text = re.sub(r'_\s*_\s*_\s*', '', restored_text)

    # Pass 5: Specific cleanup for trailing underscores at the end of headings/sentences
    # Fixes the "_ _" issue reported by the user.
    restored_text = re.sub(r'[\s_]+$', '', restored_text)

    # Pass 6: Final space normalization (Double spaces -> Single)
    restored_text = re.sub(r'\s+', ' ', restored_text).strip()
    
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
