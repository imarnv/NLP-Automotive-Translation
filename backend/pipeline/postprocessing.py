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
                # Return the value directly. Space normalization happens in later passes.
                return val
        except (ValueError, KeyError):
            pass
        return match.group(0)

    # First pass
    restored_text = pattern.sub(replace_match, restored_text)
    
    # NEW: Safety pass to ensure no highlighter markers leak out if highlight=False
    if not highlight:
        restored_text = restored_text.replace("@@", "")
    
    # Pass 2: Extremely broken cases starting with M (e.g. __ m 1 __)
    broken_pattern = re.compile(r'__?\s*M\s*[M \s _ a-z]*?\s*(\d+)\s*__?', re.IGNORECASE)
    restored_text = broken_pattern.sub(replace_match, restored_text)
    
    # Pass 3: Last Resort - Look for digits surrounded by underscores/spaces 
    # even if all letters were lost (e.g. "__ 01 __")
    last_resort_pattern = re.compile(r'__\s*[ \s _ ]*(\d+)\s*[ \s _ ]*__', re.IGNORECASE)
    restored_text = last_resort_pattern.sub(replace_match, restored_text)
    
    # Pass 4: Clean up any remaining partial placeholder artifacts
    restored_text = re.sub(r'__\s*__', '', restored_text)
    restored_text = re.sub(r'_\s*_\s*_\s*', '', restored_text)
    
    # Pass 4.5: Remove orphaned TERM/TER fragments the model mangled beyond recognition
    # Catches: TER__, __TER, TERM_, __TERM__, _TER_ etc. (requires _ or start-of-word boundary)
    restored_text = re.sub(r'(?:^|(?<=\s)|(?<=_))_*T[\s_]*E[\s_]*R[\s_]*M?\s*_*(?=\s|$|_)', '', restored_text, flags=re.IGNORECASE)
    
    # NEW: Remove sequences of 3+ underscores (common model filler)
    restored_text = re.sub(r'_{3,}', '', restored_text)
    
    # New: Remove "spacer" underscores between words
    restored_text = re.sub(r'(\w)\s*_\s*(\w)', r'\1 \2', restored_text)
    restored_text = re.sub(r'\s+_\s+', ' ', restored_text)
    
    # NEW: Remove ANY lone underscores not part of a word
    restored_text = re.sub(r'\s_\s', ' ', restored_text)
    restored_text = re.sub(r'^_\s|\s_$', '', restored_text)
    restored_text = re.sub(r'\s_$', '', restored_text)
    restored_text = re.sub(r'^_\s', '', restored_text)

    # Pass 5: Specific cleanup for trailing underscores
    restored_text = re.sub(r'[\s_]+$', '', restored_text)

    # Pass 6: Final space normalization
    while "  " in restored_text:
        restored_text = restored_text.replace("  ", " ")
    
    # PASS 7: Transliteration Fallback for English leftovers (e.g., strainer, bolt)
    # This is a safety pass for terms the model missed.
    # Note: IndicTrans2 usually doesn't need this, but we'll add a check for common table labels.
    fallback_map = {
        "strainer": "स्ट्रेनर", "bolt": "बोल्ट", "nut": "नट", "bracket": "ब्रैकेट",
        "washer": "वाशर", "screw": "स्क्रू", "stand": "स्टैंड", "plug": "प्लग",
        "housing": "हाउसिंग", "gasket": "गास्केट", "seal": "सील"
    }
    for eng, ind in fallback_map.items():
        restored_text = re.sub(r'\b' + eng + r'\b', ind, restored_text, flags=re.IGNORECASE)
    
    return restored_text.strip()

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
